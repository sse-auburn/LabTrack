try:
    # mysqlclient on Windows bundles MariaDB Connector/C which does not implement
    # MySQL 8.0's caching_sha2_password RSA key exchange, causing (2027) errors.
    # PyMySQL is pure Python and handles the full auth protocol; patching it as
    # MySQLdb here makes Django use it transparently on platforms where it is needed.
    # On Linux/Docker the real MySQL connector is preferred, but PyMySQL works too.
    import pymysql
    pymysql.install_as_MySQLdb()
except ImportError:
    pass
