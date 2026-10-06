from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://lendwise:lendwise@localhost:5432/lendwise"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "change-me"
    jwt_expire_minutes: int = 60
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.8-flash"
    model_path: str = "../ml/artifacts/model.joblib"
    upload_dir: str = "./uploads"
    annual_interest_rate: float = 0.12  # used to work out the monthly EMI


settings = Settings()