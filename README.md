# B站视频内容趋势分析系统

基于 Vue3 + FastAPI 的 B站视频数据分析与可视化系统。
test

## 项目结构

```
bilibili-analyzer/
├── frontend/          # Vue3 前端项目
├── backend/           # FastAPI 后端项目
└── docs/              # 文档和SQL脚本
```

## 快速开始

### 1. 数据库配置

```bash
# 导入数据库
mysql -u root -p < docs/database.sql
```

### 2. 后端启动

```bash
cd backend

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，配置数据库连接

# 启动服务
python main.py
```

后端地址: http://localhost:8000
API文档: http://localhost:8000/docs

### 3. 前端启动

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端地址: http://localhost:5173

## 默认账号

- 用户名: admin
- 密码: admin123

## 技术栈

**前端:** Vue3 + Vite + Element Plus + ECharts

**后端:** Python + FastAPI + SQLAlchemy + APScheduler

**数据库:** MySQL + Redis
