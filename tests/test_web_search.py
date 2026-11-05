import unittest
from ais.web_search import _GoogleResultsParser, _unwrap_google_url, _is_public_result_url, format_search_context, SearchResult


class TestGoogleSearchParsing(unittest.TestCase):
    def test_extracts_result_title_and_url(self):
        html = '<a href="https://example.org/article"><h3>Example Article</h3></a>'
        parser = _GoogleResultsParser()
        parser.feed(html)
        results = parser.finish()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "Example Article")
        self.assertEqual(results[0].url, "https://example.org/article")

    def test_unwraps_google_redirect(self):
        self.assertEqual(
            _unwrap_google_url("/url?q=https%3A%2F%2Fexample.org%2Fpage&sa=U"),
            "https://example.org/page"
        )

    def test_rejects_non_web_and_google_urls(self):
        self.assertIsNone(_unwrap_google_url("javascript:alert(1)"))
        self.assertFalse(_is_public_result_url("https://www.google.com/search?q=test"))

    def test_formats_context_with_source_links(self):
        text = format_search_context("test", [SearchResult("Example", "https://example.org", "A short snippet")])
        self.assertIn("Google Search results for: test", text)
        self.assertIn("https://example.org", text)


if __name__ == "__main__":
    unittest.main()
