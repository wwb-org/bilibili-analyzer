# Bilibili 接口文档查阅入口

本文档用于开发新功能时快速定位 Bilibili 相关接口说明与本项目接口入口。

## 本项目后端接口文档
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

启动后端后直接查阅参数、请求体和返回结构，优先以本项目 OpenAPI 为准。

## Bilibili 第三方 Python SDK（项目当前主要依赖）
- 官方文档主页: https://nemo2011.github.io/bilibili-api/
- GitHub 仓库: https://github.com/Nemo2011/bilibili-api
- PyPI 包页面: https://pypi.org/project/bilibili-api-python/

适用场景：
- 直播弹幕连接与事件监听（`LiveDanmaku`）
- 常见视频、用户、评论相关能力封装

## 非官方接口资料（补充）
- Bilibili-API-collect: https://socialsisteryi.github.io/bilibili-API-collect/

说明：
- 该资料为社区维护，字段可能变更，仅作排查与对照参考。
- 涉及生产逻辑时，优先验证当前请求返回并做好异常兜底。

## 本项目代码定位（优先从这里查）
- 采集与评论：`backend/app/services/crawler.py`
- 采集服务编排：`backend/app/services/crawl_service.py`
- 直播弹幕客户端：`backend/app/services/live_client.py`
- 直播 WebSocket API：`backend/app/api/live.py`

## 使用建议
1. 先看 `http://localhost:8000/docs` 明确本项目接口是否已覆盖需求。
2. 再查 SDK 文档确认外部能力与参数。
3. 最后用测试脚本验证：
   - `python backend/tests/test_crawl_service.py`
   - `python backend/tests/test_websocket.py <room_id>`
