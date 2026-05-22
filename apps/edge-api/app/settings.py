from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    atlas_data_api_url: str
    atlas_data_api_key: str
    atlas_data_source: str = "Cluster0"
    atlas_database: str = "fleet_ops"
    atlas_collection: str = "drivers"
    allowed_origin: str = "http://localhost:3000"



@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
