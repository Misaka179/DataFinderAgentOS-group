"""内置数字员工 API（新闻聚合数据 / 音乐 iTunes / 电影 TMDB）

返回带 self-describing 格式的统一 JSON 结构：
    {"success": true, "data": {"content": "...", "responseFormat": "...", "extraData": {...}}}

实现架构（利于后续「接口管理」模块）：
  - 外部 API 调用统一走 app/services/api_gateway.py（ApiGateway.call）
  - 本地兜底数据仅作为 API 不可用时的降级方案
  - 新增第三方 API 只需：① 在 api_gateway.py 注册 Provider ② 在此文件添加调用逻辑
"""

import json
import os
import random
import urllib.parse
import requests

from app.services.api_gateway import api_gateway

from .base import BaseHandler


# ==============================
#  新闻模块（聚合数据 API + 模拟兜底）
# ==============================

_NEWS_MOCK = [
    {
        "title": "国务院印发《数字中国建设整体布局规划》",
        "source": "新华社",
        "time": "2026-07-15 14:30",
        "summary": "《规划》明确，数字中国建设按照'2522'的整体框架进行布局，到2035年数字化发展水平进入世界前列。",
        "link": "https://www.xinhuanet.com/2026-07/15/c_112.html"
    },
    {
        "title": "2026世界人工智能大会在上海开幕",
        "source": "人民日报",
        "time": "2026-07-15 10:00",
        "summary": "本届大会以'智能无界·引领未来'为主题，汇聚全球顶尖AI科学家与企业家，展示AI最新技术与应用。",
        "link": "https://www.people.com.cn/2026-07/15/ai.html"
    },
    {
        "title": "我国成功发射新一代气象卫星",
        "source": "央视新闻",
        "time": "2026-07-14 22:15",
        "summary": "该卫星将大幅提升我国天气预报和气候变化监测能力，服务'一带一路'沿线国家。",
        "link": "https://news.cctv.com/2026/07/14/satellite.html"
    },
    {
        "title": "新能源汽车产销同比增长48%",
        "source": "经济日报",
        "time": "2026-07-14 16:45",
        "summary": "上半年我国新能源汽车产销分别完成378.8万辆和374.7万辆，市场占有率达35.2%。",
        "link": "https://www.ce.cn/2026-07/14/ev.html"
    },
    {
        "title": "教育部：2026年新增人工智能专业点200个",
        "source": "中国教育报",
        "time": "2026-07-14 09:30",
        "summary": "教育部表示将进一步扩大AI相关专业人才培养规模，推动产教深度融合。",
        "link": "https://www.jyb.cn/2026-07/14/ai-edu.html"
    },
    {
        "title": "国产大模型通过国家备案，向全社会开放",
        "source": "科技日报",
        "time": "2026-07-13 18:20",
        "summary": "多个国产大模型通过《生成式人工智能服务管理暂行办法》备案，正式向公众开放服务。",
        "link": "https://www.stdaily.com/2026-07/13/llm.html"
    },
    {
        "title": "医保谈判结果公布：67种药品平均降价61.7%",
        "source": "健康报",
        "time": "2026-07-13 11:00",
        "summary": "本次谈判涉及肿瘤、慢性病、罕见病等多个治疗领域，预计为患者减负超300亿元。",
        "link": "https://www.jkb.com.cn/2026-07/13/medical.html"
    },
    {
        "title": "杭州亚运会场馆全面向市民开放",
        "source": "浙江日报",
        "time": "2026-07-12 15:30",
        "summary": "亚运会场馆赛后利用方案公布，所有场馆已实现'还馆于民'，市民可预约使用。",
        "link": "https://zjnews.zjol.com.cn/2026-07/12/asiangames.html"
    },
    {
        "title": "全球首个商用核聚变项目启动建设",
        "source": "环球时报",
        "time": "2026-07-12 08:00",
        "summary": "该项目位于法国，计划2030年投入运行，标志着清洁能源领域里程碑式突破。",
        "link": "https://www.huanqiu.com/2026-07/12/fusion.html"
    },
    {
        "title": "暑期档票房突破200亿元，创历史新高",
        "source": "中国电影报",
        "time": "2026-07-11 20:45",
        "summary": "国产影片《流浪地球3》以45亿票房领跑，多部国产动画电影表现亮眼。",
        "link": "https://www.chinafilm.com/2026-07/11/boxoffice.html"
    },
    {
        "title": "全国首个5G-A商用网络在深圳开通",
        "source": "深圳特区报",
        "time": "2026-07-11 14:20",
        "summary": "5G-A（5.5G）网络在深圳实现全域覆盖，峰值速率可达10Gbps，支撑自动驾驶等应用。",
        "link": "https://www.sznews.com/2026-07/11/5ga.html"
    },
    {
        "title": "央行发布数字人民币最新进展",
        "source": "金融时报",
        "time": "2026-07-10 17:30",
        "summary": "数字人民币试点已覆盖26个省市，交易额突破万亿元，跨境支付场景持续拓展。",
        "link": "https://www.financialnews.com.cn/2026-07/10/dcep.html"
    }
]


def _fetch_juhe_news():
    """通过聚合数据新闻头条 API 获取实时新闻

    返回: list[dict] 或 None（失败时返回 None）
    """
    result = api_gateway.call("juhe_news", "top_news")
    if result.get("success") and result.get("data"):
        items = result["data"]
        if len(items) >= 3:
            return items
    return None


def _get_live_news():
    """实时新闻获取（聚合数据 API → 模拟数据兜底）

    返回: (list[dict], fetch_time_str)
    """
    from datetime import datetime
    now = datetime.now().strftime("%Y年%m月%d日 %H:%M")

    # 聚合数据新闻头条 API
    items = _fetch_juhe_news()
    if items:
        print(f"[新闻] 聚合数据API获取成功 ({len(items)}条)")
        return items, now

    # 兜底：模拟数据
    fallback = random.sample(_NEWS_MOCK, min(len(_NEWS_MOCK), random.randint(10, 12)))
    fallback.sort(key=lambda x: x["time"], reverse=True)
    print(f"[新闻] 使用模拟数据兜底 ({len(fallback)}条)")
    return fallback, now


class MockNewsHandler(BaseHandler):
    """返回热门新闻（聚合数据 API 优先，模拟数据兜底）"""
    def get(self):
        items, fetch_time = _get_live_news()

        text_lines = [f"📰 **热门新闻速递**（{fetch_time}）\n"]
        for i, item in enumerate(items, 1):
            text_lines.append(
                f"{i}. **[{item['title']}]({item.get('link', '')})**\n"
                f"   📍 {item.get('source', '')}{'  🕐 ' + item.get('time', '') if item.get('time') else ''}\n"
                f"   {item.get('summary', '')}"
            )

        self.set_header("Content-Type", "application/json")
        self.write(json.dumps({
            "success": True,
            "data": {
                "content": "\n\n".join(text_lines),
                "responseFormat": "news_list",
                "extraData": {"list": items}
            }
        }, ensure_ascii=False))
        self.finish()


# ====== 随机音乐（iTunes API + 本地精选兜底） ======

# 本地精选曲库（iTunes API 不可用时的兜底数据）
_MUSIC_FALLBACK = [
    {"song": "七里香", "artist": "周杰伦",
     "cover": "https://picsum.photos/seed/qilixiang/300/300",
     "url": ""},
    {"song": "起风了", "artist": "买辣椒也用券",
     "cover": "https://picsum.photos/seed/qifengle/300/300",
     "url": ""},
    {"song": "平凡之路", "artist": "朴树",
     "cover": "https://picsum.photos/seed/pfzl/300/300",
     "url": ""},
    {"song": "光年之外", "artist": "G.E.M. 邓紫棋",
     "cover": "https://picsum.photos/seed/gnzw/300/300",
     "url": ""},
    {"song": "演员", "artist": "薛之谦",
     "cover": "https://picsum.photos/seed/yanyuan/300/300",
     "url": ""},
    {"song": "稻香", "artist": "周杰伦",
     "cover": "https://picsum.photos/seed/daoxiang/300/300",
     "url": ""},
    {"song": "成都", "artist": "赵雷",
     "cover": "https://picsum.photos/seed/chengdu/300/300",
     "url": ""},
    {"song": "大鱼", "artist": "周深",
     "cover": "https://picsum.photos/seed/dayu/300/300",
     "url": ""},
    {"song": "消愁", "artist": "毛不易",
     "cover": "https://picsum.photos/seed/xiaochou/300/300",
     "url": ""},
    {"song": "孤勇者", "artist": "陈奕迅",
     "cover": "https://picsum.photos/seed/guyongzhe/300/300",
     "url": ""},
]

_ITUNES_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

_RANDOM_SEARCH_TERMS = [
    "周杰伦", "陈奕迅", "邓紫棋", "薛之谦", "林俊杰",
    "赵雷", "李荣浩", "毛不易", "周深", "张杰",
    "华语流行", "华语热歌", "抖音热歌", "治愈系", "民谣"
]


def _fetch_itunes_music(search_term=None):
    """从 iTunes API 获取真实歌曲信息"""
    try:
        if search_term is None:
            search_term = random.choice(_RANDOM_SEARCH_TERMS)
        term = urllib.parse.quote(search_term)
        url = (f"https://itunes.apple.com/search?term={term}"
               f"&country=CN&media=music&lang=zh_cn&limit=20")
        resp = requests.get(url, headers=_ITUNES_HEADERS, timeout=8)
        if resp.status_code != 200:
            return None

        data = resp.json()
        results = data.get("results", [])
        if not results:
            return None

        has_preview = [r for r in results if r.get("previewUrl")]
        if not has_preview:
            has_preview = results
        item = random.choice(has_preview)
        cover = item.get("artworkUrl100", "").replace("100x100", "300x300")

        return {
            "song": item.get("trackName", "未知歌曲"),
            "artist": item.get("artistName", "未知歌手"),
            "cover": cover,
            "url": item.get("previewUrl", ""),
        }
    except Exception:
        return None


def _get_random_music():
    """随机音乐：iTunes API 优先，本地精选兜底"""
    result = _fetch_itunes_music()
    if result and result.get("url"):
        print(f"[音乐] iTunes API 获取成功: {result['song']} - {result['artist']}")
        return result

    item = random.choice(_MUSIC_FALLBACK)
    print(f"[音乐] 使用本地精选: {item['song']} - {item['artist']}")
    return item


def _get_random_music_song():
    """兼容旧函数名"""
    return _get_random_music()


class MockMusicHandler(BaseHandler):
    """随机推荐一首音乐（iTunes API + 本地精选）"""
    def get(self):
        item = _get_random_music()
        text = f"🎵 **随机音乐推荐**\n\n**{item['song']}** - {item['artist']}"

        self.set_header("Content-Type", "application/json")
        self.write(json.dumps({
            "success": True,
            "data": {
                "content": text,
                "responseFormat": "music_player",
                "extraData": {
                    "song": item["song"],
                    "artist": item["artist"],
                    "cover": item["cover"],
                    "url": item["url"]
                }
            }
        }, ensure_ascii=False))
        self.finish()


# ====== 天气（本地 Mock，避免 wttr.in 国内不通） ======

MOCK_WEATHER_DATA = {
    "成都": {"desc": "多云转晴", "temp": 32, "humidity": 55, "wind": "东北风 3级", "aqi": 72},
    "北京": {"desc": "晴", "temp": 28, "humidity": 35, "wind": "北风 4级", "aqi": 45},
    "上海": {"desc": "小雨", "temp": 26, "humidity": 78, "wind": "东南风 2级", "aqi": 58},
    "广州": {"desc": "雷阵雨", "temp": 33, "humidity": 82, "wind": "南风 3级", "aqi": 40},
    "深圳": {"desc": "多云", "temp": 31, "humidity": 68, "wind": "西南风 2级", "aqi": 35},
    "杭州": {"desc": "阴转多云", "temp": 29, "humidity": 62, "wind": "东风 2级", "aqi": 55},
    "武汉": {"desc": "晴", "temp": 34, "humidity": 45, "wind": "南风 3级", "aqi": 60},
    "西安": {"desc": "多云", "temp": 30, "humidity": 40, "wind": "东北风 2级", "aqi": 68},
    "重庆": {"desc": "阴", "temp": 35, "humidity": 70, "wind": "北风 1级", "aqi": 80},
}

class MockWeatherHandler(BaseHandler):
    """本地天气 Mock API"""
    def get(self):
        city = self.get_argument("city", "成都")
        data = MOCK_WEATHER_DATA.get(city, MOCK_WEATHER_DATA.get("成都", {}))
        text = (
            f"【{city}天气】\n"
            f"天气：{data['desc']}\n"
            f"温度：{data['temp']}°C\n"
            f"湿度：{data['humidity']}%\n"
            f"风力：{data['wind']}\n"
            f"空气质量指数(AQI)：{data['aqi']}"
        )
        self.set_header("Content-Type", "application/json")
        self.write(json.dumps({
            "success": True,
            "data": {
                "content": text,
                "responseFormat": "weather_card",
                "extraData": {
                    "city": city, "weather": data["desc"],
                    "temperature": data["temp"], "humidity": data["humidity"],
                    "wind": data["wind"], "aqi": data["aqi"]
                }
            }
        }, ensure_ascii=False))
        self.finish()


# ====== 电影（TMDB API + 本地详情库兜底） ======

# TMDB 图片基础 URL
_TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"

# 本地电影详情库（TMDB 返回数据不足时的补充）
_MOVIE_LOCAL_DB = {
    "哪吒": {
        "title": "哪吒之魔童降世",
        "director": "饺子",
        "actors": ["吕艳婷", "囧森瑟夫", "瀚墨", "陈浩", "绿绮"],
        "summary": "天地灵气孕育出一颗混元珠，元始天尊将混元珠提炼成灵珠和魔丸。太乙真人受命将灵珠托生于陈塘关李靖家，却因申公豹的调包，灵珠和魔丸被掉包。本应是灵珠转世的哪吒成了魔丸转世。三年后，哪吒将面临天劫…",
        "rating": "8.4",
        "year": "2019",
    },
    "流浪地球": {
        "title": "流浪地球3",
        "director": "郭帆",
        "actors": ["吴京", "刘德华", "李雪健", "王智"],
        "summary": "太阳即将毁灭，人类在地球表面建造了巨大的推进器，开启'流浪地球'计划。",
        "rating": "9.2",
        "year": "2026",
    },
    "封神": {
        "title": "封神第一部",
        "director": "乌尔善",
        "actors": ["黄渤", "费翔", "李雪健", "娜然"],
        "summary": "商王殷寿残暴无道，姬发觉醒昆仑之力，集结各路英雄对抗暴政。",
        "rating": "7.8",
        "year": "2023",
    },
}


def _search_tmdb_movie(keyword):
    """通过 TMDB API 搜索电影

    Returns: (tmdb_results: list[dict], douban_urls: dict)
        tmdb_results 含 tmdb_id, title, poster_url, overview, year, rating 等
    """
    result = api_gateway.call("tmdb", "search_movie", {"query": keyword})
    if not result.get("success") or not result.get("data"):
        return [], {}

    raw = result.get("raw", {})
    tmdb_results = []
    for item in result["data"]:
        poster_path = item.get("poster_path", "")
        tmdb_results.append({
            "tmdb_id": item.get("tmdb_id"),
            "title": item.get("title", ""),
            "original_title": item.get("original_title", ""),
            "overview": item.get("overview", ""),
            "year": (item.get("release_date", "") or "")[:4],
            "poster": f"{_TMDB_IMAGE_BASE}{poster_path}" if poster_path else "",
            "rating": round(item.get("vote_average", 0), 1),
            "vote_count": item.get("vote_count", 0),
        })

    return tmdb_results, {}


def _get_movie_detail(tmdb_id):
    """通过 TMDB 获取电影详情

    Returns: dict 或 None
    """
    result = api_gateway.call("tmdb", "movie_detail", {"movie_id": str(tmdb_id)})
    if result.get("success") and result.get("data"):
        detail = result["data"]
        poster_path = detail.get("poster_path", "")
        return {
            "tmdb_id": detail.get("tmdb_id"),
            "title": detail.get("title", ""),
            "overview": detail.get("overview", ""),
            "year": (detail.get("release_date", "") or "")[:4],
            "poster": f"{_TMDB_IMAGE_BASE}{poster_path}" if poster_path else "",
            "rating": round(detail.get("vote_average", 0), 1),
            "runtime": detail.get("runtime", ""),
            "genres": [g.get("name", "") for g in detail.get("genres", [])],
            "tagline": detail.get("tagline", ""),
            "homepage": detail.get("homepage", ""),
        }
    return None


def _enrich_with_local_db(movie, keyword_lower):
    """用本地详情库补充 TMDB 结果（导演、演员、中文剧情等）"""
    for local_key, local_info in _MOVIE_LOCAL_DB.items():
        title = movie.get("title", "")
        if local_key.lower() in title.lower() or title.lower() in local_key.lower():
            movie["director"] = local_info.get("director", "")
            movie["actors"] = local_info.get("actors", [])
            if not movie.get("overview"):
                movie["overview"] = local_info.get("summary", "")
            if not movie.get("year"):
                movie["year"] = local_info.get("year", "")
            rating_val = movie.get("rating", 0)
            if isinstance(rating_val, (int, float)) and rating_val <= 0:
                movie["rating"] = local_info.get("rating", "?")
            return
    # 本地库未匹配，使用默认值
    if not movie.get("director"):
        movie["director"] = "请前往TMDB页面查看"
    if not movie.get("actors"):
        movie["actors"] = []


def _search_movie(keyword):
    """按关键词搜索电影（TMDB API + 本地库丰富）

    Returns: list[dict]
    """
    keyword_lower = keyword.lower().strip()
    tmdb_results, _ = _search_tmdb_movie(keyword)

    if not tmdb_results:
        # TMDB 无结果，尝试本地库兜底
        matched = []
        for local_key, local_info in _MOVIE_LOCAL_DB.items():
            if keyword_lower in local_key.lower() or local_key.lower() in keyword_lower:
                matched.append({
                    "title": local_info["title"],
                    "director": local_info["director"],
                    "actors": local_info["actors"],
                    "summary": local_info["summary"],
                    "rating": local_info["rating"],
                    "year": local_info["year"],
                    "poster": "",
                    "url": f"https://www.themoviedb.org/search?query={urllib.parse.quote(keyword)}",
                })
        return matched

    # 丰富 TMDB 结果
    matched = []
    for movie in tmdb_results[:8]:
        _enrich_with_local_db(movie, keyword_lower)
        movie["url"] = f"https://www.themoviedb.org/movie/{movie.get('tmdb_id', '')}"
        movie["summary"] = movie.get("overview", "")
        matched.append(movie)
    return matched


def _get_random_movie():
    """随机返回本地库中的一部电影"""
    movie = random.choice(list(_MOVIE_LOCAL_DB.values()))
    return {
        "title": movie["title"],
        "director": movie["director"],
        "actors": movie["actors"],
        "summary": movie["summary"],
        "rating": movie["rating"],
        "year": movie["year"],
        "poster": "",
        "url": f"https://www.themoviedb.org/search?query={urllib.parse.quote(movie['title'])}",
    }


class MockMovieHandler(BaseHandler):
    """支持按片名搜索（TMDB API）和随机推荐（本地库）"""
    def get(self):
        keyword = self.get_argument("keyword", "").strip()

        if keyword:
            matched = _search_movie(keyword)
            if not matched:
                self.set_header("Content-Type", "application/json")
                self.write(json.dumps({
                    "success": True,
                    "data": {
                        "content": f"😅 未找到与「{keyword}」相关的电影信息，换个关键词试试吧！",
                        "responseFormat": "text",
                        "extraData": {}
                    }
                }, ensure_ascii=False))
                self.finish()
                return
            selected = random.choice(matched)
        else:
            selected = _get_random_movie()

        actors_text = " / ".join(selected.get("actors", [])[:5])
        text = (
            f"🎬 **{selected['title']}** ({selected.get('year', '')})\n\n"
            f"⭐ 评分：**{selected.get('rating', '?')}**\n"
            f"🎥 导演：{selected.get('director', '')}\n"
        )
        if actors_text:
            text += f"👥 演员：{actors_text}\n"
        text += f"\n📖 **剧情简介**\n{selected.get('summary', '')}\n\n"
        text += f"🔗 [查看详情]({selected.get('url', '')})"

        self.set_header("Content-Type", "application/json")
        self.write(json.dumps({
            "success": True,
            "data": {
                "content": text,
                "responseFormat": "movie_detail",
                "extraData": {
                    "title": selected["title"],
                    "director": selected.get("director", ""),
                    "actors": selected.get("actors", []),
                    "summary": selected.get("summary", ""),
                    "rating": str(selected.get("rating", "?")),
                    "year": selected.get("year", ""),
                    "poster": selected.get("poster", ""),
                    "url": selected.get("url", "")
                }
            }
        }, ensure_ascii=False))
        self.finish()
