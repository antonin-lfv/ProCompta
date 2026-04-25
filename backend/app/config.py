from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=["../.env", ".env"], extra="ignore")

    database_url: str = "postgresql+asyncpg://procompta:changeme@db:5432/procompta"
    storage_path: str = "/app/storage"
    backup_path: str = "/app/backups"
    api_port: int = 8000


settings = Settings()
