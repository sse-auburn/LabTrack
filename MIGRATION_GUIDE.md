# MySQL Migration Guide: Docker → Dedicated Server

This guide covers migrating the LabTrack MySQL database from the Docker container (`docker-compose.mysql.yml`) to a dedicated external MySQL server (e.g., `mysqlprod.auburn.edu`).

**Assumptions:**
- Database size is under 1 GB.
- Brief downtime is acceptable.
- The target MySQL server is reachable from the Docker host.

---

## 1. Stop the Application

Bring down the entire stack to prevent any writes during the dump:

```bash
cd ~/labtrack

docker compose -f docker-compose.yml -f docker-compose.mysql.yml down
```

---

## 2. Start the Old DB Container

Start only the database container so you can extract the data:

```bash
docker compose -f docker-compose.yml -f docker-compose.mysql.yml up -d db
```

Wait ~10 seconds for MySQL to finish starting.

---

## 3. Dump the Database

### Option A: Using the container's environment

```bash
docker compose -f docker-compose.yml -f docker-compose.mysql.yml exec db \
  mysqldump -u root -p"$(docker compose -f docker-compose.yml -f docker-compose.mysql.yml exec -T db printenv MYSQL_ROOT_PASSWORD | tr -d '\r')" \
  --single-transaction --routines --triggers \
  smart-horticulture-systems-engineering > labtrack_dump.sql
```

### Option B: Using the root password directly

If the command above feels fragile, use this simpler version (replace `rootpassword` with your actual `MYSQL_ROOT_PASSWORD`):

```bash
docker compose -f docker-compose.yml -f docker-compose.mysql.yml exec db \
  mysqldump -u root -prootpassword \
  --single-transaction --routines --triggers \
  smart-horticulture-systems-engineering > labtrack_dump.sql
```

---

## 4. Stop the Old DB Container

```bash
docker compose -f docker-compose.yml -f docker-compose.mysql.yml down
```

---

## 5. Prepare the Target Database

If the target database already contains stale or partial data, drop and recreate it first. Run this on a host with the MySQL client installed (or see Step 6 for the Docker approach):

```bash
mysql -h mysqlprod.auburn.edu -u root -p'<root-password>' -e \
  "DROP DATABASE IF EXISTS \`smart-horticulture-systems-engineering\`; CREATE DATABASE \`smart-horticulture-systems-engineering\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

If the database is empty and you just need to ensure it exists:

```bash
mysql -h mysqlprod.auburn.edu -u root -p'<root-password>' -e \
  "CREATE DATABASE IF NOT EXISTS \`smart-horticulture-systems-engineering\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

Also ensure the application user exists and has proper privileges:

```sql
CREATE USER IF NOT EXISTS 'hort_user'@'%' IDENTIFIED BY 't3BReLajx@w!';
GRANT ALL PRIVILEGES ON `smart-horticulture-systems-engineering`.* TO 'hort_user'@'%';
FLUSH PRIVILEGES;
```

---

## 6. Import the Dump

If you don't have the MySQL client installed on the Docker host, use a temporary container:

```bash
# Mount the dump file and import
docker run --rm -i -v "$(pwd)/labtrack_dump.sql:/dump.sql" mysql:8.0 \
  bash -c "mysql -h mysqlprod.auburn.edu -u hort_user -p't3BReLajx@w!' smart-horticulture-systems-engineering < /dump.sql"
```

If the MySQL server blocks external Docker connections, copy `labtrack_dump.sql` to a trusted jump host (or the MySQL server itself) and run:

```bash
mysql -h mysqlprod.auburn.edu -u hort_user -p smart-horticulture-systems-engineering < labtrack_dump.sql
```

---

## 7. Verify the Import

Run a quick sanity check to confirm tables and row counts look correct:

```bash
docker run --rm -i mysql:8.0 mysql -h mysqlprod.auburn.edu -u hort_user -p't3BReLajx@w!' smart-horticulture-systems-engineering -e \
  "SHOW TABLES; SELECT COUNT(*) FROM django_migrations; SELECT COUNT(*) FROM auth_user;"
```

Compare these numbers with your expectations before proceeding.

---

## 8. Redeploy Without the Local MySQL Override

Your `.env` already points to the external database (`DB_HOST=mysqlprod.auburn.edu`). The `docker-compose.mysql.yml` file was overriding this to `DB_HOST=db`, so you simply need to stop including it in the deployment command:

```bash
# Old command (local MySQL container):
# docker compose -f docker-compose.yml -f docker-compose.mysql.yml up -d

# New command (external MySQL server):
docker compose -f docker-compose.yml up -d --build
```

---

## 9. Verify the Application

Check the application logs for a healthy startup:

```bash
docker compose -f docker-compose.yml logs -f web
```

Then:
1. Open the site in a browser.
2. Log in with an existing user account.
3. Spot-check equipment, borrow records, and other data.

---

## 10. Cleanup

After confirming everything works on the new database, remove the old Docker volume and the dump file to free disk space:

```bash
rm labtrack_dump.sql
docker volume rm labtrack_mysql_data
```

---

## Troubleshooting

### "Access denied" during import
- Verify `hort_user` exists on `mysqlprod.auburn.edu` and the password matches `.env`.
- Some MySQL servers require `%` wildcard or a specific host in the user definition (e.g., `'hort_user'@'<docker-host-ip>'`).

### "Duplicate table" errors during import
- The target database was not empty. Drop and recreate it (see Step 5), then re-import.

### App still tries to connect to `db` container
- Make sure you are **not** including `-f docker-compose.mysql.yml` in the `docker compose up` command.
- Run `docker compose -f docker-compose.yml config | grep DB_HOST` to confirm the resolved value.

### Network connectivity issues
- From the Docker host, test connectivity: `docker run --rm mysql:8.0 mysql -h mysqlprod.auburn.edu -u hort_user -p -e "SELECT 1;"`
- If the container cannot reach the server but the host can, check Docker's DNS or outbound firewall rules.

---

## Rollback Plan

If something goes wrong after switching to the external database:

1. Bring the stack down: `docker compose -f docker-compose.yml down`
2. Re-deploy with the local database: `docker compose -f docker-compose.yml -f docker-compose.mysql.yml up -d`
3. The old data still exists in the `labtrack_mysql_data` Docker volume until you explicitly delete it.
