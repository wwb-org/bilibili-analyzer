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

    # 细粒度情绪模型配置
    EMOTION_MODEL_NAME: str = "SchuylerH/bert-multilingual-go-emtions"
    EMOTION_DEVICE: str = "cpu"
    EMOTION_MAX_LENGTH: int = 256
    EMOTION_BATCH_SIZE: int = 16

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
