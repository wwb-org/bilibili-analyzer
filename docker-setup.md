# Docker 安装配置指南

## 一、安装 Docker Desktop

### 1. 启用 WSL2（Windows Subsystem for Linux）

以管理员身份运行 PowerShell，执行以下命令：

```powershell
# 启用 WSL
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart

# 启用虚拟机平台
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart

# 重启电脑
```

重启后，继续执行：

```powershell
# 设置 WSL2 为默认版本
wsl --set-default-version 2
```

### 2. 下载并安装 Docker Desktop

**下载地址：**
- 官网：https://www.docker.com/products/docker-desktop/
- 直接下载：https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe

**安装选项：**
- ✅ Use WSL 2 instead of Hyper-V（推荐）
- ✅ Add shortcut to desktop

**安装后：**
- 首次启动会要求接受服务条款
- 可能需要再次重启电脑
- 启动后在系统托盘会看到Docker图标

### 3. 验证安装

打开 PowerShell 或 CMD，执行：

```bash
docker --version
docker-compose --version
```

应该看到类似输出：
```
Docker version 29.1.3, build f52814d
Docker Compose version v5.0.1
```

## 二、配置 Docker

### 1. Docker Desktop 设置

打开 Docker Desktop → Settings：

**General：**
- ✅ Start Docker Desktop when you log in
- ✅ Use WSL 2 based engine

**Resources：**

- CPUs: 4（根据你的电脑配置）
- Memory: 4GB（建议最少4GB）
- Swap: 1GB
- Disk image size: 60GB

**Docker Engine（可选配置国内镜像加速）：**

```json
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com"
  ]
}
```

### 2. 测试 Docker

```bash
# 运行测试容器
docker run hello-world

# 如果看到 "Hello from Docker!" 说明安装成功
```

## 三、为项目配置 Docker Compose

### 1. 创建 docker-compose.yml

在项目根目录创建 `docker-compose.yml` 文件（已在下一步提供）

### 2. 启动服务

```bash
# 进入项目目录
cd C:\Users\hxn\Desktop\Code\bilibili-analyzer

# 启动所有服务（后台运行）
docker-compose up -d

# 查看运行状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 3. 常用命令

```bash
# 启动单个服务
docker-compose up -d redis

# 重启服务
docker-compose restart redis

# 进入容器
docker exec -it bilibili-analyzer-redis-1 redis-cli

# 查看容器日志
docker-compose logs redis

# 清理所有容器和数据
docker-compose down -v
```

## 四、验证服务

### Redis
```bash
# 测试 Redis 连接
docker exec -it bilibili-analyzer-redis-1 redis-cli ping
# 应该返回：PONG
```

### Kafka
```bash
# 查看 Kafka topics
docker exec -it bilibili-analyzer-kafka-1 kafka-topics --list --bootstrap-server localhost:9092
```

## 五、故障排查

### 问题1：Docker Desktop 启动失败
- 确认已启用 WSL2
- 确认 BIOS 中已启用虚拟化（Intel VT-x 或 AMD-V）
- 尝试以管理员身份运行 Docker Desktop

### 问题2：容器无法启动
- 检查端口是否被占用：`netstat -ano | findstr :6379`
- 查看容器日志：`docker-compose logs <service-name>`

### 问题3：网络连接问题
- 检查防火墙设置
- 尝试配置镜像加速器
- 检查 Docker 网络：`docker network ls`

### 问题4：WSL2 内存占用过高
创建 `%USERPROFILE%\.wslconfig` 文件：
```ini
[wsl2]
memory=4GB
processors=4
swap=1GB
```

## 六、项目集成

### 修改后端配置

编辑 `backend/.env` 或 `backend/app/core/config.py`：

```python
# Redis配置（Docker）
REDIS_URL = "redis://localhost:6379/0"

# Kafka配置（Docker）
KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"

# MySQL（如果也用Docker）
DATABASE_URL = "mysql+pymysql://root:123456@localhost:3306/bilibili_analyzer"
```

### 测试连接

```bash
cd backend
python -c "import redis; r = redis.from_url('redis://localhost:6379/0'); print(r.ping())"
# 应该输出：True
```

## 七、资源占用参考

**最小配置：**
- Redis: ~50MB 内存
- Kafka + Zookeeper: ~1GB 内存
- 总计: ~1.5GB 内存

**推荐配置：**
- 电脑内存: 8GB+
- 分配给Docker: 4GB
- 剩余给Windows和开发工具: 4GB

## 八、下一步

1. 安装 Docker Desktop
2. 创建 docker-compose.yml（见下一个文件）
3. 启动服务：`docker-compose up -d`
4. 修改后端配置连接到 Docker 服务
5. 测试功能是否正常