from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")
    
    DATABASE_URL: str = "sqlite:///./workflow.db"
    PROJECT_NAME: str = "workflow_service"


settings = Settings()
