from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=["../.env", ".env"], extra="ignore")

    database_url: str
    storage_path: str = "/app/storage"
    backup_path: str = "/app/backups"
    api_port: int

    secret_key: str
    admin_name: str
    admin_email: str
    admin_password: str

    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""

    @property
    def smtp_configured(self) -> bool:
        return bool(self.smtp_user and self.smtp_password)


settings = Settings()
