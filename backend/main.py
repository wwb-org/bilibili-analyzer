"""
B站视频内容趋势分析系统 - 后端入口
"""
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, videos, statistics, admin, live
from app.core.config import settings
from app.core.database import engine, Base
from app.etl.scheduler import etl_scheduler

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建数据库表（包括数仓表）
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理

    启动时：启动ETL调度器
    关闭时：停止ETL调度器
    """
    # 启动时执行
    logger.info("应用启动中...")
    etl_scheduler.start()
    logger.info("ETL调度器已启动")

    yield

    # 关闭时执行
    logger.info("应用关闭中...")
    etl_scheduler.stop()
    logger.info("ETL调度器已停止")


app = FastAPI(
    title="B站视频内容趋势分析系统",
    description="基于B站数据的视频内容趋势分析API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(videos.router, prefix="/api/videos", tags=["视频"])
app.include_router(statistics.router, prefix="/api/statistics", tags=["统计分析"])
app.include_router(admin.router, prefix="/api/admin", tags=["管理"])
app.include_router(live.router, prefix="/api/live", tags=["直播分析"])

# test

@app.get("/")
async def root():
    return {"message": "B站视频内容趋势分析系统 API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
