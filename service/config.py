import os


class Settings:
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    instance_name = os.getenv("INSTANCE_NAME", "instance-1")
    default_limit = int(os.getenv("DEFAULT_LIMIT", "60"))
    default_window_seconds = int(os.getenv("DEFAULT_WINDOW_SECONDS", "60"))


settings = Settings()
