"""多模态API —— 生图/生视频"""
from __future__ import annotations

import json
import urllib.parse

import tornado.web
from app.controllers.base import BaseHandler
from app.models.ai_model import AiModelRepository


class ImageGenHandler(BaseHandler):
    """图片生成 —— 优先调用配置的API，失败则回退到 Pollinations.ai"""
    @tornado.web.authenticated
    async def post(self):
        prompt = self.get_body_argument("prompt", "").strip()
        size = self.get_body_argument("size", "1024x1024")

        if not prompt:
            self.write({"ok": False, "msg": "请输入图片描述"})
            return

        # 尝试使用配置的模型API
        model_id = self.get_body_argument("model_id", "")
        model = None
        if model_id:
            model = AiModelRepository.get_by_id(int(model_id))
        if not model or model.get("category") != "image":
            models = AiModelRepository.get_all_active()
            model = next((m for m in models if m.get("category") == "image"), None)

        if model:
            api_base = (model.get("api_base_url") or "").rstrip("/")
            api_key = model.get("api_key") or ""
            if api_base and api_key:
                url = f"{api_base}/images/generations"
                headers = {"Content-Type": "application/json"}
                if api_key:
                    headers["Authorization"] = f"Bearer {api_key}"

                body = json.dumps({
                    "model": model.get("model_name", "dall-e-3"),
                    "prompt": prompt,
                    "n": 1,
                    "size": size
                })

                from tornado.httpclient import AsyncHTTPClient, HTTPRequest
                try:
                    client = AsyncHTTPClient()
                    req = HTTPRequest(url=url, method="POST", headers=headers, body=body,
                                    request_timeout=120, connect_timeout=15)
                    resp = await client.fetch(req, raise_error=False)
                    if resp.code < 400:
                        data = json.loads(resp.body)
                        images = data.get("data", [])
                        if images:
                            image_url = images[0].get("url") or images[0].get("b64_json") or ""
                            if image_url:
                                self.write({"ok": True, "image_url": image_url, "prompt": prompt})
                                return
                except Exception:
                    pass  # 回退到免费API

        # 回退方案: Pollinations.ai（免费，无需API Key）
        encoded = urllib.parse.quote(prompt)
        image_url = f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=1024&nologo=true"
        self.write({"ok": True, "image_url": image_url, "prompt": prompt})


class VideoGenHandler(BaseHandler):
    """视频生成 —— 代理到配置的video类别模型API"""
    @tornado.web.authenticated
    async def post(self):
        prompt = self.get_body_argument("prompt", "").strip()
        model_id = self.get_body_argument("model_id", "")

        if not prompt:
            self.write({"ok": False, "msg": "请输入视频描述"})
            return

        model = None
        if model_id:
            model = AiModelRepository.get_by_id(int(model_id))
        if not model or model.get("category") != "video":
            models = AiModelRepository.get_all_active()
            model = next((m for m in models if m.get("category") == "video"), None)
        if not model:
            self.write({"ok": False, "msg": "没有可用的生视频模型"})
            return

        api_base = (model.get("api_base_url") or "").rstrip("/")
        api_key = model.get("api_key") or ""

        url = f"{api_base}/video/generations"
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        body = json.dumps({
            "model": model.get("model_name", "video-gen"),
            "prompt": prompt,
        })

        from tornado.httpclient import AsyncHTTPClient, HTTPRequest
        try:
            client = AsyncHTTPClient()
            req = HTTPRequest(url=url, method="POST", headers=headers, body=body,
                            request_timeout=180, connect_timeout=15)
            resp = await client.fetch(req, raise_error=False)
            if resp.code >= 400:
                err = resp.body.decode("utf-8", errors="replace")[:300]
                self.write({"ok": False, "msg": f"API错误({resp.code}): {err}"})
                return
            data = json.loads(resp.body)
            video_url = data.get("url") or data.get("video_url") or ""
            self.write({"ok": True, "video_url": video_url, "prompt": prompt})
        except Exception as e:
            self.write({"ok": False, "msg": f"生成失败: {str(e)[:200]}"})
