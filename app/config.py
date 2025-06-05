from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int
    verification_token_expire_hours: int

    class Config:
        env_file = ".env"


settings = Settings()

TORTOISE_ORM = {
    "connections": {
        "default": settings.database_url,
    },
    "apps": {
        "models": {
            "models": ["app.models.core", "app.models.tenant", "aerich.models"],
            "default_connection": "default",
        },
    },
    # "use_tz": True,
    "timezone": "UTC",
}
