import threading
import unittest
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from urllib.parse import urlencode

from src.shortener import URLShortener
from src.server import ShortenerHandler


class ShortenerServerTest(unittest.TestCase):
    def setUp(self):
        self.shortener = URLShortener()
        ShortenerHandler.shortener = self.shortener
        self.linear_shortener = URLShortener(strategy="linear_probing")
        ShortenerHandler.linear_shortener = self.linear_shortener
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), ShortenerHandler)
        self.server.daemon_threads = True
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.start()
        self.port = self.server.server_address[1]

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def request(self, method, path, body=None, headers=()):
        connection = HTTPConnection("127.0.0.1", self.port, timeout=3)
        body_bytes = None if body is None else body.encode("utf-8")
        request_headers = tuple(headers)
        host = next(
            (
                value
                for name, value in request_headers
                if name.lower() == "host"
            ),
            f"127.0.0.1:{self.port}",
        )
        has_content_length = any(
            name.lower() == "content-length" for name, _ in request_headers
        )

        connection.putrequest(method, path, skip_host=True)
        connection.putheader("Host", host)
        for name, value in request_headers:
            if name.lower() != "host":
                connection.putheader(name, value)
        if body_bytes is not None and not has_content_length:
            connection.putheader("Content-Length", str(len(body_bytes)))
        connection.endheaders(body_bytes)

        response = connection.getresponse()
        status = response.status
        location = response.getheader("Location")
        content_type = response.getheader("Content-Type")
        response_body = response.read().decode("utf-8")
        connection.close()
        return status, location, content_type, response_body

    def post_url(self, url, headers=(), strategy=None):
        request_headers = (
            ("Content-Type", "application/x-www-form-urlencoded"),
            *headers,
        )
        fields = [("url", url)]
        if strategy is not None:
            fields.append(("strategy", strategy))
        return self.request(
            "POST",
            "/shorten",
            urlencode(fields),
            request_headers,
        )

    def test_home_page_has_url_form_and_navigation(self):
        status, _, content_type, body = self.request("GET", "/")

        self.assertEqual(status, 200)
        self.assertIn("text/html", content_type)
        self.assertIn("charset=utf-8", content_type)
        self.assertIn("<title>URL Shortener</title>", body)
        self.assertIn('action="/shorten"', body)
        self.assertIn('name="url"', body)
        self.assertIn('name="strategy"', body)
        self.assertIn('<option value="chaining" selected>Chaining</option>', body)
        self.assertIn(
            '<option value="linear_probing">Linear Probing</option>',
            body,
        )
        self.assertIn("Create Short URL", body)
        self.assertIn('href="/table"', body)

    def test_post_creates_and_reuses_short_url_with_copy_control(self):
        url = "https://example.com/path"

        first_status, _, _, first_body = self.post_url(url)
        second_status, _, _, second_body = self.post_url(url)

        expected_short_path = "/r/1"
        self.assertEqual(first_status, 200)
        self.assertEqual(second_status, 200)
        self.assertIn(f'href="{expected_short_path}"', first_body)
        self.assertIn(f'value="{expected_short_path}"', first_body)
        self.assertIn("window.location.origin", first_body)
        self.assertIn("field.value = shortUrl", first_body)
        self.assertNotIn("localhost", first_body)
        self.assertIn('id="copy-button"', first_body)
        self.assertIn("navigator.clipboard.writeText", first_body)
        self.assertIn(f'href="{expected_short_path}"', second_body)
        self.assertEqual(self.shortener.tables()[0][1].size, 1)

    def test_post_uses_browser_origin_when_server_host_is_internal(self):
        status, _, _, body = self.post_url(
            "https://example.com/secure",
            (
                ("Host", "localhost:8000"),
                (
                    "X-Forwarded-Host",
                    "bug-free-waffle-pjxjr5v756w4c7x7w-8000.app.github.dev",
                ),
                ("X-Forwarded-Proto", "https"),
            ),
        )

        self.assertEqual(status, 200)
        self.assertIn('href="/r/1"', body)
        self.assertIn("window.location.origin", body)
        self.assertNotIn("localhost", body)
        self.assertNotIn("bug-free-waffle", body)

    def test_chaining_and_linear_shortener_data_are_independent(self):
        chaining_url = "https://example.com/chaining"
        linear_url = "https://example.com/linear"
        chaining_status, _, _, chaining_body = self.post_url(chaining_url)
        linear_status, _, _, linear_body = self.post_url(
            linear_url,
            strategy="linear_probing",
        )

        self.assertEqual(chaining_status, 200)
        self.assertEqual(linear_status, 200)
        self.assertIn('href="/r/1"', chaining_body)
        self.assertIn('href="/r/linear/1"', linear_body)
        self.assertIn(
            '<option value="linear_probing" selected>Linear Probing</option>',
            linear_body,
        )
        self.assertEqual(self.shortener.tables()[0][1].size, 1)
        self.assertEqual(self.linear_shortener.tables()[0][1].size, 1)

        chaining_redirect = self.request("GET", "/r/1")
        linear_redirect = self.request("GET", "/r/linear/1")
        self.assertEqual(chaining_redirect[0], 302)
        self.assertEqual(chaining_redirect[1], chaining_url)
        self.assertEqual(linear_redirect[0], 302)
        self.assertEqual(linear_redirect[1], linear_url)

    def test_invalid_strategy_returns_bad_request(self):
        status, _, _, body = self.post_url(
            "https://example.com/invalid-strategy",
            strategy="unsupported",
        )

        self.assertEqual(status, 400)
        self.assertIn("valid URL", body)
        self.assertEqual(self.shortener.tables()[0][1].size, 0)
        self.assertEqual(self.linear_shortener.tables()[0][1].size, 0)

    def test_invalid_or_malformed_post_requests_return_bad_request(self):
        invalid_status, _, _, invalid_body = self.post_url("ftp://example.com")
        missing_status, _, _, missing_body = self.request(
            "POST",
            "/shorten",
            "other=value",
            (("Content-Type", "application/x-www-form-urlencoded"),),
        )
        media_status, _, _, media_body = self.request(
            "POST",
            "/shorten",
            '{"url":"https://example.com"}',
            (("Content-Type", "application/json"),),
        )

        self.assertEqual(invalid_status, 400)
        self.assertIn("valid URL", invalid_body)
        self.assertEqual(missing_status, 400)
        self.assertIn("valid URL", missing_body)
        self.assertEqual(media_status, 400)
        self.assertIn("URL-encoded form", media_body)

    def test_redirect_and_not_found_responses(self):
        url = "https://example.com/redirect"
        self.assertEqual(self.post_url(url)[0], 200)

        status, location, _, _ = self.request("GET", "/r/1")
        unknown_status, _, _, _ = self.request("GET", "/r/Z")
        invalid_status, _, _, _ = self.request("GET", "/r/bad_")
        path_status, _, _, _ = self.request("GET", "/missing")

        self.assertEqual(status, 302)
        self.assertEqual(location, url)
        self.assertEqual(unknown_status, 404)
        self.assertEqual(invalid_status, 404)
        self.assertEqual(path_status, 404)

    def test_table_displays_empty_buckets_and_both_chained_mappings(self):
        empty_status, _, _, empty_body = self.request("GET", "/table")
        self.assertEqual(empty_status, 200)
        self.assertIn("Empty bucket", empty_body)
        self.assertIn("Bucket count: 8", empty_body)
        self.assertIn("Entry count: 0", empty_body)

        first_url = "https://example.com/a"
        second_url = "https://example.com/i"
        self.shortener.shorten(first_url)
        self.shortener.shorten(second_url)
        status, _, _, body = self.request("GET", "/table")

        self.assertEqual(status, 200)
        self.assertIn("URL to code", body)
        self.assertIn("Code to URL", body)
        self.assertIn("Original URL", body)
        self.assertIn("Short code", body)
        self.assertIn("→", body)
        self.assertIn(first_url, body)
        self.assertIn(second_url, body)
        self.assertIn("Load factor: 0.250", body)
        url_table = self.shortener.tables()[0][1]
        bucket_index = url_table.hash_index(first_url)
        self.assertEqual(bucket_index, url_table.hash_index(second_url))
        self.assertIn(
            f"<strong>Final bucket index:</strong> {bucket_index}",
            body,
        )
        self.assertIn("Horner hash", body)
        self.assertIn('href="/"', body)

    def test_table_escapes_user_supplied_url(self):
        url = "https://example.com/?q=<script>alert(1)</script>"
        self.assertEqual(self.post_url(url)[0], 200)

        status, _, _, body = self.request("GET", "/table")

        self.assertEqual(status, 200)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", body)
        self.assertNotIn("<script>alert(1)</script>", body)

    def test_table_shows_linear_hash_and_probe_trace(self):
        self.linear_shortener.shorten("https://example.com/linear-table")

        status, _, _, body = self.request("GET", "/table")

        self.assertEqual(status, 200)
        self.assertIn("Chaining", body)
        self.assertIn("Linear Probing", body)
        self.assertIn("Initial hash index", body)
        self.assertIn("Probe path", body)
        self.assertIn("Final storage index", body)

    def test_unsupported_method_returns_method_not_allowed(self):
        status, _, _, _ = self.request("PUT", "/")

        self.assertEqual(status, 405)

    def test_post_to_unsupported_path_returns_not_found(self):
        status, _, _, _ = self.request(
            "POST",
            "/unknown",
            "",
            (("Content-Type", "application/x-www-form-urlencoded"),),
        )

        self.assertEqual(status, 404)


if __name__ == "__main__":
    unittest.main()
