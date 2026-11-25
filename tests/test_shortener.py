import unittest

from src.base62 import encode
from src.shortener import URLShortener


class URLShortenerTest(unittest.TestCase):
    def test_first_url_receives_code_one(self):
        shortener = URLShortener()

        self.assertEqual(shortener.shorten("https://example.com/first"), "1")

    def test_codes_encode_monotonically_increasing_serial_numbers(self):
        shortener = URLShortener()
        urls = tuple(f"https://example.com/item/{index}" for index in range(62))

        codes = tuple(shortener.shorten(url) for url in urls)

        self.assertEqual(codes[0], "1")
        self.assertEqual(codes[1], "2")
        self.assertEqual(codes[60], "Z")
        self.assertEqual(codes[61], "10")
        for serial, code in enumerate(codes, start=1):
            with self.subTest(serial=serial):
                self.assertEqual(code, encode(serial))

    def test_duplicate_url_returns_existing_code_without_consuming_serial(self):
        shortener = URLShortener()
        url = "https://example.com/same"

        first_code = shortener.shorten(url)
        duplicate_code = shortener.shorten(url)

        self.assertEqual(first_code, "1")
        self.assertEqual(duplicate_code, first_code)
        self.assertEqual(shortener.shorten("https://example.com/next"), "2")

    def test_expand_restores_original_url_exactly(self):
        shortener = URLShortener()
        url = "https://example.com/a/path?q=one%20two#section"

        code = shortener.shorten(url)

        self.assertEqual(shortener.expand(code), url)

    def test_invalid_urls_raise_value_error(self):
        shortener = URLShortener()
        invalid_urls = (
            "",
            "example.com/path",
            "ftp://example.com",
            "https:///path",
            " https://example.com",
            "https://example.com/path with space",
            "https://example.com/path\x01",
            "https://example.com:99999",
        )

        for url in invalid_urls:
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    shortener.shorten(url)

    def test_non_string_url_raises_type_error(self):
        with self.assertRaises(TypeError):
            URLShortener().shorten(None)

    def test_invalid_codes_raise_value_error(self):
        shortener = URLShortener()

        for code in ("", "bad_"):
            with self.subTest(code=code):
                with self.assertRaises(ValueError):
                    shortener.expand(code)

    def test_non_string_code_raises_type_error(self):
        with self.assertRaises(TypeError):
            URLShortener().expand(None)

    def test_unregistered_valid_code_raises_key_error(self):
        with self.assertRaises(KeyError):
            URLShortener().expand("Z")

    def test_url_with_exactly_2048_characters_is_accepted(self):
        shortener = URLShortener()
        prefix = "https://example.com/"
        url = prefix + "a" * (2048 - len(prefix))

        self.assertEqual(len(url), 2048)
        self.assertEqual(shortener.shorten(url), "1")
        self.assertEqual(shortener.expand("1"), url)

    def test_url_longer_than_2048_characters_is_rejected(self):
        shortener = URLShortener()
        prefix = "https://example.com/"
        url = prefix + "a" * (2049 - len(prefix))

        self.assertEqual(len(url), 2049)
        with self.assertRaises(ValueError):
            shortener.shorten(url)

    def test_invalid_input_does_not_consume_serial_number(self):
        shortener = URLShortener()
        self.assertEqual(shortener.shorten("https://example.com/first"), "1")

        with self.assertRaises(ValueError):
            shortener.shorten("not-a-url")

        self.assertEqual(shortener.shorten("https://example.com/second"), "2")

    def test_urls_are_compared_without_normalization(self):
        shortener = URLShortener()
        without_trailing_slash = "https://example.com"
        with_trailing_slash = "https://example.com/"

        first_code = shortener.shorten(without_trailing_slash)
        second_code = shortener.shorten(with_trailing_slash)

        self.assertNotEqual(first_code, second_code)
        self.assertEqual(shortener.expand(first_code), without_trailing_slash)
        self.assertEqual(shortener.expand(second_code), with_trailing_slash)

    def test_rehash_preserves_mappings_and_allows_new_urls(self):
        shortener = URLShortener()
        urls = tuple(f"https://example.com/bulk/{index}" for index in range(7))
        codes = tuple(shortener.shorten(url) for url in urls)

        tables = tuple(table for _, table in shortener.tables())
        self.assertEqual(len(tables), 2)
        for table in tables:
            with self.subTest(capacity=table.capacity):
                self.assertGreater(table.capacity, 8)

        for url, code in zip(urls, codes):
            with self.subTest(url=url):
                self.assertEqual(shortener.shorten(url), code)
                self.assertEqual(shortener.expand(code), url)

        self.assertEqual(shortener.shorten(urls[3]), codes[3])

        new_url = "https://example.com/after-rehash"
        new_code = shortener.shorten(new_url)
        self.assertEqual(new_code, encode(len(urls) + 1))
        self.assertEqual(shortener.expand(new_code), new_url)


if __name__ == "__main__":
    unittest.main()
