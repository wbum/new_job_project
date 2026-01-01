from pydantic import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./workflow.db"
    PROJECT_NAME: str = "workflow_service"

    class Config:
        env_file = ".env"

settings = Settings()
