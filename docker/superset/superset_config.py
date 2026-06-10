import os


def _env(key: str, default: str = "") -> str:
    return os.getenv(key, default)


POSTGRES_USER = _env("POSTGRES_CONN_USERNAME", "postgres")
POSTGRES_PASSWORD = _env("POSTGRES_CONN_PASSWORD", "")
POSTGRES_HOST = _env("POSTGRES_CONN_HOST", "postgres")
POSTGRES_PORT = _env("POSTGRES_CONN_PORT", "5432")
POSTGRES_DB = _env("SUPERSET_DATABASE_NAME", "superset")

SECRET_KEY = _env("SUPERSET_SECRET_KEY", "unsafe-dev-key")
SQLALCHEMY_DATABASE_URI = (
    f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@"
    f"{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

# Keep local startup light while enabling common chart/data cache behavior.
CACHE_CONFIG = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_DEFAULT_TIMEOUT": 300,
    "CACHE_KEY_PREFIX": "superset_cache_",
    "CACHE_REDIS_HOST": _env("REDIS_HOST", "redis"),
    "CACHE_REDIS_PORT": int(_env("REDIS_PORT", "6379")),
    "CACHE_REDIS_DB": int(_env("REDIS_DB", "1")),
}

DATA_CACHE_CONFIG = CACHE_CONFIG
FEATURE_FLAGS = {
    "ALERT_REPORTS": False,
}
