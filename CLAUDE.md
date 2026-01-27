# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## 项目概述

**项目名称**：基于Spark Streaming的B站视频内容趋势分析系统

**项目类型**：大数据专业毕业设计

**项目定位**：一个具有大数据专业特色的数据分析系统，采用前后端分离架构，支持B站视频数据采集、实时流处理、数据仓库、机器学习分析和可视化展示。

**核心特色**：
1. DWD→DWS 轻量级数据仓库分层设计
2. 实时直播弹幕分析（WebSocket + NLP）
3. 视频数据采集与情感分析
4. 前后端分离架构 + 用户权限管理

**待实现特色**：
- Kafka + Spark Streaming 实时流处理
- XGBoost热度预测 + TF-IDF内容推荐

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
| Scikit-learn | TF-IDF推荐 |
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
│   │   ├── views/              # 页面组件
│   │   │   ├── Login.vue       # 登录页面（完成）
│   │   │   ├── Register.vue    # 注册页面（完成）
│   │   │   ├── Home.vue        # 首页仪表盘（完成）
│   │   │   └── VideoList.vue   # 视频列表页（卡片网格+详情弹窗）
│   │   ├── components/         # 公共组件
│   │   │   ├── common/
│   │   │   │   └── Layout.vue  # 全局布局
│   │   │   └── video/          # 视频相关组件
│   │   │       ├── VideoCard.vue          # 视频卡片组件
│   │   │       ├── VideoPlayer.vue        # B站嵌入式播放器
│   │   │       ├── VideoDetailDialog.vue  # 视频详情弹窗
│   │   │       └── CommentList.vue        # 评论列表组件
│   │   ├── api/                # API请求封装
│   │   │   ├── index.js        # Axios实例
│   │   │   ├── auth.js         # 认证API
│   │   │   └── videos.js       # 视频数据API
│   │   ├── store/              # Pinia状态管理
│   │   │   └── user.js          # 用户状态
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
│   │   │   ├── statistics.py   # 统计分析（含数仓优化接口）
│   │   │   ├── admin.py        # 管理员功能（含ETL管理）
│   │   │   └── live.py         # 直播弹幕分析 WebSocket
│   │   ├── core/               # 核心配置
│   │   │   ├── config.py       # 应用配置
│   │   │   ├── database.py     # 数据库连接
│   │   │   └── security.py     # JWT认证
│   │   ├── models/             # 数据模型
│   │   │   ├── models.py       # SQLAlchemy模型
│   │   │   └── warehouse.py    # 数仓模型（DWD/DWS层）
│   │   ├── etl/                # 数据仓库ETL模块
│   │   │   ├── base.py         # ETL基类
│   │   │   ├── dwd_tasks.py    # DWD层ETL任务
│   │   │   ├── dws_tasks.py    # DWS层ETL任务
│   │   │   └── scheduler.py    # ETL调度器
│   │   ├── services/           # 业务服务
│   │   │   ├── crawler.py      # B站数据采集
│   │   │   ├── crawl_service.py # 采集服务层
│   │   │   ├── nlp.py          # NLP分析（情感分析、词云）
│   │   │   ├── live_client.py  # B站直播弹幕客户端封装
│   │   │   └── analyzer.py     # 数据分析
│   │   └── tasks/              # 定时任务
│   │       └── scheduler.py    # 采集定时调度（定时采集+热词更新）
│   ├── tests/                  # 测试脚本目录
│   │   ├── test_etl.py         # ETL 测试脚本
│   │   ├── test_websocket.py   # WebSocket 测试脚本
│   │   └── test_crawl_service.py # 采集服务测试脚本
│   ├── main.py                 # 应用入口
│   └── requirements.txt
│
├── docs/                       # 文档
│   └── database.sql            # 数据库初始化脚本
│
├── CLAUDE.md                   # 项目说明（本文件）
└── README.md
```

**注意：以下目录在文档中规划但尚未创建：**
- `streaming/` - Kafka + Spark Streaming（待实现）
- `ml/` - 机器学习模块（待实现）
- `data_warehouse/` - 已集成到 `backend/app/etl/`

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
| 4 | 视频数据 | VideoList.vue | 用户 | 视频卡片网格、详情弹窗（含播放器、评论） |
| 5 | 评论分析 | Comments.vue | 用户 | 全局评论聚合分析 |
| 6 | 热词分析 | Keywords.vue | 用户 | 全局热词聚合分析 |
| 7 | 直播分析 | Live.vue | 用户 | **实时弹幕分析（亮点）** |
| 8 | ML预测 | Prediction.vue | 用户 | 热度预测、相似推荐 |
| 9 | 管理后台 | Admin.vue | 管理员 | 用户管理、采集控制 |
| 10 | 个人中心 | Profile.vue | 用户 | 个人信息、修改密码 |

### 核心页面说明

#### 首页仪表盘 (Home.vue)
- 核心指标卡片：视频总数、总播放量、总评论数、总弹幕数、平均互动率
- 数据趋势图：播放量/新增视频/评论数（支持7天/30天切换）
- 分区分布饼图、热门视频TOP10、情感分析概览、今日热词云
- 系统状态（仅管理员可见）

#### 视频数据 (VideoList.vue)
- 已实现：视频卡片网格布局、关键词/分区/排序筛选、分页
- 已实现：点击卡片打开详情弹窗（B站嵌入式播放器、数据统计、评论列表）
- 待实现：导出Excel、更多筛选项（日期范围）

#### 评论分析 (Comments.vue)
- 筛选栏：时间范围、视频分区、情感类型、关键词搜索
- 情感统计卡片 + 分布饼图 + 趋势折线图
- 评论词云（颜色区分情感）、评论列表（支持分页、导出）

#### 热词分析 (Keywords.vue)
- 筛选栏：时间范围、视频分区、词来源
- 热词统计卡片、热词词云、热词排行榜
- 热词趋势图、热词详情面板（来源分布、关联视频）

#### 直播分析 (Live.vue) - 亮点功能
- 直播间输入：输入房间ID，连接/断开按钮
- 实时弹幕流：滚动显示，每条带情感标签
- 统计卡片：弹幕数、弹幕速率、平均情感分、礼物数
- 情感分布饼图 + 情感趋势图 + 实时词云

#### ML预测 (Prediction.vue)
- 热度预测：选择视频，预测7天后播放量，展示特征重要性
- 相似视频推荐：选择视频，展示TOP10相似视频
- 预测历史记录、模型信息面板

#### 管理员后台 (Admin.vue)
- 用户管理：列表、启用/禁用、修改角色
- 采集任务管理：启动/停止、配置参数、查看日志
- 系统状态监控：MySQL/Redis/Kafka连接状态
- 数据统计、数据清理

#### 个人中心 (Profile.vue)
- 个人信息：用户名、邮箱、角色、注册时间
- 修改密码

---

## 后端API接口（实际实现）

### 用户认证 (/api/auth)
```
POST /register     # 用户注册
POST /login        # 用户登录，返回JWT
GET  /profile      # 获取当前用户信息
PUT  /password     # 修改密码
```

### 视频数据 (/api/videos)
```
GET  /             # 视频列表（分页、筛选）
GET  /{bvid}       # 视频详情
GET  /{bvid}/comments  # 视频评论列表（含情感标签）
```

### 统计分析 (/api/statistics)
```
GET  /overview        # 总览数据（卡片）
GET  /trends          # 趋势数据（折线图）
GET  /categories      # 分区统计（饼图）
GET  /keywords        # 热词数据（词云）
GET  /sentiment       # 情感分析统计
GET  /top-videos      # 热门视频榜
```

### ML预测 (/api/ml)
```
POST /predict      # 视频热度预测
GET  /recommend/{bvid}  # 相似视频推荐
```

### 直播分析 (/api/live)
```
WebSocket /ws/{room_id}  # 直播弹幕实时分析
GET  /rooms              # 获取活跃直播间列表
GET  /rooms/{room_id}/status  # 获取直播间连接状态
```

#### WebSocket 消息格式

**服务端推送消息类型：**

| type | 说明 | 频率 |
|------|------|------|
| status | 连接状态 | 连接时 |
| danmaku | 弹幕消息（含情感分析） | 实时 |
| gift | 礼物消息 | 实时 |
| interact | 互动消息（进场/点赞） | 实时 |
| stats | 统计数据 | 每5秒 |
| wordcloud | 词云数据 | 每10秒 |

**弹幕消息示例：**
```json
{
  "type": "danmaku",
  "data": {
    "content": "弹幕内容",
    "user_name": "用户名",
    "user_id": 12345,
    "timestamp": "2024-01-01T12:00:00",
    "sentiment_score": 0.75,
    "sentiment_label": "positive"
  }
}
```

**统计数据示例：**
```json
{
  "type": "stats",
  "data": {
    "total_danmaku": 100,
    "total_gift": 5,
    "danmaku_rate": 12.5,
    "avg_sentiment": 0.65,
    "sentiment_dist": {"positive": 40, "neutral": 35, "negative": 25}
  }
}
```

**词云数据示例：**
```json
{
  "type": "wordcloud",
  "data": [
    {"name": "主播", "value": 50},
    {"name": "好看", "value": 30}
  ]
}
```

### 数据导出 (/api/export)（未实现）
```
GET  /videos       # 导出视频数据Excel（未实现）
GET  /keywords     # 导出热词数据Excel（未实现）
```

### 管理员 (/api/admin)
```
GET  /users           # 用户列表
GET  /crawl/logs      # 采集日志
GET  /crawl/status    # 获取最近采集任务状态
POST /crawl/start     # 启动采集任务（已实现，支持配置视频数和评论数）
POST /crawl/stop      # 停止采集任务（未实现）
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

## 数据仓库分层设计（实际实现）

```
┌─────────────────────────────────────────────────────────────┐
│ DWS层（汇总数据层）- 预聚合，直接供API查询                    │
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐          │
│ │dws_stats_    │ │dws_category_ │ │dws_sentiment_│          │
│ │   daily      │ │   daily      │ │   daily      │          │
│ │ 每日全局统计  │ │ 每日分区统计  │ │ 每日情感统计  │          │
│ └──────────────┘ └──────────────┘ └──────────────┘          │
│ ┌──────────────┐                                            │
│ │dws_video_    │                                            │
│ │   trend      │ 视频热度趋势                                │
│ └──────────────┘                                            │
├─────────────────────────────────────────────────────────────┤
│ DWD层（明细数据层）- 清洗后的每日快照                         │
│ ┌───────────────────┐ ┌───────────────────┐                 │
│ │ dwd_video_snapshot│ │ dwd_comment_daily │                 │
│ │ 视频每日快照       │ │ 评论每日增量       │                 │
│ └───────────────────┘ └───────────────────┘                 │
├─────────────────────────────────────────────────────────────┤
│ ODS层（现有表作为数据源）                                     │
│ ┌──────┐ ┌──────────┐ ┌──────────┐                          │
│ │videos│ │ comments │ │ keywords │                          │
│ └──────┘ └──────────┘ └──────────┘                          │
└─────────────────────────────────────────────────────────────┘
```

**说明**：实际采用轻量级两层设计（DWD + DWS），ODS层复用现有业务表。

---

## 机器学习模型（待实现）

### 1. 视频热度预测（XGBoost）
- **输入特征**：like_rate, coin_rate, publish_hour, category, title_length
- **预测目标**：7天后播放量
- **模型文件**：ml/models/xgboost_model.pkl（待创建）

### 2. 内容推荐（TF-IDF）
- **方法**：基于视频标题的TF-IDF向量余弦相似度
- **模型文件**：ml/models/tfidf_vectorizer.pkl（待创建）

**注意**：ml/ 目录尚未创建，以上为规划设计。

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

### 数据采集
```bash
cd backend
python tests/test_crawl_service.py    # 采集数据（带情感分析和日志）
python 补充情感分析.py                 # 对已有评论补充情感分析
```

**采集配置：**
- 每个视频采集 100 条评论
- 采集间隔 2 秒（符合B站API限制）
- 建议每天运行 1-2 次

### 数据仓库ETL
```bash
cd backend

# 测试ETL执行
python tests/test_etl.py

# 通过API手动触发ETL（需要管理员权限）
# POST /api/admin/etl/run-sync
# Body: {"stat_date": "2026-01-11"}  # 可选，默认昨日

# 历史数据回填
# POST /api/admin/etl/backfill
# Body: {"start_date": "2026-01-01", "end_date": "2026-01-10"}
```

**ETL调度：**
- 自动调度：每天凌晨2点自动执行
- 手动触发：通过 `/api/admin/etl/run` 或 `/api/admin/etl/run-sync`
- 历史回填：通过 `/api/admin/etl/backfill`，最多90天

**数仓表说明：**
| 表名 | 层级 | 用途 |
|------|------|------|
| dwd_video_snapshot | DWD | 视频每日快照，保留历史统计数据 |
| dwd_comment_daily | DWD | 评论每日增量，含情感标签 |
| dws_stats_daily | DWS | 每日全局统计（视频数、播放量等） |
| dws_category_daily | DWS | 每日分区统计 |
| dws_sentiment_daily | DWS | 每日情感分布统计 |
| dws_video_trend | DWS | 视频热度趋势（7日增长率） |

**优化接口：**
| 接口 | 说明 |
|------|------|
| GET /api/statistics/dw/overview | 总览统计（数仓优化版） |
| GET /api/statistics/dw/trends | 趋势数据（数仓优化版） |
| GET /api/statistics/dw/categories | 分区统计（数仓优化版） |
| GET /api/statistics/dw/sentiment | 情感统计（数仓优化版） |
| GET /api/statistics/dw/video-trends | 视频热度排行 |
| GET /api/statistics/dw/video/{bvid}/history | 单视频历史趋势 |

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
```

### 直播弹幕功能测试
```bash
cd backend

# 1. 启动后端服务
python main.py

# 2. 新终端运行 WebSocket 测试
python tests/test_websocket.py <直播间ID>
# 示例: python tests/test_websocket.py 22625027

# 测试输出说明:
# [弹幕][+0.75] 用户名: 弹幕内容   (+正面 =中性 -负面)
# --- 统计 --- (每5秒更新)
# [词云] TOP10: 词1(频次) | 词2(频次)... (每10秒更新)
```

---

## 环境变量配置

后端 `backend/.env` 文件：
```
DATABASE_URL=mysql+pymysql://root:password@localhost:3306/bilibili_analyzer
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-secret-key-here
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
BILIBILI_COOKIE=your-bilibili-cookie-here
```

### B站 Cookie 配置（重要）

**为什么需要 Cookie？**
- B站评论 API 在未登录状态下有严格限制，每个视频只返回约 3 条评论
- 配置 Cookie 后可正常获取完整评论数据

**获取方法：**
1. 用浏览器登录 B站 (bilibili.com)
2. 按 F12 打开开发者工具 → Network（网络）标签
3. 刷新页面，点击任意请求
4. 在 Request Headers 中找到 `Cookie` 字段
5. 复制完整 Cookie 字符串到 `.env` 文件

**配置示例：**
```
BILIBILI_COOKIE=buvid3=xxx; SESSDATA=xxx; bili_jct=xxx; ...
```

**注意事项：**
- Cookie 有效期通常 1-3 个月，过期后需重新获取
- 配置后需重启后端服务生效
- 不要泄露你的 Cookie（包含登录凭证）

---

## 开发注意事项

1. **B站API频率限制**：约30次/分钟，采集间隔建议2秒以上
2. **B站评论API限制**：未登录状态只返回约3条评论，需配置Cookie才能获取完整数据
3. **Kafka和Spark**：需要Java 8+环境
4. **数据合规**：数据仅用于学术研究，不公开传播
5. **默认账号**：admin / admin123
6. **情感分析阈值**：
   - 正面：score > 0.6
   - 中性：0.4 ≤ score ≤ 0.6
   - 负面：score < 0.4
7. 前端开发时，严格遵循前端项目文件夹中的 STYLE_RULE.md 文件中的规范

---

## bilibili-api-python 使用指南

### 安装

```bash
pip install bilibili-api-python==17.4.1
pip install aiohttp      # 必须，支持WebSocket
```

**重要**：`httpx` 不支持 WebSocket，直播弹幕功能必须使用 `aiohttp` 或 `curl_cffi`

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
```

### 常用事件类型

| 事件名 | 说明 |
|-------|------|
| `DANMU_MSG` | 弹幕消息 |
| `SEND_GIFT` | 礼物赠送 |
| `INTERACT_WORD` | 用户进入直播间 |
| `LIKE_INFO_V3_CLICK` | 用户点赞 |

### 注意事项

1. **412 错误**：表示IP被限流，需要配置代理或等待
2. **房间号**：支持短号和真实房间号，库会自动转换
3. **异步设计**：库全部使用 async/await，需要配合 asyncio 使用

### 测试脚本

项目已包含测试脚本目录 `backend/tests/`：

```bash
cd backend
python tests/test_websocket.py <直播间ID>   # WebSocket 测试
python tests/test_etl.py                    # ETL 测试
python tests/test_crawl_service.py          # 采集服务测试
```

---

## 功能完成情况

### 前端页面（6/10 完成）
- [x] Login.vue - 登录页面（完整实现）
- [x] Register.vue - 注册页面（完整实现）
- [x] Home.vue - 首页仪表盘（基础结构）
- [x] VideoList.vue - 视频数据查询（卡片网格+详情弹窗+播放器+评论）
- [ ] Comments.vue - 评论分析（未实现）
- [ ] Keywords.vue - 热词分析（未实现）
- [x] Live.vue - 直播弹幕分析（完整实现）
- [ ] Prediction.vue - ML预测（未实现）
- [x] Admin.vue - 管理员后台（完整实现）
- [ ] Profile.vue - 个人中心（未实现）

**Admin.vue 功能详情：**

*服务状态监控（已完成）：*
- [x] MySQL/Redis/Kafka/ETL调度器 状态卡片
- [x] B站账号登录状态显示
- [x] 自动检测服务可用性

*数据采集模块（已完成）：*
- [x] 可配置采集视频数和每视频评论数
- [x] 启动采集任务按钮
- [x] 采集日志表格（状态、视频数、评论数、错误信息）
- [x] 日志刷新功能

*ETL调度管理（已完成）：*
- [x] 启动/停止ETL调度器
- [x] 手动执行ETL
- [x] 历史数据回填（支持日期范围选择）
- [x] 调度状态和下次执行时间显示

*用户管理（已完成）：*
- [x] 用户列表表格
- [x] 显示用户角色（管理员/普通用户）

**Live.vue 功能详情：**

*多房间监控（已完成）：*
- [x] 支持同时监控最多 4 个直播间
- [x] 房间标签页切换
- [x] 房间添加/移除管理
- [x] Kafka / Redis / B站登录状态显示
- [x] 支持登录认证连接（配置Cookie后自动使用）

*单房间详情视图（已完成）：*
- [x] WebSocket 实时连接 B站直播间
- [x] 实时弹幕流（带情感分析标签）
- [x] 统计卡片（弹幕数、速率、平均情感分、礼物数）
- [x] 情感分布饼图
- [x] 情感趋势折线图
- [x] 实时词云（每10秒更新）

*全局对比视图（已完成）：*
- [x] 房间热度排行（按弹幕数量排序，金银铜牌样式）
- [x] 多房间情感趋势对比折线图
- [x] 跨房间热词聚合词云（TOP50）

*基础能力（已完成）：*
- [x] 自动重连机制
- [x] 响应式窗口适配
- [x] 图表自适应 resize

**前端其他模块：**
- [x] API基础框架 (axios实例、拦截器)
- [x] 认证API封装 (auth.js)
- [x] Live API封装 (live.js - WebSocket连接地址、HTTP接口)
- [x] Admin API封装 (admin.js - 采集、ETL、用户管理接口)
- [x] WebSocket工具类 (utils/websocket.js - 连接管理、事件分发、自动重连)
- [ ] 其他API模块（videos, statistics）
- [x] 状态管理 (Pinia user store)
- [x] 公共组件 (Layout)
- [x] Vite配置（WebSocket代理支持）
- [x] 路由守卫（管理员权限检查）

### 后端功能（约90% 完成）
- [x] 用户认证API（注册、登录、JWT）
- [x] 视频数据API（列表、详情）
- [x] 视频评论API（含情感标签）
- [x] 统计分析API（原始版 + 数仓优化版 /dw/*）
- [x] 直播弹幕WebSocket服务（含NLP情感分析、词云）
- [x] 数据采集模块（BilibiliCrawler + CrawlService，含情感分析）
- [x] NLP分析服务（情感分析、分词、词云）
- [x] 数据仓库ETL模块（DWD + DWS 两层）
- [x] ETL调度器（每日自动执行、手动触发、历史回填）
- [x] 定时采集任务调度 (tasks/scheduler.py)
- [x] 管理员采集控制接口（/crawl/start 完整实现，/crawl/status 已实现）
- [ ] 数据导出功能（未实现）
- [ ] 直播数据持久化存储（可选扩展）

**直播模块后端功能：**
- [x] 多房间 WebSocket 连接管理
- [x] 弹幕数据发送到 Kafka（供 Spark 处理）
- [x] 礼物数据发送到 Kafka
- [x] Redis 实时统计存储（可选）
- [x] 服务状态检测接口 `/live/status/services`

**直播模块可选扩展功能：**
- [ ] 在弹幕流中显示礼物消息（当前仅统计）
- [ ] 在弹幕流中显示互动消息（进场、点赞）
- [ ] 热门直播间推荐列表（后端接口已有）
- [ ] 直播历史分析记录查询
- [ ] 高频用户排行榜
- [ ] 弹幕关键词提醒功能

### 大数据模块
- [x] 数据仓库ETL（已集成到 backend/app/etl/）
- [ ] streaming/ - Kafka + Spark Streaming（目录不存在）
- [ ] ml/ - 机器学习模型训练（目录不存在）

---

## 项目创新点

1. **数据仓库分层设计**：DWD→DWS 两层架构，预聚合优化查询性能
2. **直播弹幕实时分析**：WebSocket实时连接，NLP流式处理
3. **多维度分析**：播放量、互动率、情感等多指标综合分析
4. **完整系统架构**：前后端分离 + 用户权限 + 管理后台

### 待实现的创新点
- Kafka + Spark Streaming 实时流处理
- XGBoost热度预测 + TF-IDF内容推荐
