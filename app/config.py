from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "SmartShift Scheduler Service"
    APP_ENV: str = "development"
    APP_PORT: int = 8000

    SCHEDULER_API_KEY: str

    SOLVER_MAX_TIME: int = 20
    SOLVER_ALLOW_PARTIAL: bool = True

    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"


settings = Settings()
