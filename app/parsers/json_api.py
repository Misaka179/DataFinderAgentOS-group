"""
JSON API response parser.
Handles common JSON response shapes (search APIs, REST APIs).
"""
import json
import re

from app.parsers.base import BaseParser


class JsonApiParser(BaseParser):
    """Parse JSON API responses with heuristic field mapping.

    Automatically detects the array location (hits/results/data/items/top-level array)
    and maps common field names for title, url, and summary.
    """

    @staticmethod
    def parse(response_text, source_id, source_name, keyword):
        items = []

        # Parse JSON
        try:
            data = json.loads(response_text)
        except (json.JSONDecodeError, ValueError):
            return items

        # Find the result array
        result_array = JsonApiParser._find_array(data)
        if not result_array:
            return items

        for entry in result_array:
            if not isinstance(entry, dict):
                continue

            title = JsonApiParser._find_field(entry, ["title", "name", "headline", "subject"])
            url = JsonApiParser._find_field(entry, ["url", "link", "href"])
            summary = JsonApiParser._find_field(entry, ["summary", "description", "content", "body", "text"])

            if not title or len(title) < 4:
                continue

            # Clean summary
            summary_clean = re.sub(r'<[^>]+>', '', summary)[:200]

            items.append({
                "source_id": source_id,
                "keyword": keyword,
                "title": title.strip(),
                "url": url.strip() if url else "",
                "summary": summary_clean.strip(),
                "source_name": source_name
            })

            if len(items) >= 50:
                break

        return items

    @staticmethod
    def _find_array(data):
        """Detect the result array from common JSON response shapes."""
        if isinstance(data, list):
            return data

        if not isinstance(data, dict):
            return []

        # Common keys for result arrays
        for key in ("hits", "results", "data", "items", "posts", "articles", "entries"):
            val = data.get(key)
            if isinstance(val, list):
                return val

        # If a key's value is a dict with a hits/data key, recurse
        for key, val in data.items():
            if isinstance(val, dict):
                sub = JsonApiParser._find_array(val)
                if sub:
                    return sub

        return []

    @staticmethod
    def _find_field(entry, candidates):
        """Find the first matching field from a list of candidate key names."""
        for key in candidates:
            val = entry.get(key)
            if val and isinstance(val, str):
                return val
            # Some APIs put title/name inside nested objects
            if isinstance(val, dict):
                for sub_key in candidates:
                    sub_val = val.get(sub_key)
                    if sub_val and isinstance(sub_val, str):
                        return sub_val
            # Handle null/None string fields
            if isinstance(val, (type(None),)) and key in entry:
                val2 = entry.get(key)
                if val2 and isinstance(val2, str):
                    return val2
        return ""
