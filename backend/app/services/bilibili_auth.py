"""
B站账号认证服务

提供Cookie验证和管理功能：
- 验证Cookie是否有效（调用B站API）
- 更新Cookie配置（内存 + .env文件持久化）
- 获取当前Cookie状态
"""
import os
import re
import requests
from typing import Dict, Any, Optional
from pathlib import Path

from app.core.config import settings, get_settings


# 运行时Cookie存储（覆盖.env配置）
_runtime_cookie: Optional[str] = None

# B站用户信息API
BILIBILI_NAV_API = "https://api.bilibili.com/x/web-interface/nav"

# .env文件路径
ENV_FILE_PATH = Path(__file__).parent.parent.parent / ".env"


def get_current_cookie() -> str:
    """
    获取当前使用的Cookie

    优先使用运行时Cookie，其次使用.env配置
    """
    global _runtime_cookie
    if _runtime_cookie is not None:
        return _runtime_cookie
    return settings.BILIBILI_COOKIE


def validate_cookie(cookie_str: str) -> Dict[str, Any]:
    """
    验证B站Cookie是否有效

    调用B站导航栏API获取用户信息

    Args:
        cookie_str: Cookie字符串

    Returns:
        验证结果字典，包含：
        - valid: 是否有效
        - logged_in: 是否已登录
        - username: 用户名
        - uid: 用户ID
        - avatar: 头像URL
        - message: 提示信息
    """
    if not cookie_str or not cookie_str.strip():
        return {
            "valid": False,
            "logged_in": False,
            "message": "Cookie为空"
        }

    # 检查必要字段
    cookie_str = cookie_str.strip()
    if "SESSDATA" not in cookie_str:
        return {
            "valid": False,
            "logged_in": False,
            "message": "Cookie中缺少SESSDATA字段"
        }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.bilibili.com",
        "Cookie": cookie_str
    }

    try:
        resp = requests.get(BILIBILI_NAV_API, headers=headers, timeout=10)
        data = resp.json()

        if data.get("code") == 0:
            user_info = data.get("data", {})
            is_login = user_info.get("isLogin", False)

            if is_login:
                return {
                    "valid": True,
                    "logged_in": True,
                    "username": user_info.get("uname", ""),
                    "uid": user_info.get("mid", 0),
                    "avatar": user_info.get("face", ""),
                    "vip_type": user_info.get("vipType", 0),
                    "level": user_info.get("level_info", {}).get("current_level", 0),
                    "message": "Cookie有效"
                }
            else:
                return {
                    "valid": False,
                    "logged_in": False,
                    "message": "Cookie已过期或无效"
                }
        else:
            return {
                "valid": False,
                "logged_in": False,
                "message": data.get("message", "验证失败")
            }
    except requests.exceptions.Timeout:
        return {
            "valid": False,
            "logged_in": False,
            "message": "验证请求超时，请稍后重试"
        }
    except requests.exceptions.RequestException as e:
        return {
            "valid": False,
            "logged_in": False,
            "message": f"网络请求失败: {str(e)}"
        }
    except Exception as e:
        return {
            "valid": False,
            "logged_in": False,
            "message": f"验证异常: {str(e)}"
        }


def update_cookie_in_env(cookie_str: str) -> bool:
    """
    更新.env文件中的BILIBILI_COOKIE配置

    Args:
        cookie_str: 新的Cookie字符串

    Returns:
        是否更新成功
    """
    global _runtime_cookie

    try:
        # 更新运行时Cookie
        _runtime_cookie = cookie_str.strip()

        # 读取现有.env内容
        env_content = ""
        if ENV_FILE_PATH.exists():
            with open(ENV_FILE_PATH, "r", encoding="utf-8") as f:
                env_content = f.read()

        # 转义Cookie中的特殊字符（用于正则替换）
        escaped_cookie = cookie_str.strip().replace("\\", "\\\\")

        # 检查是否已存在BILIBILI_COOKIE配置
        pattern = r'^BILIBILI_COOKIE=.*$'
        new_line = f'BILIBILI_COOKIE={escaped_cookie}'

        if re.search(pattern, env_content, re.MULTILINE):
            # 替换现有配置
            env_content = re.sub(pattern, new_line, env_content, flags=re.MULTILINE)
        else:
            # 添加新配置
            if env_content and not env_content.endswith("\n"):
                env_content += "\n"
            env_content += new_line + "\n"

        # 写入.env文件
        with open(ENV_FILE_PATH, "w", encoding="utf-8") as f:
            f.write(env_content)

        return True
    except Exception as e:
        print(f"[BilibiliAuth] 更新.env文件失败: {e}")
        return False


def get_cookie_status() -> Dict[str, Any]:
    """
    获取当前Cookie状态

    自动验证当前配置的Cookie是否有效

    Returns:
        状态字典，包含验证结果和用户信息
    """
    cookie = get_current_cookie()

    if not cookie:
        return {
            "configured": False,
            "valid": False,
            "logged_in": False,
            "message": "未配置Cookie"
        }

    # 验证Cookie
    result = validate_cookie(cookie)
    result["configured"] = True

    return result


def clear_runtime_cookie():
    """清除运行时Cookie，恢复使用.env配置"""
    global _runtime_cookie
    _runtime_cookie = None
