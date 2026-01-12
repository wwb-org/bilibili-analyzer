"""
ETL任务基类

提供 Extract（抽取）→ Transform（转换）→ Load（加载）的标准流程
"""
from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)


class ETLTask(ABC):
    """
    ETL任务基类

    子类需要实现 extract、transform、load 三个方法
    """

    def __init__(self, db: Session):
        self.db = db
        self.task_name = self.__class__.__name__
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.records_processed = 0
        self.errors: List[str] = []

    @abstractmethod
    def extract(self, stat_date: date) -> Any:
        """
        抽取数据

        Args:
            stat_date: 统计日期

        Returns:
            抽取的原始数据
        """
        pass

    @abstractmethod
    def transform(self, data: Any) -> Any:
        """
        转换数据

        Args:
            data: 抽取的原始数据

        Returns:
            转换后的数据
        """
        pass

    @abstractmethod
    def load(self, data: Any, stat_date: date) -> int:
        """
        加载数据

        Args:
            data: 转换后的数据
            stat_date: 统计日期

        Returns:
            处理的记录数
        """
        pass

    def run(self, stat_date: date) -> Dict:
        """
        执行ETL任务

        Args:
            stat_date: 统计日期

        Returns:
            执行结果字典
        """
        self.start_time = datetime.now()
        logger.info(f"[{self.task_name}] 开始执行，日期: {stat_date}")

        try:
            # Extract - 抽取
            raw_data = self.extract(stat_date)
            extract_count = len(raw_data) if hasattr(raw_data, '__len__') else 0
            logger.info(f"[{self.task_name}] 抽取完成，记录数: {extract_count}")

            # Transform - 转换
            transformed_data = self.transform(raw_data)
            logger.info(f"[{self.task_name}] 转换完成")

            # Load - 加载
            self.records_processed = self.load(transformed_data, stat_date)
            logger.info(f"[{self.task_name}] 加载完成，处理记录: {self.records_processed}")

            # 提交事务
            self.db.commit()

        except Exception as e:
            self.db.rollback()
            self.errors.append(str(e))
            logger.error(f"[{self.task_name}] 执行失败: {e}")
            raise

        finally:
            self.end_time = datetime.now()

        duration = (self.end_time - self.start_time).total_seconds()
        logger.info(f"[{self.task_name}] 执行完成，耗时: {duration:.2f}秒")

        return {
            "task": self.task_name,
            "stat_date": str(stat_date),
            "records_processed": self.records_processed,
            "duration": duration,
            "errors": self.errors
        }

    def _safe_divide(self, numerator: float, denominator: float, default: float = 0) -> float:
        """
        安全除法，避免除零错误

        Args:
            numerator: 分子
            denominator: 分母
            default: 除零时的默认值

        Returns:
            除法结果或默认值
        """
        if denominator == 0:
            return default
        return numerator / denominator
