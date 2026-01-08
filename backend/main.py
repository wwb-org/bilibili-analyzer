"""
B站视频内容趋势分析系统 - 后端入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, videos, statistics, admin
from app.core.config import settings
from app.core.database import engine, Base

# 创建数据库表
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="B站视频内容趋势分析系统",
    description="基于B站数据的视频内容趋势分析API",
    version="1.0.0"
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


@app.get("/")
async def root():
    return {"message": "B站视频内容趋势分析系统 API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
