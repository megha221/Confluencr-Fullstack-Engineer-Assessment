from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./transactions.db"
    process_delay_seconds: int = 30
    worker_poll_seconds: float = 1.0


settings = Settings()
