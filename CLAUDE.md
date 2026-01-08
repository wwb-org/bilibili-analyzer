# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## 项目概述

**项目名称**：基于Spark Streaming的B站视频内容趋势分析系统

**项目类型**：大数据专业毕业设计

**项目定位**：一个具有大数据专业特色的数据分析系统，采用前后端分离架构，支持B站视频数据采集、实时流处理、数据仓库、机器学习分析和可视化展示。

**核心特色**：
1. Kafka + Spark Streaming 实时流处理
2. ODS→DWD→DWS→ADS 数据仓库分层设计
3. XGBoost热度预测 + K-Means用户聚类 + TF-IDF内容推荐
4. 实时直播弹幕分析（亮点功能）

---

## 技术栈

### 后端
| 技术 | 用途 |
|------|------|
| FastAPI | Web框架，Python 3.10+ |
| SQLAlchemy | ORM |
| MySQL 8.0 | 关系型数据库 |
| Redis | 缓存、实时指标存储 |
| Kafka | 消息队列 |
| Spark Streaming (PySpark) | 实时流处理 |
| Jieba | 中文分词 |
| SnowNLP | 情感分析 |
| XGBoost | 热度预测模型 |
| Scikit-learn | K-Means聚类、TF-IDF |
| bilibili-api-python | B站直播弹幕连接 |

### 前端
| 技术 | 用途 |
|------|------|
| Vue3 + Vite | 前端框架 |
| Element Plus | UI组件库 |
| ECharts | 数据可视化图表 |
| echarts-wordcloud | 词云图 |
| Pinia | 状态管理 |
| Axios | HTTP请求 |
| WebSocket | 实时数据推送 |

---

## 项目结构

```
bilibili-analyzer/
├── frontend/                   # Vue3 前端项目
│   ├── src/
│   │   ├── views/              # 页面组件（12个页面）
│   │   ├── components/         # 公共组件
│   │   ├── api/                # API请求封装
│   │   ├── store/              # Pinia状态管理
│   │   ├── router/             # Vue Router路由
│   │   ├── App.vue
│   │   └── main.js
│   ├── package.json
│   └── vite.config.js
│
├── backend/                    # FastAPI 后端项目
│   ├── app/
│   │   ├── api/                # API路由
│   │   │   ├── auth.py         # 用户认证
│   │   │   ├── videos.py       # 视频数据
│   │   │   ├── statistics.py   # 统计分析
│   │   │   └── admin.py        # 管理员功能
│   │   ├── core/               # 核心配置
│   │   │   ├── config.py       # 应用配置
│   │   │   ├── database.py     # 数据库连接
│   │   │   └── security.py     # JWT认证
│   │   ├── models/             # 数据模型
│   │   │   └── models.py       # SQLAlchemy模型
│   │   ├── services/           # 业务服务
│   │   │   ├── crawler.py      # B站数据采集
│   │   │   ├── nlp.py          # NLP分析
│   │   │   └── analyzer.py     # 数据分析
│   │   └── tasks/              # 定时任务
│   │       └── scheduler.py    # APScheduler
│   ├── main.py                 # 应用入口
│   └── requirements.txt
│
├── streaming/                  # Kafka + Spark Streaming
│   ├── kafka_producer.py       # Kafka生产者
│   ├── spark_streaming.py      # Spark流处理
│   └── config.py
│
├── data_warehouse/             # 数据仓库ETL
│   ├── ods/                    # 原始数据层
│   ├── dwd/                    # 明细数据层
│   ├── dws/                    # 汇总数据层
│   ├── ads/                    # 应用数据层
│   └── etl_scheduler.py        # ETL调度
│
├── ml/                         # 机器学习模块
│   ├── train_xgboost.py        # 热度预测训练
│   ├── train_kmeans.py         # UP主聚类
│   ├── similarity.py           # TF-IDF相似度推荐
│   └── models/                 # 训练好的模型文件
│
├── docs/                       # 文档
│   └── database.sql            # 数据库初始化脚本
│
├── CLAUDE.md                   # 项目说明（本文件）
└── README.md
```

---

## 数据采集策略

- **采集范围**：B站每日热门榜单（约100-200个视频/天）
- **数据积累**：运行1-2周后，约有1000-3000条视频数据
- **频率限制**：B站API约30次/分钟，采集间隔建议2秒以上
- **数据含义**：
  - 视频总数 = 系统累计采集到的热门视频数量
  - 今日新增 = 今天新上榜的热门视频数量

---

## 前端页面说明（共10个）

### 页面总览

| 序号 | 页面 | 文件 | 权限 | 说明 |
|------|------|------|------|------|
| 1 | 登录 | Login.vue | 公开 | 用户登录 |
| 2 | 注册 | Register.vue | 公开 | 用户注册 |
| 3 | 首页仪表盘 | Home.vue | 用户 | 数据概览仪表盘 |
| 4 | 视频数据 | Videos.vue | 用户 | 视频列表 + 单视频详情（含评论、热词） |
| 5 | 评论分析 | Comments.vue | 用户 | 全局评论聚合分析 |
| 6 | 热词分析 | Keywords.vue | 用户 | 全局热词聚合分析 |
| 7 | 直播分析 | Live.vue | 用户 | **实时弹幕分析（亮点）** |
| 8 | ML预测 | Prediction.vue | 用户 | 热度预测、相似推荐 |
| 9 | 管理后台 | Admin.vue | 管理员 | 用户管理、采集控制 |
| 10 | 个人中心 | Profile.vue | 用户 | 个人信息、修改密码 |

### 核心页面详细说明

#### 全局导航栏（左侧边栏）
采用左侧固定导航栏，所有页面共享：
- 首页、视频数据、评论分析、热词分析、直播分析、智能预测
- 管理后台（仅管理员可见）
- 个人中心、退出登录

#### 首页仪表盘 (Home.vue)
**模块一：核心指标卡片（5个）**
- 视频总数（+今日新增）
- 总播放量
- 总评论数（+今日新增）
- 总弹幕数（+今日新增）
- 平均互动率

**模块二：数据趋势图**
- ECharts折线图，支持切换：播放量/新增视频/评论数
- 时间范围切换：近7天/近30天

**模块三：分区分布**
- ECharts环形图，展示视频分区占比
- 点击扇区可跳转该分区视频列表

**模块四：热门视频TOP10**
- 列表展示：标题、播放量、UP主
- 点击可跳转视频详情

**模块五：情感分析概览**
- 进度条展示正面/中性/负面占比
- 点击可跳转评论分析页

**模块六：今日热词云**
- echarts-wordcloud展示今日高频词
- 点击词语可跳转热词分析页

**模块七：系统状态（仅管理员可见）**
- 最近采集时间、状态、数量
- MySQL/Redis/Kafka连接状态
- 点击可进入管理后台

#### 视频数据 (Videos.vue)
**页面定位**：视频列表 + 单视频详情（以视频为中心的完整画像）

**视频列表**：
- 筛选栏：时间范围、分区、关键词、排序方式
- 表格字段：封面、标题、UP主、分区、播放量、点赞、投币、发布时间
- 底部：分页 + Excel导出

**视频详情弹窗**（点击视频打开）：
- 视频基础信息：标题、封面、UP主、播放量、点赞、投币等
- 该视频的评论列表（带情感标签）
- 该视频的评论情感分布饼图
- 该视频的热词/弹幕词云

#### 评论分析 (Comments.vue)
**页面定位**：全局评论聚合分析（跨视频）

**模块一：筛选栏**
- 时间范围：近7天/近30天/自定义
- 视频分区：全部/游戏/生活/科技/...
- 情感类型：全部/正面/中性/负面
- 关键词搜索：搜索评论内容

**模块二：情感统计卡片（3个）**
- 正面评论：数量+占比（绿色）
- 中性评论：数量+占比（灰色）
- 负面评论：数量+占比（红色）

**模块三：情感分布饼图**
- ECharts饼图展示正面/中性/负面占比

**模块四：情感趋势折线图**
- X轴日期，Y轴评论数量
- 三条线：正面、中性、负面

**模块五：评论词云**
- 全局高频词展示
- 颜色区分：正面词绿色、负面词红色、中性词灰色
- 点击词语可筛选包含该词的评论

**模块六：评论列表**
- 字段：评论内容、所属视频（可跳转）、用户名、情感标签、情感分数、发布时间
- 支持分页、按情感分数排序
- 支持导出Excel

#### 热词分析 (Keywords.vue)
**页面定位**：全局热词聚合分析（跨视频）

**模块一：筛选栏**
- 时间范围：近7天/近30天/自定义
- 视频分区：全部/游戏/生活/科技/...
- 词来源：全部/标题/弹幕/评论

**模块二：热词统计卡片（3个）**
- 今日热词数：今日出现的不同词汇数量
- 今日Top1热词：频次最高的词
- 新晋热词：今日新上榜的热词数量

**模块三：热词词云**
- ECharts wordcloud展示，词频越高越大
- 点击词语选中，联动更新趋势图和详情面板

**模块四：热词排行榜**
- 字段：排名、热词、频次、来源、较昨日涨跌
- 支持按频次/涨幅排序
- 点击热词查看详情

**模块五：热词趋势图**
- 显示选中热词的历史频次变化
- X轴日期，Y轴频次

**模块六：热词详情面板**（点击热词展开）
- 基本信息：总频次、首次出现时间
- 来源分布饼图：标题/弹幕/评论占比
- 关联视频列表：包含该词的视频
- 相关评论/弹幕：最新10条

**导出功能**：支持导出热词数据Excel

#### 直播分析 (Live.vue) - 亮点功能
**页面定位**：实时连接B站直播间，对弹幕进行实时NLP分析

**模块一：直播间输入**
- 输入框：直播间ID或URL
- 连接按钮：开始/停止连接
- 连接状态：已连接/连接中/未连接

**模块二：直播间信息卡片**
- 主播名称、头像、直播标题
- 当前人气值、直播时长

**模块三：实时弹幕流**
- 滚动显示最新弹幕
- 每条弹幕带情感标签（正面绿/负面红/中性灰）
- 支持暂停滚动查看

**模块四：统计卡片（4个）**
- 总弹幕数、弹幕速率（条/分钟）、平均情感分、礼物数

**模块五：情感分布饼图**
- 正面/中性/负面占比，实时更新

**模块六：情感折线图**
- 实时展示情感变化趋势
- X轴时间，Y轴情感分数

**模块七：人气曲线图**
- 监测直播间热度变化
- X轴时间，Y轴人气值

**模块八：实时弹幕词云**
- 高频词展示，每10秒更新

**模块九：礼物明细**
- 礼物名称、送礼人、价值

**数据存储**：直播结束后保存弹幕数据供后续分析

#### ML预测 (Prediction.vue)
**页面定位**：机器学习功能展示（热度预测 + 相似推荐）

**模块一：热度预测**
- 视频选择：下拉搜索选择已有视频
- 预测结果：7天后播放量预测值、置信区间
- 特征重要性：柱状图展示各特征贡献度

**模块二：相似视频推荐**
- 视频选择：下拉搜索选择一个视频
- 推荐结果：相似视频TOP10（标题、相似度分数、播放量）
- 相似原因：展示共同关键词

**模块三：预测历史**
- 用户历史预测记录列表
- 字段：预测时间、视频标题、预测值、实际值（如有）

**模块四：模型信息面板**
- 模型版本、训练时间、训练数据量、模型准确率

#### 管理员后台 (Admin.vue)
**页面定位**：管理员专属，系统管理与数据采集控制

**模块一：用户管理**
- 用户列表：用户名、邮箱、角色、状态、注册时间
- 操作：启用/禁用、修改角色
- 搜索筛选：按用户名、角色、状态筛选

**模块二：采集任务管理**
- 任务状态：当前采集任务运行状态
- 操作：启动/停止、立即执行
- 采集配置：采集间隔、每次数量等参数

**模块三：采集日志**
- 字段：任务名称、状态、采集数量、开始/结束时间、错误信息
- 支持分页查看

**模块四：系统状态监控**
- MySQL：连接状态、响应时间
- Redis：连接状态、内存使用
- Kafka：连接状态、Topic数量

**模块五：数据统计**
- 各表数据量：视频数、评论数、弹幕数、热词数等

**模块六：数据清理**
- 删除N天前的数据
- 操作需二次确认

#### 个人中心 (Profile.vue)
**页面定位**：用户个人信息管理

**模块一：个人信息**
- 用户名（不可修改）
- 邮箱（可修改）
- 角色（显示）
- 注册时间（显示）

**模块二：修改密码**
- 当前密码、新密码、确认密码

---

## 后端API接口

### 用户认证 (/api/auth)
```
POST /register     # 用户注册
POST /login        # 用户登录，返回JWT
GET  /profile      # 获取当前用户信息
PUT  /profile      # 更新用户信息
PUT  /password     # 修改密码
```

### 视频数据 (/api/videos)
```
GET  /             # 视频列表（分页、筛选）
GET  /{bvid}       # 视频详情
GET  /{bvid}/comments  # 视频评论列表
```

### 统计分析 (/api/statistics)
```
GET  /overview        # 总览数据（卡片）
GET  /trends          # 趋势数据（折线图）
GET  /categories      # 分区统计（饼图）
GET  /keywords        # 热词数据（词云）
GET  /sentiment       # 情感分析统计
GET  /top-videos      # 热门视频榜
GET  /top-authors     # 热门UP主榜
```

### UP主分析 (/api/authors)
```
GET  /             # UP主列表（含聚类标签）
GET  /{author_id}  # UP主详情
GET  /{author_id}/videos  # UP主视频列表
```

### ML预测 (/api/ml)
```
POST /predict      # 视频热度预测
GET  /recommend/{bvid}  # 相似视频推荐
```

### 直播分析 (/api/live)
```
WebSocket /ws/{room_id}  # 直播弹幕实时分析
```

### 数据导出 (/api/export)
```
GET  /videos       # 导出视频数据Excel
GET  /keywords     # 导出热词数据Excel
```

### 管理员 (/api/admin)
```
GET  /users           # 用户列表
PUT  /users/{id}      # 修改用户状态/角色
GET  /crawl/logs      # 采集日志
POST /crawl/start     # 启动采集任务
POST /crawl/stop      # 停止采集任务
GET  /system/status   # 系统状态
```

---

## 数据库设计

### 核心表结构

```sql
-- 用户表
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('admin', 'user') DEFAULT 'user',
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 视频表
CREATE TABLE videos (
    id INT PRIMARY KEY AUTO_INCREMENT,
    bvid VARCHAR(20) UNIQUE NOT NULL,
    title VARCHAR(200) NOT NULL,
    category VARCHAR(50),
    author_id VARCHAR(50),
    author_name VARCHAR(100),
    play_count INT DEFAULT 0,
    like_count INT DEFAULT 0,
    coin_count INT DEFAULT 0,
    share_count INT DEFAULT 0,
    danmaku_count INT DEFAULT 0,
    comment_count INT DEFAULT 0,
    publish_time DATETIME,
    cover_url VARCHAR(500),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 评论表
CREATE TABLE comments (
    id INT PRIMARY KEY AUTO_INCREMENT,
    video_id INT,
    content TEXT,
    user_name VARCHAR(100),
    sentiment_score FLOAT,  -- 0-1，越高越正面
    sentiment_label ENUM('positive', 'neutral', 'negative'),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (video_id) REFERENCES videos(id)
);

-- 弹幕表
CREATE TABLE danmakus (
    id INT PRIMARY KEY AUTO_INCREMENT,
    video_id INT,
    content VARCHAR(500),
    send_time FLOAT,  -- 视频时间点（秒）
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (video_id) REFERENCES videos(id)
);

-- 热词统计表
CREATE TABLE keywords (
    id INT PRIMARY KEY AUTO_INCREMENT,
    word VARCHAR(50) NOT NULL,
    frequency INT DEFAULT 1,
    source ENUM('title', 'comment', 'danmaku'),
    category VARCHAR(50),
    stat_date DATE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- UP主表
CREATE TABLE authors (
    id INT PRIMARY KEY AUTO_INCREMENT,
    author_id VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100),
    face_url VARCHAR(500),
    follower_count INT DEFAULT 0,
    video_count INT DEFAULT 0,
    total_play INT DEFAULT 0,
    cluster_label VARCHAR(50),  -- 聚类标签
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 采集日志表
CREATE TABLE crawl_logs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    task_name VARCHAR(100),
    status ENUM('running', 'success', 'failed'),
    video_count INT DEFAULT 0,
    comment_count INT DEFAULT 0,
    error_msg TEXT,
    started_at DATETIME,
    finished_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## 数据仓库分层设计

```
┌─────────────────────────────────────────────────────────┐
│  ADS（应用数据层）- 直接给前端用                          │
│  ads_hot_video_top100, ads_category_stats              │
├─────────────────────────────────────────────────────────┤
│  DWS（汇总数据层）- 按日/周聚合                          │
│  dws_video_daily, dws_category_daily, dws_author_daily │
├─────────────────────────────────────────────────────────┤
│  DWD（明细数据层）- 清洗后标准数据                        │
│  dwd_video, dwd_comment, dwd_danmaku                   │
├─────────────────────────────────────────────────────────┤
│  ODS（原始数据层）- 原始JSON保留                         │
│  ods_video_raw, ods_comment_raw, ods_danmaku_raw       │
└─────────────────────────────────────────────────────────┘
```

---

## 机器学习模型

### 1. 视频热度预测（XGBoost）
- **输入特征**：like_rate, coin_rate, publish_hour, category, title_length
- **预测目标**：7天后播放量
- **模型文件**：ml/models/xgboost_model.pkl

### 2. UP主聚类画像（K-Means）
- **输入特征**：avg_play, avg_like, video_count, update_freq
- **聚类数量**：5类
- **标签含义**：
  - 高产型：更新频繁，播放稳定
  - 爆款型：更新少但单个播放高
  - 稳定型：粉丝多，数据稳定
  - 新人型：粉丝少，视频少
  - 沉寂型：很久不更新
- **模型文件**：ml/models/kmeans_model.pkl

### 3. 内容推荐（TF-IDF）
- **方法**：基于视频标题的TF-IDF向量余弦相似度
- **模型文件**：ml/models/tfidf_vectorizer.pkl

---

## 常用命令

### 后端启动
```bash
cd backend
pip install -r requirements.txt
python main.py                    # 启动 http://localhost:8000
# API文档：http://localhost:8000/docs
```

### 前端启动
```bash
cd frontend
npm install
npm run dev                       # 启动 http://localhost:5173
npm run build                     # 构建生产版本
```

### 数据库初始化
```bash
mysql -u root -p < docs/database.sql
```

### Kafka（本地单节点）
```bash
# 启动 Zookeeper
bin/zookeeper-server-start.sh config/zookeeper.properties

# 启动 Kafka
bin/kafka-server-start.sh config/server.properties

# 创建Topic
bin/kafka-topics.sh --create --topic video-topic --bootstrap-server localhost:9092
bin/kafka-topics.sh --create --topic comment-topic --bootstrap-server localhost:9092
bin/kafka-topics.sh --create --topic danmaku-topic --bootstrap-server localhost:9092
```

### Spark Streaming
```bash
cd streaming
spark-submit spark_streaming.py
```

### 机器学习模型训练
```bash
cd ml
python train_xgboost.py      # 训练热度预测模型
python train_kmeans.py       # 训练UP主聚类模型
```

---

## 环境变量配置

后端 `backend/.env` 文件：
```
DATABASE_URL=mysql+pymysql://root:password@localhost:3306/bilibili_analyzer
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-secret-key-here
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
```

---

## 开发注意事项

1. **B站API频率限制**：约30次/分钟，采集间隔建议2秒以上
2. **Kafka和Spark**：需要Java 8+环境
3. **数据合规**：数据仅用于学术研究，不公开传播
4. **默认账号**：admin / admin123
5. **情感分析阈值**：
   - 正面：score > 0.6
   - 中性：0.4 ≤ score ≤ 0.6
   - 负面：score < 0.4

---

## bilibili-api-python 使用指南

### 概述
`bilibili-api-python` 是连接B站直播弹幕的核心库，用于实时监听直播间弹幕、礼物等事件。

**官方文档**：https://nemo2011.github.io/bilibili-api/
**GitHub**：https://github.com/Nemo2011/bilibili-api

### 安装

```bash
# 安装主库
pip install bilibili-api-python==17.4.1

# 必须安装一个异步HTTP客户端（三选一）
pip install aiohttp      # 推荐，支持WebSocket
pip install httpx        # 轻量，不支持WebSocket
pip install curl_cffi    # 最强TLS指纹伪装，抗风控
```

**优先级**：`curl_cffi` > `aiohttp` > `httpx`

**重要**：`httpx` 不支持 WebSocket，直播弹幕功能必须使用 `aiohttp` 或 `curl_cffi`

### 请求客户端选择

```python
from bilibili_api import select_client, request_settings

# 选择客户端
select_client("aiohttp")      # 推荐用于直播弹幕
select_client("curl_cffi")    # 抗风控场景

# curl_cffi 浏览器指纹伪装（可选）
request_settings.set("impersonate", "chrome131")

# 设置代理（可选，遇到412错误时使用）
request_settings.set_proxy("http://127.0.0.1:7890")
```

### 直播弹幕监听

```python
from bilibili_api import live, sync

room = live.LiveDanmaku(房间号)

@room.on('DANMU_MSG')
async def on_danmaku(event):
    """收到弹幕"""
    info = event["data"]["info"]
    content = info[1]           # 弹幕内容
    user_name = info[2][1]      # 用户名
    print(f"{user_name}: {content}")

@room.on('SEND_GIFT')
async def on_gift(event):
    """收到礼物"""
    data = event["data"]["data"]
    print(f"{data['uname']} 送出 {data['giftName']} x{data['num']}")

# 启动连接
sync(room.connect())

# 或使用 asyncio
import asyncio
asyncio.run(room.connect())
```

### 获取直播间信息（需要登录凭据）

```python
from bilibili_api import live, Credential, sync

credential = Credential(
    sessdata="xxx",    # Cookie中的SESSDATA
    bili_jct="xxx",    # Cookie中的bili_jct
    buvid3="xxx"       # Cookie中的buvid3
)

room = live.LiveRoom(房间号, credential=credential)
info = sync(room.get_room_info())
```

### 常用事件类型

| 事件名 | 说明 |
|-------|------|
| `DANMU_MSG` | 弹幕消息 |
| `SEND_GIFT` | 礼物赠送 |
| `INTERACT_WORD` | 用户进入直播间 |
| `LIKE_INFO_V3_CLICK` | 用户点赞 |
| `STOP_LIVE_ROOM_LIST` | 停播房间列表 |
| `LOG_IN_NOTICE` | 登录提示 |

### 注意事项

1. **WebSocket 支持**：仅 `aiohttp` 和 `curl_cffi` 支持，`httpx` 不支持
2. **412 错误**：表示IP被限流，需要配置代理或等待
3. **登录凭据**：部分API需要登录才能使用（如获取用户昵称）
4. **房间号**：支持短号和真实房间号，库会自动转换
5. **异步设计**：库全部使用 async/await，需要配合 asyncio 使用

### 测试脚本

项目已包含测试脚本 `backend/test_bilibili_live.py`：

```bash
cd backend
python test_bilibili_live.py <直播间ID> --client aiohttp
```

---

## 待实现功能清单

### 前端页面
- [ ] Home.vue - 首页仪表盘
- [ ] Videos.vue - 视频数据查询
- [ ] Comments.vue - 评论分析
- [ ] Keywords.vue - 热词分析
- [ ] Trends.vue - 趋势分析
- [ ] Authors.vue - UP主分析
- [ ] Live.vue - 直播弹幕分析
- [ ] Prediction.vue - ML预测
- [ ] Admin.vue - 管理员后台
- [ ] Profile.vue - 个人中心
- [ ] Register.vue - 注册页面

### 后端功能
- [ ] 完善统计分析API
- [ ] 直播弹幕WebSocket服务
- [ ] 数据导出功能

### 大数据模块
- [ ] streaming/ - Kafka + Spark Streaming
- [ ] data_warehouse/ - 数据仓库ETL
- [ ] ml/ - 机器学习模型训练

---

## 项目创新点

1. **实时流处理架构**：Kafka + Spark Streaming，实现秒级数据处理
2. **数据仓库分层设计**：ODS→DWD→DWS→ADS 四层架构
3. **机器学习应用**：热度预测 + UP主聚类 + 内容推荐
4. **直播弹幕实时分析**：WebSocket实时连接，NLP流式处理
5. **多维度分析**：播放量、互动率、情感等多指标综合分析
6. **完整系统架构**：前后端分离 + 用户权限 + 管理后台
