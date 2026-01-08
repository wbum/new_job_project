from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database Configuration
    DATABASE_URL: str = "sqlite:///./workflow.db"

    # Application Settings
    PROJECT_NAME: str = "workflow_service"
    APP_VERSION: str = "0.1.0"

    # Environment Configuration
    APP_ENV: str = "dev"  # dev, staging, prod
    LOG_LEVEL: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL

    class Config:
        env_file = ".env"


settings = Settings()
