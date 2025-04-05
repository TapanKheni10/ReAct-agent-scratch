from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file = "../../env",
        extra = "ignore"
    )

    SERP_API_KEY: str
    GROQ_API_KEY: str
    SERPER_DEV_API_KEY: str
    
Config = Settings()