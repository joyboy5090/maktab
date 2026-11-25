import os
import urllib.parse
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from pydantic import field_validator

# .env fayllarini qidirib yuklash
backend_env = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
if os.path.exists(backend_env):
    load_dotenv(backend_env)
load_dotenv()

def get_async_db_url(url: str) -> str:
    if not url:
        return "postgresql+asyncpg://postgres:postgres@localhost:5432/maktab_sms_db"
    
    parsed = urllib.parse.urlsplit(url)
    
    # query parametrlarini tozalash
    query_params = urllib.parse.parse_qsl(parsed.query)
    clean_params = []
    for k, v in query_params:
        if k == "channel_binding":
            continue
        elif k == "sslmode":
            clean_params.append(("ssl", v))
        else:
            clean_params.append((k, v))
            
    scheme = "postgresql+asyncpg"
    new_query = urllib.parse.urlencode(clean_params)
    return urllib.parse.urlunsplit((scheme, parsed.netloc, parsed.path, new_query, parsed.fragment))

class Settings(BaseSettings):
    PROJECT_NAME: str = "Maktab SMS Backend API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Database (PostgreSQL Multi-tenant)
    DATABASE_URL: str = ""
    ALEMBIC_DATABASE_URL: str = ""

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: str) -> str:
        return get_async_db_url(v)

    @field_validator("ALEMBIC_DATABASE_URL", mode="before")
    @classmethod
    def assemble_alembic_db_connection(cls, v: str) -> str:
        if not v:
            return ""
        return get_async_db_url(v)
    
    # JWT Security
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 kun
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7          # 7 kun

    @field_validator("SECRET_KEY", mode="before")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        key = v or os.getenv("SECRET_KEY", "")
        if not key or key.strip() == "":
            raise ValueError(
                "XATOLIK: SECRET_KEY environment variable topilmadi! Dastur xavfsizligi uchun .env faylida SECRET_KEY ni sozlang."
            )
        return key
    
    # CORS
    BACKEND_CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://maktab.uz",
    ]

    class Config:
        case_sensitive = True

settings = Settings()
