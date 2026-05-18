#!/bin/bash
set -euo pipefail

# =============================================================================
# LabTrack Database Migration Script
# =============================================================================
# Migrates the MySQL database from the Docker container (source) to the
# external MySQL server defined in .env (target).
#
# This script does NOT stop the old stack first. It extracts data while the
# source is running, loads it into the target, and then pauses for your
# verification before completing the cutover.
#
# Usage:
#   chmod +x migrate_db.sh
#   ./migrate_db.sh [OPTIONS]
#
# Options:
#   --drop-target    Drop and recreate the target database before import
#   --skip-verify    Skip post-import verification step
#   --help, -h       Show this help message
#
# Prerequisites:
#   - Docker and Docker Compose installed
#   - .env file present with DB_NAME, DB_USER, DB_PASSWORD, DB_HOST
#   - Source DB container accessible via docker-compose.mysql.yml
# =============================================================================

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
DROP_TARGET=false
SKIP_VERIFY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --drop-target)
            DROP_TARGET=true
            shift
            ;;
        --skip-verify)
            SKIP_VERIFY=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --drop-target    Drop and recreate the target database before import"
            echo "  --skip-verify    Skip post-import verification"
            echo "  --help, -h       Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# ---------------------------------------------------------------------------
# Load .env safely (handles comments, empty lines, and CRLF)
# ---------------------------------------------------------------------------
if [ ! -f .env ]; then
    echo -e "${RED}Error: .env file not found in $(pwd)${NC}"
    exit 1
fi

echo -e "${BLUE}[INFO]${NC} Loading environment from .env..."

while IFS='=' read -r key value; do
    # Skip comments
    [[ "$key" =~ ^[[:space:]]*# ]] && continue
    # Skip lines without an equals sign (or empty key)
    [[ -z "$key" ]] && continue
    # Trim whitespace from key
    key=$(echo "$key" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    # Skip empty keys or keys with only spaces
    [[ -z "$key" ]] && continue
    # Remove optional 'export ' prefix
    key="${key#export }"
    # Trim whitespace from value
    value=$(echo "$value" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    # Remove surrounding quotes (single or double)
    value="${value#\"}"
    value="${value%\"}"
    value="${value#\'}"
    value="${value%\'}"
    # Remove carriage returns (Windows line endings)
    value="${value//$'\r'/}"
    # Export if key is valid
    if [[ "$key" =~ ^[a-zA-Z_][a-zA-Z0-9_]*$ ]]; then
        export "$key=$value"
    fi
done < .env

# ---------------------------------------------------------------------------
# Validate required environment variables
# ---------------------------------------------------------------------------
required_vars=(DB_NAME DB_USER DB_PASSWORD DB_HOST)
missing_vars=()

for var in "${required_vars[@]}"; do
    if [ -z "${!var:-}" ]; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -ne 0 ]; then
    echo -e "${RED}Error: Missing required variables in .env:${NC}"
    for var in "${missing_vars[@]}"; do
        echo "  - $var"
    done
    exit 1
fi

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SRC_DB_NAME="${DB_NAME}"
SRC_ROOT_PASSWORD="${MYSQL_ROOT_PASSWORD:-rootpassword}"

TARGET_HOST="${DB_HOST}"
TARGET_PORT="${DB_PORT:-3306}"
TARGET_DB="${DB_NAME}"
TARGET_USER="${DB_USER}"
TARGET_PASS="${DB_PASSWORD}"

DUMP_FILE="labtrack_dump_$(date +%Y%m%d_%H%M%S).sql"

# ---------------------------------------------------------------------------
# Check Docker availability
# ---------------------------------------------------------------------------
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed or not in PATH${NC}"
    exit 1
fi

DOCKER_COMPOSE="docker compose"
if ! docker compose version &> /dev/null 2>&1; then
    if command -v docker-compose &> /dev/null; then
        DOCKER_COMPOSE="docker-compose"
    else
        echo -e "${RED}Error: Docker Compose is not installed${NC}"
        exit 1
    fi
fi

# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   LabTrack Database Migration Tool     ${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "Source: ${YELLOW}Docker MySQL container (left running)${NC}"
echo -e "Target: ${YELLOW}${TARGET_HOST}:${TARGET_PORT}/${TARGET_DB}${NC}"
echo -e "User:   ${YELLOW}${TARGET_USER}${NC}"
echo -e "Drop:   ${YELLOW}${DROP_TARGET}${NC}"
echo ""

read -p "Continue with migration? [y/N]: " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Migration cancelled by user.${NC}"
    exit 0
fi

# ############################################################################
# PHASE 1: Extract and Load (non-destructive)
# ############################################################################

# ---------------------------------------------------------------------------
# Step 1: Ensure source database is running
# ---------------------------------------------------------------------------
echo ""
echo -e "${YELLOW}[1/6] Ensuring source database container is running...${NC}"
${DOCKER_COMPOSE} -f docker-compose.yml -f docker-compose.mysql.yml up -d db

echo -e "${YELLOW}        Waiting for MySQL to be ready...${NC}"
for i in {1..60}; do
    if ${DOCKER_COMPOSE} -f docker-compose.yml -f docker-compose.mysql.yml exec -T db \
        mysqladmin ping -h localhost -u root -p"${SRC_ROOT_PASSWORD}" --silent 2>/dev/null; then
        echo -e "${GREEN}        MySQL is ready.${NC}"
        break
    fi
    if [ $i -eq 60 ]; then
        echo -e "${RED}        MySQL failed to start within 60 seconds.${NC}"
        exit 1
    fi
    sleep 1
done

# ---------------------------------------------------------------------------
# Step 2: Dump the source database
# ---------------------------------------------------------------------------
echo -e "${YELLOW}[2/6] Dumping source database '${SRC_DB_NAME}'...${NC}"

if ! ${DOCKER_COMPOSE} -f docker-compose.yml -f docker-compose.mysql.yml exec -T db \
    mysqldump -u root -p"${SRC_ROOT_PASSWORD}" \
    --single-transaction --routines --triggers \
    "${SRC_DB_NAME}" > "${DUMP_FILE}"; then
    echo -e "${RED}        Dump failed. Is the root password correct?${NC}"
    exit 1
fi

if [ ! -s "${DUMP_FILE}" ]; then
    echo -e "${RED}        Error: Dump file is empty.${NC}"
    exit 1
fi

DUMP_SIZE=$(du -sh "${DUMP_FILE}" | cut -f1)
echo -e "${GREEN}        Dump complete: ${DUMP_FILE} (${DUMP_SIZE})${NC}"

# ---------------------------------------------------------------------------
# Step 3: Test target connection
# ---------------------------------------------------------------------------
echo -e "${YELLOW}[3/6] Testing connection to target database...${NC}"
if ! docker run --rm -i mysql:8.0 mysql -h "${TARGET_HOST}" -P "${TARGET_PORT}" \
    -u "${TARGET_USER}" -p"${TARGET_PASS}" \
    -e "SELECT 1;" > /dev/null 2>&1; then
    echo -e "${RED}        Error: Cannot connect to target MySQL server.${NC}"
    echo -e "${RED}               Host: ${TARGET_HOST}:${TARGET_PORT}${NC}"
    echo -e "${RED}               User: ${TARGET_USER}${NC}"
    echo -e "${YELLOW}        The dump file is preserved: ${DUMP_FILE}${NC}"
    exit 1
fi
echo -e "${GREEN}        Connection successful.${NC}"

# ---------------------------------------------------------------------------
# Step 4: Prepare target database
# ---------------------------------------------------------------------------
echo -e "${YELLOW}[4/6] Preparing target database...${NC}"

if [ "$DROP_TARGET" = true ]; then
    echo -e "${YELLOW}        Dropping existing database (if exists)...${NC}"
    if ! docker run --rm -i mysql:8.0 mysql -h "${TARGET_HOST}" -P "${TARGET_PORT}" \
        -u "${TARGET_USER}" -p"${TARGET_PASS}" \
        -e "DROP DATABASE IF EXISTS \`${TARGET_DB}\`; CREATE DATABASE \`${TARGET_DB}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" 2>/dev/null; then
        echo -e "${YELLOW}        Warning: DROP failed (user may lack privilege). Trying CREATE only...${NC}"
        docker run --rm -i mysql:8.0 mysql -h "${TARGET_HOST}" -P "${TARGET_PORT}" \
            -u "${TARGET_USER}" -p"${TARGET_PASS}" \
            -e "CREATE DATABASE IF NOT EXISTS \`${TARGET_DB}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" || true
    fi
else
    docker run --rm -i mysql:8.0 mysql -h "${TARGET_HOST}" -P "${TARGET_PORT}" \
        -u "${TARGET_USER}" -p"${TARGET_PASS}" \
        -e "CREATE DATABASE IF NOT EXISTS \`${TARGET_DB}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
fi
echo -e "${GREEN}        Target database ready.${NC}"

# ---------------------------------------------------------------------------
# Step 5: Import dump to target
# ---------------------------------------------------------------------------
echo -e "${YELLOW}[5/6] Importing dump to target database...${NC}"
if ! docker run --rm -i -v "${SCRIPT_DIR}/${DUMP_FILE}:/dump.sql:ro" mysql:8.0 \
    bash -c "mysql -h ${TARGET_HOST} -P ${TARGET_PORT} -u ${TARGET_USER} -p'${TARGET_PASS}' ${TARGET_DB} < /dump.sql"; then
    echo -e "${RED}        Error: Import failed.${NC}"
    echo -e "${YELLOW}        The dump file is preserved at: ${DUMP_FILE}${NC}"
    exit 1
fi
echo -e "${GREEN}        Import complete.${NC}"

# ---------------------------------------------------------------------------
# Step 6: Verify import
# ---------------------------------------------------------------------------
if [ "$SKIP_VERIFY" = false ]; then
    echo -e "${YELLOW}[6/6] Verifying import...${NC}"
    
    TABLE_COUNT=$(docker run --rm -i mysql:8.0 mysql -h "${TARGET_HOST}" -P "${TARGET_PORT}" \
        -u "${TARGET_USER}" -p"${TARGET_PASS}" "${TARGET_DB}" -N -s \
        -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='${TARGET_DB}';" 2>/dev/null || echo "0")
    
    MIGRATION_COUNT=$(docker run --rm -i mysql:8.0 mysql -h "${TARGET_HOST}" -P "${TARGET_PORT}" \
        -u "${TARGET_USER}" -p"${TARGET_PASS}" "${TARGET_DB}" -N -s \
        -e "SELECT COUNT(*) FROM django_migrations;" 2>/dev/null || echo "0")
    
    echo -e "${GREEN}        Tables in target:      ${TABLE_COUNT}${NC}"
    echo -e "${GREEN}        Django migrations:     ${MIGRATION_COUNT}${NC}"
    
    if [ "$TABLE_COUNT" = "0" ]; then
        echo -e "${RED}        Warning: No tables found in target database!${NC}"
    fi
else
    echo -e "${YELLOW}[6/6] Verification skipped.${NC}"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   Phase 1 complete: Data migrated      ${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "The old Docker database is still running.${NC}"
echo -e "Dump file: ${YELLOW}${DUMP_FILE}${NC}"
echo ""

# ############################################################################
# PHASE 2: Cutover (waits for your confirmation)
# ############################################################################

echo -e "${YELLOW}Press Enter to cut over to the new database...${NC}"
read -p "(This will stop the old stack and redeploy with the external DB) "

echo ""
echo -e "${YELLOW}[CUT-OVER] Stopping old stack...${NC}"
${DOCKER_COMPOSE} -f docker-compose.yml -f docker-compose.mysql.yml down

echo -e "${YELLOW}[CUT-OVER] Starting new stack with external database...${NC}"
${DOCKER_COMPOSE} -f docker-compose.yml up -d --build

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   Cutover complete!                    ${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# ############################################################################
# PHASE 3: Cleanup (waits for your confirmation)
# ############################################################################

echo -e "${YELLOW}Press Enter to clean up old Docker volume and dump file...${NC}"
read -p "(Or Ctrl+C to keep them for now) "

echo -e "${YELLOW}[CLEANUP] Removing old Docker volume...${NC}"
docker volume rm labtrack_mysql_data 2>/dev/null || echo -e "${YELLOW}        Volume not found or already removed.${NC}"

echo -e "${YELLOW}[CLEANUP] Removing dump file...${NC}"
rm -f "${DUMP_FILE}"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   Migration fully complete!            ${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
