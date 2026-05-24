import pymysql
import sys
import os

# 1. THE SHIM (Unlock the door first)
# We lie about the version and install the alias BEFORE importing Django stuff
pymysql.version_info = (2, 2, 1, "final", 0)
pymysql.install_as_MySQLdb()

# 2. THE PATCHES (Now it's safe to import Django backends)
try:
    from django.db.backends.mysql.base import DatabaseWrapper
    from django.db.backends.mysql.features import DatabaseFeatures

    # Disable the "RETURNING" feature for MariaDB 10.4 (XAMPP)
    DatabaseFeatures.can_return_columns_from_insert = property(lambda self: False)
    DatabaseFeatures.can_return_rows_from_bulk_insert = property(lambda self: False)

    # Bypass the MariaDB 10.6+ version requirement
    DatabaseWrapper.check_database_version_supported = lambda self: None
except ImportError:
    # This handles cases where the database backend hasn't loaded yet
    pass

# print(f"Using Key: {os.getenv('GEMINI_API_KEY')}")