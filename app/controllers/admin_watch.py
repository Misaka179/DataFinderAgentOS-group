import json
import re
import urllib.request
import urllib.parse
import ssl

import tornado.web

from app.controllers.base import BaseHandler
from app.models.watch_source import WatchSourceRepository
from app.models.watch_data import WatchDataRepository
from app.models.data_warehouse import DataWarehouseRepository


class WatchManagementHandler(BaseHandler):
    """瞭望管理页面"""
    @tornado.web.authenticated
    def get(self):
        self.render("admin/watch_management.html", title="瞭望采集", username=self.current_user)


class WatchCollectApiHandler(BaseHandler):
    """瞭望采集API - 根据选择的瞭源和关键词发起采集"""
    @tornado.web.authenticated
    def post(self):
        keyword = self.get_argument("keyword", "").strip()
        source_ids = self.get_argument("source_ids", "")  # 逗号分隔的ID列表
        page = int(self.get_argument("page", 1))  # 采集页码，默认第1页

        if not keyword:
            self.set_status(400)
            self.write(json.dumps({"success": False, "message": "请输入关键词"}))
            return

        if not source_ids:
            self.set_status(400)
            self.write(json.dumps({"success": False, "message": "请选择至少一个瞭源"}))
            return

        if page < 1:
            page = 1

        id_list = [int(x) for x in source_ids.split(",") if x.strip()]
        all_items = []

        for sid in id_list:
            source = WatchSourceRepository.get_by_id(sid)
            if not source or source.get("status") != 1:
                continue

            try:
                items = WatchCollectApiHandler._fetch_from_source(source, keyword, page)
                all_items.extend(items)
            except Exception as e:
                print(f"采集出错 [source={source.get('name')}]: {e}")

        # 批量入库
        if all_items:
            WatchDataRepository.batch_insert(all_items)

        self.write(json.dumps({
            "success": True,
            "message": f"采集完成，共获取 {len(all_items)} 条数据",
            "count": len(all_items)
        }))

    @staticmethod
    def _fetch_from_source(source, keyword, page=1):
        """根据瞭源规则发起HTTP请求并解析结果
        
        Args:
            source: 瞭源配置
            keyword: 搜索关键词
            page: 采集页码（从1开始），默认为1
        """
        url_template = source["url_template"]
        keyword_param = source.get("keyword_param", "word")
        page_param = source.get("page_param", "pn")
        page_step = source.get("page_step", 10)
        headers_raw = source.get("headers", "{}")

        # 计算分页偏移值: (page - 1) * page_step
        page_offset = (page - 1) * page_step
        params = {keyword_param: keyword, page_param: str(page_offset)}
        url = url_template + urllib.parse.urlencode(params)

        # 解析headers
        try:
            headers = json.loads(headers_raw) if isinstance(headers_raw, str) else headers_raw
        except (json.JSONDecodeError, TypeError):
            headers = {}

        # 发起请求
        req = urllib.request.Request(url, method="GET")
        for k, v in headers.items():
            if k.lower() not in ("host", "content-length", "content-type"):
                req.add_header(k, v)

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        try:
            with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
        except Exception as e:
            print(f"HTTP请求失败: {e}")
            return []

        # 解析百度新闻HTML
        return WatchCollectApiHandler._parse_baidu_news(html, source["id"], source["name"], keyword)

    @staticmethod
    def _parse_baidu_news(html, source_id, source_name, keyword):
        """解析百度新闻搜索结果HTML"""
        items = []

        # 百度新闻结果模式
        # 1. 匹配 <div class="result"> 或 <div class="result-op">...<h3>...<a>标题</a>
        # 2. 匹配 <h3 class="news-title">...<a>标题</a>
        # 3. 匹配摘要内容

        # 尝试多种解析模式

        # 模式1: 匹配 h3 内的链接 (百度新闻典型结构)
        title_links = re.findall(
            r'<h3[^>]*>.*?<a[^>]*href="(https?://[^"]+)"[^>]*>(.*?)</a>',
            html, re.DOTALL
        )

        # 模式2: 匹配 news-title_1 _2LjNc 等class
        if not title_links:
            title_links = re.findall(
                r'<a[^>]*href="(https?://[^"]+)"[^>]*>(.*?)</a>',
                html, re.DOTALL
            )

        # 提取摘要 (<span class="content-right_8Zs40"> 或 <div class="c-abstract">)
        summaries = re.findall(
            r'<span[^>]*class="[^"]*content-right[^"]*"[^>]*>(.*?)</span>',
            html, re.DOTALL
        )
        if not summaries:
            summaries = re.findall(
                r'<div[^>]*class="[^"]*c-abstract[^"]*"[^>]*>(.*?)</div>',
                html, re.DOTALL
            )
        if not summaries:
            summaries = re.findall(
                r'<span[^>]*class="[^"]*abstract[^"]*"[^>]*>(.*?)</span>',
                html, re.DOTALL
            )

        # 去重
        seen_titles = set()

        for i, (url, title) in enumerate(title_links):
            # 清理标题中的HTML标签
            title_clean = re.sub(r'<[^>]+>', '', title).strip()
            if not title_clean:
                continue

            # 跳过非新闻链接
            if title_clean in seen_titles:
                continue
            if len(title_clean) < 4:
                continue

            seen_titles.add(title_clean)

            # 规范化URL：处理协议相对路径(//...)和相对路径
            normalized_url = url.strip()
            if normalized_url.startswith("//"):
                normalized_url = "https:" + normalized_url
            elif normalized_url.startswith("/"):
                normalized_url = "https://www.baidu.com" + normalized_url
            elif not normalized_url.startswith("http://") and not normalized_url.startswith("https://"):
                normalized_url = "https://" + normalized_url

            # 获取对应的摘要
            summary = ""
            if i < len(summaries):
                summary = re.sub(r'<[^>]+>', '', summaries[i]).strip()
                summary = re.sub(r'\s+', ' ', summary)[:200]

            items.append({
                "source_id": source_id,
                "keyword": keyword,
                "title": title_clean,
                "url": normalized_url,
                "summary": summary,
                "source_name": source_name
            })

            if len(items) >= 50:  # 限制最多50条
                break

        return items


class WatchCollectedDataApiHandler(BaseHandler):
    """瞭望采集数据列表API（橱窗模式）"""
    @tornado.web.authenticated
    def get(self):
        page = int(self.get_argument("page", 1))
        page_size = int(self.get_argument("page_size", 12))
        keyword = self.get_argument("keyword", "")
        source_id = self.get_argument("source_id", "")

        if not keyword:
            keyword = None
        if not source_id:
            source_id = None
        else:
            source_id = int(source_id)

        result = WatchDataRepository.get_collected(keyword, source_id, page, page_size)
        self.write(json.dumps(result, ensure_ascii=False))


class WatchSaveToWarehouseApiHandler(BaseHandler):
    """将采集到的数据保存到数据仓库（支持选择/全选）"""
    @tornado.web.authenticated
    def post(self):
        try:
            body = self.request.body
            data = json.loads(body) if body else {}
        except Exception:
            data = {}

        # 支持两种方式：1.传入data_ids 2.直接传入items数组
        data_ids = data.get("data_ids", [])
        keyword = data.get("keyword", "")
        source_id = data.get("source_id", "")
        items = data.get("items", [])

        # 如果传入了data_ids，从watch_collected_data查询
        if data_ids and not items:
            from app.models.watch_data import WatchDataRepository
            for did in data_ids:
                item = WatchDataRepository.get_by_id(did)
                if item:
                    items.append(item)

        # 如果还是空的，从当前采集结果获取
        if not items and keyword:
            result = WatchDataRepository.get_collected(keyword if keyword else None,
                                                       int(source_id) if source_id else None,
                                                       1, 500)
            items = result.get("data", [])

        if not items:
            self.write(json.dumps({"success": False, "message": "没有数据可保存"}))
            return

        # 转换成数据仓库格式
        warehouse_items = []
        for item in items:
            warehouse_items.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "summary": item.get("summary", ""),
                "source_name": item.get("source_name", ""),
                "keyword": item.get("keyword", keyword),
                "source_id": item.get("source_id", source_id or 0)
            })

        ok = DataWarehouseRepository.batch_upsert(warehouse_items)
        if ok:
            self.write(json.dumps({
                "success": True,
                "message": f"已保存 {len(warehouse_items)} 条数据到数据仓库（重复数据已更新）",
                "count": len(warehouse_items)
            }))
        else:
            self.write(json.dumps({"success": False, "message": "保存失败"}))
