"""
Base parser class. All source parsers inherit from this.
"""


class BaseParser:
    """Abstract base for all source parsers.

    Subclasses override parse() to convert raw HTTP response text
    into a standardized list of item dicts.
    """

    @staticmethod
    def parse(response_text, source_id, source_name, keyword):
        """Parse raw response text into standardized item dicts.

        Args:
            response_text: Raw HTTP response body (str)
            source_id: watch_sources.id
            source_name: watch_sources.name
            keyword: Search keyword used

        Returns:
            list[dict] with keys: source_id, keyword, title, url, summary, source_name
        """
        raise NotImplementedError
