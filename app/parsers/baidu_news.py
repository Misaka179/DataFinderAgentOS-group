"""
Baidu News HTML parser.
Extracted from admin_watch.py _parse_baidu_news() — logic unchanged.
"""
import re

from app.parsers.base import BaseParser


class BaiduNewsParser(BaseParser):
    """Parse Baidu News search result HTML using regex patterns."""

    @staticmethod
    def parse(response_text, source_id, source_name, keyword):
        items = []

        # Pattern 1: <h3>...<a href="...">title</a> (Baidu news typical)
        title_links = re.findall(
            r'<h3[^>]*>.*?<a[^>]*href="(https?://[^"]+)"[^>]*>(.*?)</a>',
            response_text, re.DOTALL
        )

        # Pattern 2 (fallback): any <a href="...">title</a>
        if not title_links:
            title_links = re.findall(
                r'<a[^>]*href="(https?://[^"]+)"[^>]*>(.*?)</a>',
                response_text, re.DOTALL
            )

        # Extract summaries
        summaries = re.findall(
            r'<span[^>]*class="[^"]*content-right[^"]*"[^>]*>(.*?)</span>',
            response_text, re.DOTALL
        )
        if not summaries:
            summaries = re.findall(
                r'<div[^>]*class="[^"]*c-abstract[^"]*"[^>]*>(.*?)</div>',
                response_text, re.DOTALL
            )
        if not summaries:
            summaries = re.findall(
                r'<span[^>]*class="[^"]*abstract[^"]*"[^>]*>(.*?)</span>',
                response_text, re.DOTALL
            )

        # Deduplicate by title
        seen_titles = set()

        for i, (url, title) in enumerate(title_links):
            # Strip HTML tags from title
            title_clean = re.sub(r'<[^>]+>', '', title).strip()
            if not title_clean:
                continue

            if title_clean in seen_titles:
                continue
            if len(title_clean) < 4:
                continue

            seen_titles.add(title_clean)

            # Normalize URL
            normalized_url = url.strip()
            if normalized_url.startswith("//"):
                normalized_url = "https:" + normalized_url
            elif normalized_url.startswith("/"):
                normalized_url = "https://www.baidu.com" + normalized_url
            elif not normalized_url.startswith("http://") and not normalized_url.startswith("https://"):
                normalized_url = "https://" + normalized_url

            # Get corresponding summary
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

            if len(items) >= 50:
                break

        return items
