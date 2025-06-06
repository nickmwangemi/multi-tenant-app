from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int
    verification_token_expire_hours: int
    migrations_location: str = "migrations"
    tenant_database_base: str = "postgres://postgres:postgres@localhost:5432"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
