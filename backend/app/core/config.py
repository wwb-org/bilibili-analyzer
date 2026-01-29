"""
应用配置
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # 数据库配置
    DATABASE_URL: str = "mysql+pymysql://root:123456@localhost:3306/bilibili_analyzer"

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


def reload_settings():
    """
    重新加载配置

    清除lru_cache缓存，使配置重新从.env文件读取
    """
    get_settings.cache_clear()
    global settings
    settings = get_settings()
    return settings


settings = get_settings()
