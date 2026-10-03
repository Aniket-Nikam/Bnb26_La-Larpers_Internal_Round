import os

os.environ.setdefault("APP_PROFILE", "test")
# Tests require a caller-provided, migrated disposable PostgreSQL database.
if "DATABASE_URL" not in os.environ:
    raise RuntimeError("Set DATABASE_URL to a migrated disposable PostgreSQL test database.")
