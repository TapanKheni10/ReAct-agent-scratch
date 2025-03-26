from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file = "/Users/tapankheni/Developer/ReAct-agent-scratch/.env",
        extra = "ignore"
    )

    SERP_API_KEY: str
    
Config = Settings()