from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    mongodb_uri: str = Field(alias="MONGODB_URI")
    mongodb_database_name: str = Field(alias="MONGODB_DATABASE_NAME")
    allowed_origin: str = Field(alias="ALLOWED_ORIGIN")



@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
