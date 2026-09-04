from typing import Optional
from datetime import datetime, time
from zoneinfo import ZoneInfo
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
    REDIS_URL : Optional[str] = None
    YANDEX_CLIENT_ID : Optional[str] = None
    QUIET_MODE_START : str = "23:00:00"
    QUIET_MODE_END : str = "11:00:00"
    QUIET_MODE_TIMEZONE : str = "Europe/Moscow"
    
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

    @field_validator("PROXY_URL", "YANDEX_CLIENT_ID", mode="before")
    @classmethod
    def normalize_optional_str(cls, value):
        if isinstance(value, str) and value.strip().lower() in ("", "none"):
            return None
        return value

    @field_validator("QUIET_MODE_START", "QUIET_MODE_END")
    @classmethod
    def parse_quiet_time(cls, value):
        try:
            hours, minutes, seconds = (int(part) for part in value.split(":"))
            return time(hours, minutes, seconds).isoformat()
        except (AttributeError, ValueError) as e:
            raise ValueError(f"ожидается время в формате ЧЧ:ММ:СС, получено: {value!r}") from e

    @field_validator("QUIET_MODE_TIMEZONE")
    @classmethod
    def validate_quiet_timezone(cls, value):
        try:
            ZoneInfo(value)
        except Exception as e:
            raise ValueError(f"неизвестная таймзона: {value}") from e
        return value

    def is_quiet_hours(self) -> bool:
        now = datetime.now(ZoneInfo(self.QUIET_MODE_TIMEZONE)).time()
        start = time.fromisoformat(self.QUIET_MODE_START)
        end = time.fromisoformat(self.QUIET_MODE_END)
        if start <= end:
            return start <= now < end
        return now >= start or now < end


settings = Settings()
    