"""
RSS / Atom feed parser.
Uses xml.etree.ElementTree from the standard library.
"""
import re
import xml.etree.ElementTree as ET

from app.parsers.base import BaseParser


class RssParser(BaseParser):
    """Parse RSS 2.0 and Atom feeds.

    RSS 2.0: <rss>/<channel>/<item> with <title>, <link>, <description>
    Atom:    <feed>/<entry> with <title>, <link href="...">, <summary> or <content>
    """

    # Atom namespace
    ATOM_NS = "http://www.w3.org/2005/Atom"

    @staticmethod
    def parse(response_text, source_id, source_name, keyword):
        items = []

        try:
            root = ET.fromstring(response_text)
        except ET.ParseError:
            # Try with encoding fix: strip before XML declaration
            try:
                clean = response_text.strip()
                root = ET.fromstring(clean)
            except ET.ParseError:
                return items

        tag = root.tag.lower()
        is_atom = "feed" in tag

        if is_atom:
            items = RssParser._parse_atom(root, source_id, source_name)
        else:
            items = RssParser._parse_rss(root, source_id, source_name)

        # Local keyword filtering (case-insensitive)
        if keyword:
            kw = keyword.lower()
            items = [
                it for it in items
                if kw in (it.get("title", "") + " " + it.get("summary", "")).lower()
            ]

        return items[:50]

    @staticmethod
    def _parse_rss(root, source_id, source_name):
        """Parse RSS 2.0 format."""
        items = []
        channel = root.find("channel")
        if channel is None:
            return items

        for item_el in channel.findall("item"):
            title_el = item_el.find("title")
            link_el = item_el.find("link")
            desc_el = item_el.find("description")

            title = RssParser._text(title_el)
            url = RssParser._text(link_el)
            summary = RssParser._clean_html(RssParser._text(desc_el))[:200]

            if not title or len(title) < 4:
                continue

            items.append({
                "source_id": source_id,
                "keyword": "",
                "title": RssParser._clean_html(title),
                "url": url,
                "summary": summary,
                "source_name": source_name
            })

        return items

    @staticmethod
    def _parse_atom(root, source_id, source_name):
        """Parse Atom feed format."""
        items = []
        ns = {"atom": RssParser.ATOM_NS}

        # Try namespace-aware first, fall back to direct children
        entries = root.findall("atom:entry", ns) or root.findall("entry")

        for entry_el in entries:
            title_el = entry_el.find("atom:title", ns) or entry_el.find("title")
            summary_el = (entry_el.find("atom:summary", ns) or entry_el.find("summary")
                          or entry_el.find("atom:content", ns) or entry_el.find("content"))

            # Atom <link> has href attribute
            link_el = entry_el.find("atom:link", ns) or entry_el.find("link")
            url = ""
            if link_el is not None:
                url = link_el.get("href", "") or RssParser._text(link_el)

            title = RssParser._text(title_el)
            summary = RssParser._clean_html(RssParser._text(summary_el))[:200]

            if not title or len(title) < 4:
                continue

            items.append({
                "source_id": source_id,
                "keyword": "",
                "title": RssParser._clean_html(title),
                "url": url,
                "summary": summary,
                "source_name": source_name
            })

        return items

    @staticmethod
    def _text(element):
        """Extract text from an Element, returning empty string if None."""
        if element is None:
            return ""
        return element.text or ""

    @staticmethod
    def _clean_html(text):
        """Strip HTML tags and normalize whitespace."""
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
