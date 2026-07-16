"""
API 网关服务层 — 统一管理外部 API 提供商（利于后续「接口管理」模块扩展）

设计原则：
  1. 每个 API 提供商注册为一个 ApiProvider，包含认证方式、端点、参数映射
  2. 调用方只需传入 provider_name + endpoint_name + params，无需关心底层 HTTP 细节
  3. 后续「接口管理」模块可直接读取 _PROVIDERS 注册表生成配置界面
  4. 密钥统一存储在 config/api_keys.json

使用示例：
    from app.services.api_gateway import api_gateway
    result = api_gateway.call("tmdb", "search_movie", {"keyword": "哪吒"})
"""

import json
import os
import urllib.parse
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Callable

import requests

_CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config")
_API_KEYS_PATH = os.path.join(_CONFIG_DIR, "api_keys.json")


def _load_api_keys():
    try:
        if os.path.exists(_API_KEYS_PATH):
            with open(_API_KEYS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _reload_api_keys():
    """重新加载密钥（供接口管理模块修改后调用）"""
    return _load_api_keys()


@dataclass
class ApiProvider:
    """API 提供商定义"""
    name: str                                    # 提供商标识，如 "tmdb"
    display_name: str                            # 显示名称，如 "TMDB电影"
    base_url: str                                # 基础 URL
    auth_type: str                               # "bearer" | "api_key" | "none"
    auth_header: str = "Authorization"           # 认证头名称
    auth_prefix: str = "Bearer"                  # 认证前缀
    api_key_config_path: str = ""                # api_keys.json 中的配置路径，如 "tmdb"
    description: str = ""                        # 描述
    endpoints: Dict[str, Dict] = field(default_factory=dict)  # 端点定义

    def get_auth_headers(self) -> Dict[str, str]:
        """获取认证请求头"""
        keys = _load_api_keys()
        provider_cfg = keys.get(self.api_key_config_path, {})
        api_key = provider_cfg.get("key", "")

        if not api_key:
            return {}

        if self.auth_type == "bearer":
            return {self.auth_header: f"{self.auth_prefix} {api_key}"}
        elif self.auth_type == "api_key":
            return {}
        return {}


# ====== 提供商定义注册表（后续「接口管理」模块可从此读取） ======

_PROVIDERS: Dict[str, ApiProvider] = {}


def register_provider(provider: ApiProvider):
    """注册 API 提供商"""
    _PROVIDERS[provider.name] = provider


def get_provider(name: str) -> Optional[ApiProvider]:
    """获取已注册的提供商"""
    return _PROVIDERS.get(name)


def list_providers() -> List[Dict]:
    """列出所有已注册的提供商（供接口管理模块使用）"""
    result = []
    for name, p in _PROVIDERS.items():
        result.append({
            "name": p.name,
            "display_name": p.display_name,
            "base_url": p.base_url,
            "auth_type": p.auth_type,
            "description": p.description,
            "endpoint_count": len(p.endpoints),
            "endpoints": list(p.endpoints.keys()),
        })
    return result


def get_provider_endpoints(name: str) -> List[Dict]:
    """获取指定提供商的所有端点定义（供接口管理模块使用）"""
    provider = _PROVIDERS.get(name)
    if not provider:
        return []
    result = []
    for ep_name, ep in provider.endpoints.items():
        result.append({
            "name": ep_name,
            "path": ep.get("path", ""),
            "method": ep.get("method", "GET"),
            "description": ep.get("description", ""),
            "params": ep.get("params", {}),
            "response_mapping": ep.get("response_mapping", {}),
        })
    return result


# ====== 统一调用入口 ======

class ApiGateway:
    """API 网关 — 统一的 API 调用入口"""

    def call(self, provider_name: str, endpoint_name: str,
             params: Dict[str, str] = None) -> Dict[str, Any]:
        """调用指定提供商的指定端点

        Args:
            provider_name: 提供商名称，如 "tmdb"
            endpoint_name: 端点名称，如 "search_movie"
            params: 参数，如 {"keyword": "哪吒"}

        Returns:
            {"success": True/False, "data": ..., "error": "..."}
        """
        provider = _PROVIDERS.get(provider_name)
        if not provider:
            return {"success": False, "error": f"未知的API提供商: {provider_name}"}

        endpoint = provider.endpoints.get(endpoint_name)
        if not endpoint:
            return {"success": False, "error": f"未知的端点: {provider_name}/{endpoint_name}"}

        params = params or {}

        try:
            # 构建 URL
            url = provider.base_url.rstrip("/") + endpoint["path"]

            # 填充路径参数（如 /movie/{movie_id}）
            for k, v in params.items():
                url = url.replace(f"{{{k}}}", urllib.parse.quote(str(v)))

            method = endpoint.get("method", "GET").upper()
            default_params = endpoint.get("params", {}).copy()

            # 合并参数
            merged_params = {**default_params, **params}
            # 移除已用于路径的参数
            merged_params = {k: v for k, v in merged_params.items()
                           if f"{{{k}}}" not in url}

            # 获取认证头
            headers = {
                "User-Agent": "DataFinderAgentOS/1.0",
                "Accept": "application/json",
            }
            auth_headers = provider.get_auth_headers()
            headers.update(auth_headers)

            # 如果是 api_key 认证类型，将密钥加入 params
            if provider.auth_type == "api_key":
                keys = _load_api_keys()
                provider_cfg = keys.get(provider.api_key_config_path, {})
                api_key = provider_cfg.get("key", "")
                param_name = provider_cfg.get("param_name", "key")
                merged_params[param_name] = api_key

            # 发起请求
            if method == "GET":
                resp = requests.get(url, params=merged_params,
                                   headers=headers, timeout=15)
            elif method == "POST":
                resp = requests.post(url, json=merged_params,
                                    headers=headers, timeout=15)
            else:
                return {"success": False, "error": f"不支持的HTTP方法: {method}"}

            if resp.status_code != 200:
                return {"success": False, "error": f"API返回错误: HTTP {resp.status_code}"}

            raw_data = resp.json()

            # 应用响应映射
            mapping = endpoint.get("response_mapping", {})
            if mapping:
                mapped = _apply_response_mapping(raw_data, mapping)
                return {"success": True, "data": mapped, "raw": raw_data}

            return {"success": True, "data": raw_data}

        except requests.exceptions.Timeout:
            return {"success": False, "error": "API请求超时"}
        except requests.exceptions.ConnectionError:
            return {"success": False, "error": "API连接失败，请检查网络"}
        except Exception as e:
            return {"success": False, "error": f"API调用异常: {str(e)[:200]}"}


def _apply_response_mapping(data, mapping: Dict) -> Any:
    """根据映射规则转换 API 响应数据"""
    result_type = mapping.get("_type", "dict")

    if result_type == "list":
        path = mapping.get("_path", "")
        items = _get_by_path(data, path) if path else data
        if not isinstance(items, list):
            items = [items] if items else []

        mapped_list = []
        item_mapping = mapping.get("_items", {})
        for item in items[:mapping.get("_limit", 20)]:
            mapped_item = {}
            for target_key, source_key in item_mapping.items():
                val = _get_by_path(item, source_key)
                mapped_item[target_key] = val if val else ""
            mapped_list.append(mapped_item)
        return mapped_list

    elif result_type == "dict":
        mapped = {}
        for target_key, source_key in mapping.items():
            if target_key.startswith("_"):
                continue
            val = _get_by_path(data, source_key)
            mapped[target_key] = val if val else ""
        return mapped

    return data


def _get_by_path(data, path: str):
    """按点分隔路径从嵌套字典/列表中取值，如 "result.data.0.title" """
    if not path:
        return data
    parts = path.split(".")
    current = data
    for p in parts:
        if current is None:
            return None
        if isinstance(current, dict):
            current = current.get(p)
        elif isinstance(current, list) and p.isdigit():
            idx = int(p)
            current = current[idx] if idx < len(current) else None
        else:
            return None
    return current


# ====== 注册内置 API 提供商 ======

def _init_providers():
    """初始化内置 API 提供商（应用启动时调用）"""

    # ---- TMDB 电影 API（v3 使用 api_key 查询参数认证） ----
    register_provider(ApiProvider(
        name="tmdb",
        display_name="TMDB电影数据库",
        base_url="https://api.themoviedb.org/3",
        auth_type="api_key",
        api_key_config_path="tmdb",
        description="The Movie Database (TMDB) 电影数据 API，支持搜索影片和获取详情",
        endpoints={
            "search_movie": {
                "path": "/search/movie",
                "method": "GET",
                "description": "搜索电影",
                "params": {"language": "zh-CN", "page": "1"},
                "response_mapping": {
                    "_type": "list",
                    "_path": "results",
                    "_limit": 15,
                    "_items": {
                        "tmdb_id": "id",
                        "title": "title",
                        "original_title": "original_title",
                        "overview": "overview",
                        "release_date": "release_date",
                        "poster_path": "poster_path",
                        "vote_average": "vote_average",
                        "vote_count": "vote_count",
                        "popularity": "popularity",
                    }
                }
            },
            "movie_detail": {
                "path": "/movie/{movie_id}",
                "method": "GET",
                "description": "获取电影详情",
                "params": {"language": "zh-CN"},
                "response_mapping": {
                    "tmdb_id": "id",
                    "title": "title",
                    "original_title": "original_title",
                    "overview": "overview",
                    "release_date": "release_date",
                    "poster_path": "poster_path",
                    "backdrop_path": "backdrop_path",
                    "vote_average": "vote_average",
                    "vote_count": "vote_count",
                    "runtime": "runtime",
                    "genres": "genres",
                    "tagline": "tagline",
                    "homepage": "homepage",
                    "budget": "budget",
                    "revenue": "revenue",
                    "status": "status",
                }
            },
            "movie_credits": {
                "path": "/movie/{movie_id}/credits",
                "method": "GET",
                "description": "获取电影演职员",
                "params": {"language": "zh-CN"},
            }
        }
    ))

    # ---- 聚合数据新闻头条 API ----
    register_provider(ApiProvider(
        name="juhe_news",
        display_name="聚合数据新闻头条",
        base_url="https://v.juhe.cn",
        auth_type="api_key",
        api_key_config_path="juhe_news",
        description="聚合数据新闻头条 API，返回最新新闻列表",
        endpoints={
            "top_news": {
                "path": "/toutiao/index",
                "method": "GET",
                "description": "获取新闻头条列表",
                "params": {"type": "top"},
                "response_mapping": {
                    "_type": "list",
                    "_path": "result.data",
                    "_limit": 15,
                    "_items": {
                        "title": "title",
                        "source": "author_name",
                        "time": "date",
                        "link": "url",
                        "category": "category",
                        "thumbnail": "thumbnail_pic_s",
                    }
                }
            }
        }
    ))

    # ---- wttr.in 天气（免费无需密钥） ----
    register_provider(ApiProvider(
        name="wttr",
        display_name="wttr.in天气",
        base_url="https://wttr.in",
        auth_type="none",
        description="免费天气API，无需密钥",
        endpoints={
            "weather": {
                "path": "/{city}",
                "method": "GET",
                "description": "获取城市天气",
                "params": {"format": "j1", "lang": "zh"},
            }
        }
    ))


# 模块导入时自动初始化（仅注册提供商定义，不发起网络请求）
_init_providers()

# 全局单例
api_gateway = ApiGateway()
