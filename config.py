from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator

class Settings(BaseSettings):
    KETTLE_IP : str
    KETTLE_TOKEN : str
    BOT_TOKEN : str
    API_BASE_URL : str
    KETTLE_USERNAME : str
    KETTLE_PASSWORD : str
    JWT_SECRET : str
    ADMIN_ID : Optional[set[int]] = None
    PROXY_URL : Optional[str] = None
    
    model_config = SettingsConfigDict(
            env_file=".env",
            env_file_encoding="utf-8",
            extra="ignore"
        )

    @field_validator("ADMIN_ID", mode="before")
    @classmethod
    def parse_admin_ids(cls, value):
        if not value or (isinstance(value, str) and value.strip().lower() == "none"):
            return None
        if isinstance(value, str):
            value = value.split(",")
        elif not isinstance(value, (list, set, tuple)):
            value = [value]
        try:
            return {int(item) for item in value}
        except (TypeError, ValueError) as e:
            raise ValueError("ADMIN_ID должен быть числом или списком чисел (через запятую) или None") from e

    @field_validator("PROXY_URL", mode="before")
    @classmethod
    def normalize_proxy_url(cls, value):
        if isinstance(value, str) and value.strip().lower() == "none":
            return None
        return value

    

settings = Settings()    
    