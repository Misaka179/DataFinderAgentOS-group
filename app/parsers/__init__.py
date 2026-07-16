"""
Parser registry — maps source_type strings to parser classes.
"""
from app.parsers.baidu_news import BaiduNewsParser
from app.parsers.rss import RssParser
from app.parsers.json_api import JsonApiParser


class ParserRegistry:
    """Registry of all available source parsers.

    Usage:
        parser_cls = ParserRegistry.get_parser("rss")
        items = parser_cls.parse(html, source_id, source_name, keyword)
    """

    _parsers = {
        "baidu_news": BaiduNewsParser,
        "rss": RssParser,
        "json_api": JsonApiParser,
    }

    @classmethod
    def get_parser(cls, source_type):
        """Return the parser class for the given source_type.

        Falls back to BaiduNewsParser if type is missing or unknown.
        """
        if not source_type:
            return cls._parsers["baidu_news"]
        return cls._parsers.get(source_type, cls._parsers["baidu_news"])

    @classmethod
    def get_available_types(cls):
        """Return list of registered source_type strings."""
        return list(cls._parsers.keys())
