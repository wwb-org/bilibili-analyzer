"""
机器学习预测 API
"""
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, Query, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models import User, UserRole
from app.ml.predictor import hot_predictor
from app.ml.recommender import video_recommender
from app.ml.model_manager import model_manager

router = APIRouter()


# ==================== 权限检查 ====================

def require_admin(current_user: User = Depends(get_current_user)):
    """要求管理员权限"""
    if current_user.role != UserRole.ADMIN:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return current_user


# ==================== 请求/响应模型 ====================

class PredictByBvidRequest(BaseModel):
    """按 BVID 预测请求"""
    bvid: str = Field(..., description="视频 BV 号", min_length=3)


class PredictByParamsRequest(BaseModel):
    """按参数预测请求"""
    play_count: int = Field(..., ge=0, description="当前播放量")
    like_count: int = Field(0, ge=0, description="点赞数")
    coin_count: int = Field(0, ge=0, description="投币数")
    favorite_count: int = Field(0, ge=0, description="收藏数")
    share_count: int = Field(0, ge=0, description="分享数")
    danmaku_count: int = Field(0, ge=0, description="弹幕数")
    comment_count: int = Field(0, ge=0, description="评论数")
    category: Optional[str] = Field(None, description="分区")
    publish_hour: int = Field(12, ge=0, le=23, description="发布小时")
    publish_weekday: int = Field(0, ge=0, le=6, description="发布星期")
    video_age_days: int = Field(30, ge=1, description="视频发布天数")
    title_length: int = Field(20, ge=0, description="标题长度")
    duration_minutes: float = Field(5, ge=0, description="视频时长(分钟)")


class PredictionResult(BaseModel):
    """预测结果"""
    success: bool
    bvid: Optional[str] = None
    title: Optional[str] = None
    current_play_count: Optional[int] = None
    predicted_play_count: Optional[int] = None
    play_increment: Optional[int] = None
    growth_rate: Optional[float] = None
    heat_level: Optional[str] = None
    prediction_days: int = 7
    feature_importance: Optional[dict] = None
    features_used: Optional[dict] = None
    predicted_at: Optional[str] = None
    error: Optional[str] = None


class RecommendationItem(BaseModel):
    """推荐项"""
    bvid: str
    title: str
    cover_url: Optional[str] = None
    author_name: Optional[str] = None
    category: Optional[str] = None
    play_count: int
    like_count: int
    similarity_score: float
    title_similarity: float = 0.0
    same_category: bool
    same_author: bool


class RecommendationTarget(BaseModel):
    """推荐目标"""
    bvid: str
    title: str
    category: Optional[str] = None
    author_name: Optional[str] = None


class RecommendationResult(BaseModel):
    """推荐结果"""
    success: bool
    target: Optional[RecommendationTarget] = None
    recommendations: Optional[List[RecommendationItem]] = None
    total: int = 0
    method: Optional[str] = None
    error: Optional[str] = None


class PredictorInfo(BaseModel):
    """预测模型信息"""
    model_config = {"protected_namespaces": ()}

    loaded: bool
    model_type: Optional[str] = None
    feature_count: Optional[int] = None
    feature_names: Optional[List[str]] = None
    model_path: Optional[str] = None
    feature_importance: Optional[dict] = None
    message: Optional[str] = None


class RecommenderInfo(BaseModel):
    """推荐模型信息"""
    loaded: bool
    video_count: int = 0
    vectorizer_path: Optional[str] = None
    matrix_path: Optional[str] = None


class ModelInfo(BaseModel):
    """模型信息"""
    predictor: PredictorInfo
    recommender: RecommenderInfo


class TrainResult(BaseModel):
    """训练结果"""
    model_config = {"protected_namespaces": ()}

    success: bool
    model_type: Optional[str] = None
    train_samples: Optional[int] = None
    test_samples: Optional[int] = None
    train_r2: Optional[float] = None
    test_r2: Optional[float] = None
    video_count: Optional[int] = None
    vocabulary_size: Optional[int] = None
    feature_count: Optional[int] = None
    feature_names: Optional[List[str]] = None
    model_path: Optional[str] = None
    trained_at: Optional[str] = None
    error: Optional[str] = None


class TrainAllResult(BaseModel):
    """训练所有模型结果"""
    predictor: TrainResult
    recommender: TrainResult
    trained_at: Optional[str] = None


# ==================== 预测接口 ====================

@router.post("/predict/bvid", response_model=PredictionResult)
def predict_by_bvid(
    request: PredictByBvidRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    根据视频 BVID 预测 7 天后的播放量

    - **bvid**: 视频的 BV 号
    """
    # 标准化 BVID
    bvid = request.bvid.strip()
    if not bvid.startswith('BV'):
        bvid = 'BV' + bvid

    result = hot_predictor.predict_by_bvid(bvid, db)
    return result


@router.post("/predict/params", response_model=PredictionResult)
def predict_by_params(
    request: PredictByParamsRequest,
    current_user: User = Depends(get_current_user)
):
    """
    根据手动输入的参数预测播放量

    适用于：
    - 预测新视频的潜在表现
    - 模拟不同参数组合的效果
    """
    params = request.model_dump()
    result = hot_predictor.predict_by_params(params)
    return result


# ==================== 推荐接口 ====================

@router.get("/recommend/{bvid}", response_model=RecommendationResult)
def get_recommendations(
    bvid: str,
    top_k: int = Query(10, ge=1, le=50, description="返回数量"),
    same_category: bool = Query(True, description="是否优先同分区"),
    same_author: bool = Query(False, description="是否包含同作者"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取与指定视频相似的推荐视频

    - **bvid**: 目标视频 BV 号
    - **top_k**: 返回推荐数量，默认 10
    - **same_category**: 是否优先推荐同分区视频
    - **same_author**: 是否包含同一 UP 主的视频
    """
    # 标准化 BVID
    bvid = bvid.strip()
    if not bvid.startswith('BV'):
        bvid = 'BV' + bvid

    result = video_recommender.recommend_by_bvid(
        bvid, db, top_k, same_category, same_author
    )
    return result


# ==================== 模型信息接口 ====================

@router.get("/model-info", response_model=ModelInfo)
def get_model_info(current_user: User = Depends(get_current_user)):
    """
    获取模型状态和信息
    """
    return {
        "predictor": hot_predictor.get_model_info(),
        "recommender": video_recommender.get_model_info()
    }


# ==================== 模型训练接口（管理员） ====================

@router.post("/train/predictor", response_model=TrainResult)
def train_predictor_model(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """
    训练热度预测模型（管理员专用）

    训练过程：
    1. 从数据库提取视频数据
    2. 构建特征和标签
    3. 使用 XGBoost 训练回归模型
    4. 保存模型到 ml_models/ 目录
    """
    result = model_manager.train_predictor(db)

    # 重新加载模型
    if result.get("success"):
        hot_predictor.reload_model()

    return result


@router.post("/train/recommender", response_model=TrainResult)
def train_recommender_model(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """
    训练推荐模型（管理员专用）

    训练过程：
    1. 获取所有视频标题
    2. 中文分词处理
    3. 训练 TF-IDF 向量化器
    4. 生成相似度矩阵
    5. 保存模型到 ml_models/ 目录
    """
    result = model_manager.train_recommender(db)

    # 重新加载模型
    if result.get("success"):
        video_recommender.reload_models()

    return result


@router.post("/train/all", response_model=TrainAllResult)
def train_all_models(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """
    训练所有模型（管理员专用）
    """
    results = model_manager.train_all(db)

    # 重新加载模型
    if results.get("predictor", {}).get("success"):
        hot_predictor.reload_model()
    if results.get("recommender", {}).get("success"):
        video_recommender.reload_models()

    return results
