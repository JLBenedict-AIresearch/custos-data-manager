# src.core.config

from pathlib import Path
from pydantic import Field, SecretStr, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    db_user: str 
    db_password: SecretStr 
    db_host: str 
    db_port: int | None 
    db_name: str 
    custos_encryption_key: SecretStr = Field(..., validation_alias="CUSTOS_ENCRYPTION_KEY")
    custos_hash_secret: SecretStr
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @computed_field
    @property
    def DATABASE_URL(self) -> str:
        return URL.create(
            drivername="postgresql+psycopg",  
            username=self.db_user,
            password=self.db_password.get_secret_value(),
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
        ).render_as_string(hide_password=False)


settings = Settings() # type: ignore