from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    mongodb_uri: str = Field(alias="MONGODB_URI")
    mongodb_database_name: str = Field(alias="MONGODB_DATABASE_NAME")
    allowed_origin: str = Field(alias="ALLOWED_ORIGIN")
    simulator_api_token: str = Field(default="local-dev-simulator-token", alias="SIMULATOR_API_TOKEN")
    redis_url: str = Field(default="redis://127.0.0.1:6379/0", alias="REDIS_URL")



@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
