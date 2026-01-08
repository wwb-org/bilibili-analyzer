"""
应用配置
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # 数据库配置
    DATABASE_URL: str = "mysql+pymysql://root:password@localhost:3306/bilibili_analyzer"

    # Redis配置
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT配置
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # B站Cookie（可选，用于获取更多数据）
    BILIBILI_COOKIE: str = ""

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings():
    return Settings()


settings = get_settings()
