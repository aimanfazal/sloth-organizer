from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    LM_STUDIO_BASE_URL: str = "http://127.0.0.1:1234/v1"
    LM_STUDIO_MODEL: str = ""
    DB_PATH: str = "~/.sloth_organizer/data.db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
