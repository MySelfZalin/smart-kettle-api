from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    KETTLE_IP : str
    KETTLE_TOKEN : str
    BOT_TOKEN : str
    API_BASE_URL : str
    KETTLE_USERNAME : str
    KETTLE_PASSWORD : str
    JWT_SECRET : str
    ADMIN_ID : int
    
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()    
    