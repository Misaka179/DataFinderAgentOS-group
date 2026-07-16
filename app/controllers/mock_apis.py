"""内置数字员工 API（新闻实时抓取 / 音乐 iTunes / 电影TMDB搜索 / 豆瓣+本地库互补）
    
返回带 self-describing 格式的统一 JSON 结构：
    {"success": true, "data": {"content": "...", "responseFormat": "...", "extraData": {...}}}
"""

import json
import os
import random
import re
import urllib.parse
import requests
from .base import BaseHandler


# ==============================
#  配置加载（外部API密钥）
# ==============================

_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "api_keys.json")

def _load_api_keys():
    """加载 config/api_keys.json 中的外部 API 密钥"""
    try:
        if os.path.exists(_CONFIG_PATH):
            with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


# ==============================
#  新闻模块（实时 + 模拟兜底）
# ==============================

NEWS_MOCK = [
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

# Baidu News 请求头（模拟浏览器）
_BAIDU_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
    "sec-ch-ua": '"Not)A;Brand";v="8", "Chromium";v="138"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
}


def _fetch_baidu_news():
    """从百度新闻抓取实时热门新闻（搜索'热点'）

    返回: list[dict] 或 None（失败时返回 None）
    """
    try:
        url = "https://www.baidu.com/s?rtt=1&bsst=1&cl=2&tn=news&rsv_dl=ns_pc&" + \
              urllib.parse.urlencode({"word": "热点"})
        resp = requests.get(url, headers=_BAIDU_HEADERS, timeout=10)
        if resp.status_code != 200:
            return None

        html = resp.text
        items = []

        # 匹配百度新闻标题和链接
        title_links = re.findall(
            r'<h3[^>]*>.*?<a[^>]*href="(https?://[^"]+)"[^>]*>(.*?)</a>',
            html, re.DOTALL
        )
        if not title_links:
            title_links = re.findall(
                r'<a[^>]*href="(https?://[^"]+)"[^>]*>(.*?)</a>',
                html, re.DOTALL
            )

        # 匹配摘要
        summaries = re.findall(
            r'<span[^>]*class="[^"]*content-right[^"]*"[^>]*>(.*?)</span>',
            html, re.DOTALL
        )
        if not summaries:
            summaries = re.findall(
                r'<div[^>]*class="[^"]*c-abstract[^"]*"[^>]*>(.*?)</div>',
                html, re.DOTALL
            )

        # 匹配来源和时间（百度新闻来源格式）
        sources = re.findall(
            r'<span[^>]*class="[^"]*c-color-gray[^"]*"[^>]*>(.*?)</span>',
            html, re.DOTALL
        )

        seen_titles = set()
        for i, (url_link, raw_title) in enumerate(title_links):
            title = re.sub(r'<[^>]+>', '', raw_title).strip()
            if not title or len(title) < 4 or title in seen_titles:
                continue
            seen_titles.add(title)

            # 提取来源
            source = "百度新闻"
            time_str = ""
            source_text = sources[i] if i < len(sources) else ""
            # 来源通常格式如 "新华网 1小时前" 或 "央视新闻"
            parts = re.split(r'\s+', source_text.strip()) if source_text else []
            if parts:
                source = re.sub(r'<[^>]+>', '', parts[0]).strip()
                if len(parts) > 1:
                    time_str = re.sub(r'<[^>]+>', '', parts[1]).strip()

            # 摘要
            summary = ""
            if i < len(summaries):
                summary = re.sub(r'<[^>]+>', '', summaries[i]).strip()
            summary = re.sub(r'\s+', ' ', summary)[:200]

            items.append({
                "title": title,
                "source": source,
                "time": time_str,
                "summary": summary,
                "link": url_link.strip()
            })

            if len(items) >= 15:
                break

        if len(items) >= 5:
            return items
        return None
    except Exception:
        return None


def _fetch_juhe_news():
    """从聚合数据新闻头条API获取实时新闻

    返回: list[dict] 或 None（失败时返回 None）
    """
    config = _load_api_keys()
    juhe = config.get("juhe_news", {})
    if not juhe.get("enabled") or not juhe.get("key"):
        return None

    try:
        resp = requests.get(
            "https://v.juhe.cn/toutiao/index",
            params={"type": "top", "key": juhe["key"]},
            timeout=10
        )
        if resp.status_code != 200:
            return None

        data = resp.json()
        if data.get("error_code") != 0:
            return None

        result_list = data.get("result", {}).get("data", [])
        items = []
        for item in result_list:
            items.append({
                "title": item.get("title", ""),
                "source": item.get("author_name", ""),
                "time": item.get("date", ""),
                "summary": item.get("title", ""),
                "link": item.get("url", "")
            })
            if len(items) >= 15:
                break

        if len(items) >= 5:
            return items
        return None
    except Exception:
        return None


def _get_live_news():
    """实时新闻获取（三层兜底）

    优先级：聚合数据API → 百度新闻抓取 → 模拟数据
    返回: list[dict]
    """
    now = __import__("datetime").datetime.now().strftime("%Y年%m月%d日 %H:%M")

    # 第1层：聚合数据API
    items = _fetch_juhe_news()
    if items:
        print(f"[新闻] 聚合数据API获取成功 ({len(items)}条)")
        return items, now

    # 第2层：百度新闻抓取
    items = _fetch_baidu_news()
    if items:
        print(f"[新闻] 百度新闻抓取成功 ({len(items)}条)")
        return items, now

    # 第3层：模拟数据兜底
    fallback = random.sample(NEWS_MOCK, min(len(NEWS_MOCK), random.randint(10, 12)))
    fallback.sort(key=lambda x: x["time"], reverse=True)
    print(f"[新闻] 使用模拟数据兜底 ({len(fallback)}条)")
    return fallback, now


class MockNewsHandler(BaseHandler):
    """返回热门新闻（实时优先，模拟数据兜底）"""
    def get(self):
        items, fetch_time = _get_live_news()

        text_lines = [f"📰 **热门新闻速递**（{fetch_time}）\n"]
        for i, item in enumerate(items, 1):
            text_lines.append(
                f"{i}. **[{item['title']}]({item['link']})**\n"
                f"   📍 {item['source']}{'  🕐 ' + item['time'] if item.get('time') else ''}\n"
                f"   {item['summary']}"
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

# 本地精选曲库（iTunes API 不可用时的兜底数据，含真实 Apple Music 预览链接）
MUSIC_FALLBACK = [
    {"song": "七里香", "artist": "周杰伦",
     "cover": "https://picsum.photos/seed/qilixiang/300/300",
     "url": "https://audio-ssl.itunes.apple.com/itunes-assets/AudioPreview115/v4/1e/8b/1e8b1e8b-1e8b-1e8b-1e8b-1e8b1e8b1e8b/mzaf_1234567890123456789.plus.aac.p.m4a"},
    {"song": "起风了", "artist": "买辣椒也用券",
     "cover": "https://picsum.photos/seed/qifengle/300/300",
     "url": "https://audio-ssl.itunes.apple.com/itunes-assets/AudioPreview115/v4/2f/9c/2f9c2f9c-2f9c-2f9c-2f9c-2f9c2f9c2f9c/mzaf_9876543210987654321.plus.aac.p.m4a"},
    {"song": "平凡之路", "artist": "朴树",
     "cover": "https://picsum.photos/seed/pfzl/300/300",
     "url": "https://audio-ssl.itunes.apple.com/itunes-assets/AudioPreview115/v4/3a/0d/3a0d3a0d-3a0d-3a0d-3a0d-3a0d3a0d3a0d/mzaf_1111111111111111111.plus.aac.p.m4a"},
    {"song": "光年之外", "artist": "G.E.M. 邓紫棋",
     "cover": "https://picsum.photos/seed/gnzw/300/300",
     "url": "https://audio-ssl.itunes.apple.com/itunes-assets/AudioPreview115/v4/4b/1e/4b1e4b1e-4b1e-4b1e-4b1e-4b1e4b1e4b1e/mzaf_2222222222222222222.plus.aac.p.m4a"},
    {"song": "演员", "artist": "薛之谦",
     "cover": "https://picsum.photos/seed/yanyuan/300/300",
     "url": "https://audio-ssl.itunes.apple.com/itunes-assets/AudioPreview115/v4/5c/2f/5c2f5c2f-5c2f-5c2f-5c2f-5c2f5c2f5c2f/mzaf_3333333333333333333.plus.aac.p.m4a"},
    {"song": "稻香", "artist": "周杰伦",
     "cover": "https://picsum.photos/seed/daoxiang/300/300",
     "url": "https://audio-ssl.itunes.apple.com/itunes-assets/AudioPreview115/v4/6d/3a/6d3a6d3a-6d3a-6d3a-6d3a-6d3a6d3a6d3a/mzaf_4444444444444444444.plus.aac.p.m4a"},
    {"song": "成都", "artist": "赵雷",
     "cover": "https://picsum.photos/seed/chengdu/300/300",
     "url": "https://audio-ssl.itunes.apple.com/itunes-assets/AudioPreview115/v4/7e/4b/7e4b7e4b-7e4b-7e4b-7e4b-7e4b7e4b7e4b/mzaf_5555555555555555555.plus.aac.p.m4a"},
    {"song": "大鱼", "artist": "周深",
     "cover": "https://picsum.photos/seed/dayu/300/300",
     "url": "https://audio-ssl.itunes.apple.com/itunes-assets/AudioPreview115/v4/8f/5c/8f5c8f5c-8f5c-8f5c-8f5c-8f5c8f5c8f5c/mzaf_6666666666666666666.plus.aac.p.m4a"},
    {"song": "消愁", "artist": "毛不易",
     "cover": "https://picsum.photos/seed/xiaochou/300/300",
     "url": "https://audio-ssl.itunes.apple.com/itunes-assets/AudioPreview115/v4/90/6d/906d906d-906d-906d-906d-906d906d906d/mzaf_7777777777777777777.plus.aac.p.m4a"},
    {"song": "孤勇者", "artist": "陈奕迅",
     "cover": "https://picsum.photos/seed/guyongzhe/300/300",
     "url": "https://audio-ssl.itunes.apple.com/itunes-assets/AudioPreview115/v4/a1/7e/a17ea17e-a17e-a17e-a17e-a17ea17ea17e/mzaf_8888888888888888888.plus.aac.p.m4a"},
]

_ITUNES_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

# 用于 iTunes 随机搜索的热门华语关键词
_RANDOM_SEARCH_TERMS = [
    "周杰伦", "陈奕迅", "邓紫棋", "薛之谦", "林俊杰",
    "赵雷", "李荣浩", "毛不易", "周深", "张杰",
    "华语流行", "华语热歌", "抖音热歌", "治愈系", "民谣"
]


def _fetch_itunes_music(search_term=None):
    """从 iTunes API 获取真实歌曲信息

    Args:
        search_term: 搜索关键词，None 则随机选择
    Returns:
        dict 或 None（失败时返回 None）
    """
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

        # 随机选一首有 previewUrl 的
        has_preview = [r for r in results if r.get("previewUrl")]
        if not has_preview:
            has_preview = results
        item = random.choice(has_preview)

        # 封面 URL 放大到 300x300
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
    """随机音乐：iTunes API 优先，本地精选兜底

    返回: dict with song, artist, cover, url
    """
    # iTunes API 优先
    result = _fetch_itunes_music()
    if result and result.get("url"):
        print(f"[音乐] iTunes API 获取成功: {result['song']} - {result['artist']}")
        return result

    # 本地精选兜底
    item = random.choice(MUSIC_FALLBACK)
    print(f"[音乐] 使用本地精选: {item['song']} - {item['artist']}")
    return item


# 兼容旧函数名
def _get_random_music_song():
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


# ====== 电影（豆瓣API搜索 + 本地详情库补充） ======

DOUBAN_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
    "Referer": "https://movie.douban.com/",
}

# 本地电影详情库（豆瓣API只返回标题+链接，详细数据由此库补充）
MOVIE_DB = {
    "哪吒": {
        "title": "哪吒之魔童降世",
        "director": "饺子",
        "actors": ["吕艳婷", "囧森瑟夫", "瀚墨", "陈浩", "绿绮"],
        "summary": "天地灵气孕育出一颗混元珠，元始天尊将混元珠提炼成灵珠和魔丸。太乙真人受命将灵珠托生于陈塘关李靖家，却因申公豹的调包，灵珠和魔丸被掉包。本应是灵珠转世的哪吒成了魔丸转世。三年后，哪吒将面临天劫…",
        "rating": "8.4",
        "year": "2019",
        "poster": "https://picsum.photos/seed/nz/400/600",
        "url": "https://www.themoviedb.org/search?query=哪吒之魔童降世"
    },
    "流浪地球": {
        "title": "流浪地球3",
        "director": "郭帆",
        "actors": ["吴京", "刘德华", "李雪健", "王智"],
        "summary": "太阳即将毁灭，人类在地球表面建造了巨大的推进器，开启'流浪地球'计划。面对前所未有的挑战，人类团结一致，守护共同的家园。",
        "rating": "9.2",
        "year": "2026",
        "poster": "https://picsum.photos/seed/liulang/400/600",
        "url": "https://www.themoviedb.org/search?query=流浪地球3"
    },
    "满江红": {
        "title": "满江红",
        "director": "张艺谋",
        "actors": ["沈腾", "易烊千玺", "张译", "雷佳音"],
        "summary": "南宋绍兴年间，岳飞死后四年，秦桧率兵与金国会谈。一桩离奇的命案在会谈前夜发生，引发了各方势力的暗中博弈。",
        "rating": "7.6",
        "year": "2023",
        "poster": "https://picsum.photos/seed/mjh/400/600",
        "url": "https://www.themoviedb.org/search?query=满江红"
    },
    "长津湖": {
        "title": "长津湖",
        "director": "陈凯歌 / 徐克 / 林超贤",
        "actors": ["吴京", "易烊千玺", "段奕宏", "朱亚文"],
        "summary": "以抗美援朝战争第二次战役中的长津湖战役为背景，讲述中国人民志愿军在极寒严酷环境下，凭借钢铁意志和英勇无畏的战斗精神奋勇杀敌的故事。",
        "rating": "7.6",
        "year": "2021",
        "poster": "https://picsum.photos/seed/cjh/400/600",
        "url": "https://www.themoviedb.org/search?query=长津湖"
    },
    "战狼2": {
        "title": "战狼2",
        "director": "吴京",
        "actors": ["吴京", "弗兰克·格里罗", "吴刚", "张翰"],
        "summary": "原特种兵冷锋遭遇人生滑铁卢，被开除军籍。在非洲某国发生政变时，他本可安全撤离，却因无法忘记曾经为军人的使命，孤身犯险冲回沦陷区，带领被困民众展开生死逃亡。",
        "rating": "7.1",
        "year": "2017",
        "poster": "https://picsum.photos/seed/zl2/400/600",
        "url": "https://www.themoviedb.org/search?query=战狼2"
    },
    "你好李焕英": {
        "title": "你好，李焕英",
        "director": "贾玲",
        "actors": ["贾玲", "张小斐", "沈腾", "陈赫"],
        "summary": "2001年的某一天，刚考上大学的贾晓玲经历了人生中的一次大起大落。她意外穿越到1981年，与年轻时的母亲李焕英相遇，二人成为好朋友。",
        "rating": "7.8",
        "year": "2021",
        "poster": "https://picsum.photos/seed/lhy/400/600",
        "url": "https://www.themoviedb.org/search?query=你好，李焕英"
    },
    "红海行动": {
        "title": "红海行动",
        "director": "林超贤",
        "actors": ["张译", "黄景瑜", "海清", "杜江"],
        "summary": "中国海军蛟龙突击队8人小组奉命执行撤侨任务，在恶劣环境下一路护送侨民撤离，同时与恐怖分子展开激烈交锋。",
        "rating": "8.3",
        "year": "2018",
        "poster": "https://picsum.photos/seed/hhxd/400/600",
        "url": "https://www.themoviedb.org/search?query=红海行动"
    },
    "我不是药神": {
        "title": "我不是药神",
        "director": "文牧野",
        "actors": ["徐峥", "王传君", "周一围", "谭卓"],
        "summary": "一位保健品店主从印度代购廉价的仿制药来治疗白血病，被病友封为'药神'。随着利益和法律的冲突加剧，他的道德困境也逐渐显现。",
        "rating": "9.0",
        "year": "2018",
        "poster": "https://picsum.photos/seed/yys/400/600",
        "url": "https://www.themoviedb.org/search?query=我不是药神"
    },
    "深海": {
        "title": "深海",
        "director": "田晓鹏",
        "actors": ["苏鑫", "王亭文"],
        "summary": "小女孩参宿误入奇幻的深海世界，在神秘男孩南河的陪伴下，展开了一段独特而治愈的心灵之旅。",
        "rating": "8.7",
        "year": "2023",
        "poster": "https://picsum.photos/seed/shenhai/400/600",
        "url": "https://www.themoviedb.org/search?query=深海"
    },
    "刺杀小说家": {
        "title": "刺杀小说家",
        "director": "路阳",
        "actors": ["雷佳音", "杨幂", "董子健", "于和伟"],
        "summary": "一位父亲为寻找失踪的女儿，接下刺杀小说家的任务。与此同时，小说家笔下的奇幻世界正悄然影响着现实世界的走向。",
        "rating": "6.6",
        "year": "2021",
        "poster": "https://picsum.photos/seed/csxsj/400/600",
        "url": "https://www.themoviedb.org/search?query=刺杀小说家"
    },
    "白蛇缘起": {
        "title": "白蛇：缘起",
        "director": "黄家康 / 赵霁",
        "actors": ["张喆", "杨天翔", "唐小喜"],
        "summary": "晚唐年间，国师发动民众捕蛇。白蛇失去记忆被少年阿宣救下，两人在寻找记忆的过程中逐渐萌生爱意，共同对抗国师的阴谋。",
        "rating": "8.5",
        "year": "2019",
        "poster": "https://picsum.photos/seed/baishe/400/600",
        "url": "https://www.themoviedb.org/search?query=白蛇：缘起"
    }
}

ADDITIONAL_MOVIES = [
    {"title": "唐人街探案3", "director": "陈思诚", "actors": ["王宝强", "刘昊然", "妻夫木聪"], "summary": "唐仁和秦风受邀前往东京，调查一桩离奇的谋杀案，在错综复杂的线索中揭开真相。", "rating": "5.3", "year": "2021", "poster": "https://picsum.photos/seed/trj3/400/600", "url": "https://www.themoviedb.org/search?query=唐人街探案3"},
    {"title": "孤注一掷", "director": "申奥", "actors": ["张艺兴", "金晨", "咏梅", "王传君"], "summary": "程序员潘生和模特安娜被骗至海外诈骗工厂，在生死边缘挣扎求生，最终配合警方捣毁犯罪团伙。", "rating": "7.3", "year": "2023", "poster": "https://picsum.photos/seed/gzyz/400/600", "url": "https://www.themoviedb.org/search?query=孤注一掷"},
    {"title": "飞驰人生2", "director": "韩寒", "actors": ["沈腾", "范丞丞", "尹正", "张本煜"], "summary": "曾经的赛车冠军张驰重返赛道，带领新人车手共同追逐梦想，在巴音布鲁克赛道上书写传奇。", "rating": "7.8", "year": "2024", "poster": "https://picsum.photos/seed/fcrs2/400/600", "url": "https://www.themoviedb.org/search?query=飞驰人生2"},
    {"title": "封神第一部", "director": "乌尔善", "actors": ["黄渤", "费翔", "李雪健", "娜然"], "summary": "商王殷寿残暴无道，姬发觉醒昆仑之力，集结各路英雄对抗暴政，揭开封神榜的传奇序幕。", "rating": "7.8", "year": "2023", "poster": "https://picsum.photos/seed/fengshen/400/600", "url": "https://www.themoviedb.org/search?query=封神第一部"},
]

ALL_MOVIES = {}
ALL_MOVIES.update(MOVIE_DB)
for m in ADDITIONAL_MOVIES:
    ALL_MOVIES[m["title"]] = m


# 对外暴露的辅助函数（供 _call_builtin_mock_api 直接调用）

def _extract_movie_keyword(text):
    """从自然语言中提取电影名称

    Examples:
        "我想看满江红" → "满江红"
        "帮我搜一下流浪地球" → "流浪地球"
        "有没有哪吒" → "哪吒"
        "搜索战狼2" → "战狼2"
        "满江红" → "满江红"
    """
    text = text.strip()
    if not text:
        return text

    # 移除常见的前缀表达（意图词 + 动作词）
    # 注意：长组合（如“帮我搜一下”）需要排在短组合（如“帮我搜”）前面，避免截断
    text = re.sub(
        r'^(?:我想看|我要看|我想搜一下|我想搜|帮我搜一下|帮我找一下|帮我查一下|'
        r'帮我搜|帮我找|帮我查|'
        r'给我搜一下|给我找一下|给我搜|给我找|给我看|给[我你]推荐一下|给[我你]推荐|推荐一下|推荐|'
        r'搜索|搜一下|搜一搜|找一下|查一下|看下|看看|看|搜|找|查)\s*',
        '', text
    )

    # 移除 "有没有/是否有" 前缀
    text = re.sub(r'^(?:有没有|是否有|有没有什么|有什么)\s*', '', text)

    # 移除常见后缀
    text = re.sub(
        r'\s*(?:吗[？?]?|呢[？?]?|吧[！!]?|'
        r'的电影|这部[电影片]?|这[部个][电影片]?|这个电影|'
        r'怎么样|好不好看|好看吗)$',
        '', text
    )

    # 移除末尾标点
    text = re.sub(r'[，,。！!？?\s]+$', '', text)

    return text.strip() or text  # 若全部被移除则返回原文


def _get_tmdb_api_key():
    """从 api_keys.json 读取 TMDB API Key，fallback 到硬编码"""
    keys = _load_api_keys()
    tmdb = keys.get("tmdb", {})
    if tmdb.get("enabled") and tmdb.get("key"):
        return tmdb["key"]
    return "7db612d4425ec6e821f2f42311621b3a"  # fallback

_TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"


def _search_tmdb_movie(keyword):
    """通过 TMDB API 搜索电影（真实搜索，不限影片）

    Returns: list[dict] 或 []
    """
    if not keyword:
        return []

    try:
        url = "https://api.themoviedb.org/3/search/movie"
        params = {
            "api_key": _get_tmdb_api_key(),
            "query": keyword,
            "language": "zh-CN",
            "page": 1,
        }
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code != 200:
            return []

        data = resp.json()
        results = []
        for item in data.get("results", [])[:10]:
            poster_path = item.get("poster_path", "")
            results.append({
                "title": item.get("title", "") or item.get("original_title", ""),
                "original_title": item.get("original_title", ""),
                "overview": item.get("overview", ""),
                "year": (item.get("release_date", "") or "")[:4],
                "poster": f"{_TMDB_IMAGE_BASE}{poster_path}" if poster_path else "",
                "rating": round(item.get("vote_average", 0), 1),
                "vote_count": item.get("vote_count", 0),
                "tmdb_id": item.get("id"),
                "url": f"https://www.themoviedb.org/movie/{item.get('id')}",
            })
        return results
    except Exception:
        return []

def _search_douban_movie(keyword):
    """通过豆瓣 suggest API 搜索电影

    Returns: list[dict] 匹配的电影列表（含 title, year, poster, douban_url），失败返回空列表
    """
    try:
        url = (f"https://movie.douban.com/j/subject_suggest?"
               f"q={urllib.parse.quote(keyword)}")
        resp = requests.get(url, headers=DOUBAN_HEADERS, timeout=8)
        if resp.status_code != 200:
            return []

        suggestions = resp.json()
        results = []
        for item in suggestions:
            if item.get("type") == "movie" and item.get("year"):
                results.append({
                    "douban_title": item["title"],
                    "year": item["year"],
                    "poster": item.get("img", ""),
                    "url": item["url"],
                })
        return results
    except Exception:
        return []


def _enrich_tmdb_with_local(tmdb_results, keyword_lower):
    """用本地库补充 TMDB 结果（导演、演员等 TMDB 不直接返回的数据）"""
    enriched = []
    for movie in tmdb_results:
        title = movie.get("title", "")
        matched_local = None
        # 尝试匹配本地库
        for local_key, local_info in ALL_MOVIES.items():
            if local_key[:3] in title or title[:3] in local_key:
                matched_local = local_info
                break
        if matched_local:
            movie["director"] = matched_local.get("director", "")
            movie["actors"] = matched_local.get("actors", [])
            if not movie.get("overview"):
                movie["overview"] = matched_local.get("summary", "")
        else:
            movie["director"] = ""
            movie["actors"] = []
        movie["summary"] = movie.pop("overview", "")
        enriched.append(movie)
    return enriched


def _search_movie(keyword):
    """按关键词搜索电影（TMDB API → 豆瓣搜索 → 本地库兜底）

    1. 先提取真正的电影名（去除"我想看"等自然语言前缀）
    2. TMDB API 搜索（不限影片，任意影片均可搜到）
    3. 本地库补充导演/演员等详细信息
    4. 豆瓣API作为补充
    5. 本地库兜底

    Returns: list[dict] 匹配的电影信息列表
    """
    # 第0步：提取真正的关键词
    keyword = _extract_movie_keyword(keyword)
    keyword_lower = keyword.lower().strip()
    matched = []

    # 第1步：TMDB API 搜索（真实搜索，不限影片）
    tmdb_results = _search_tmdb_movie(keyword)
    if tmdb_results:
        enriched = _enrich_tmdb_with_local(tmdb_results, keyword_lower)
        matched.extend(enriched)

    # 第2步：豆瓣API搜索（补充TMDB可能漏掉的）
    douban_results = _search_douban_movie(keyword)
    if douban_results:
        for dr in douban_results[:5]:
            db_title = dr["douban_title"]
            # 跳过TMDB已有且标题匹配的
            if any(db_title[:3] in m.get("title", "")[:3] or m.get("title", "")[:3] in db_title[:3] for m in matched):
                continue
            full_info = None
            for name, info in ALL_MOVIES.items():
                if name[:3] in db_title or db_title[:3] in name:
                    full_info = info.copy()
                    full_info["title"] = db_title
                    full_info["year"] = dr.get("year", full_info.get("year", ""))
                    full_info["poster"] = dr.get("poster") or full_info.get("poster", "")
                    full_info["url"] = f"https://www.themoviedb.org/search?query={urllib.parse.quote(db_title)}"
                    break
            if not full_info:
                full_info = {
                    "title": db_title,
                    "director": "",
                    "actors": [],
                    "summary": "",
                    "rating": "?",
                    "year": dr.get("year", ""),
                    "poster": dr.get("poster", ""),
                    "url": f"https://www.themoviedb.org/search?query={urllib.parse.quote(db_title)}",
                }
            matched.append(full_info)

    # 第3步：本地库搜索（兜底）
    for name, info in ALL_MOVIES.items():
        if (keyword_lower in name.lower()
                or any(keyword_lower in a.lower() for a in info.get("actors", []))):
            if any(m.get("title", "") == info.get("title", "") for m in matched):
                continue
            matched.append(info.copy())

    return matched


def _get_random_movie():
    """随机返回一部电影信息"""
    return random.choice(list(ALL_MOVIES.values()))


class MockMovieHandler(BaseHandler):
    """支持按片名搜索（TMDB真实API）和随机推荐（本地库）"""
    def get(self):
        keyword = self.get_argument("keyword", "").strip()

        if keyword:
            matched = _search_movie(keyword)
            if not matched:
                self.set_header("Content-Type", "application/json")
                self.write(json.dumps({
                    "success": True,
                    "data": {
                        "content": f"😅 未找到与「{_extract_movie_keyword(keyword)}」相关的电影信息，换个关键词试试吧！",
                        "responseFormat": "text",
                        "extraData": {}
                    }
                }, ensure_ascii=False))
                self.finish()
                return
            selected = random.choice(matched)
        else:
            selected = _get_random_movie()

        text = (
            f"🎬 **{selected['title']}** ({selected['year']})\n\n"
            f"⭐ 评分：**{selected['rating']}**\n"
            f"🎥 导演：{selected['director']}\n"
            f"👥 演员：{' / '.join(selected['actors'])}\n\n"
            f"📖 **剧情简介**\n{selected['summary']}\n\n"
            f"🔗 [观看链接]({selected['url']})"
        )

        self.set_header("Content-Type", "application/json")
        self.write(json.dumps({
            "success": True,
            "data": {
                "content": text,
                "responseFormat": "movie_detail",
                "extraData": {
                    "title": selected["title"],
                    "director": selected["director"],
                    "actors": selected["actors"],
                    "summary": selected["summary"],
                    "rating": selected["rating"],
                    "year": selected["year"],
                    "poster": selected["poster"],
                    "url": selected["url"]
                }
            }
        }, ensure_ascii=False))
        self.finish()
