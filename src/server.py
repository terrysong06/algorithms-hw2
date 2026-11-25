import argparse
import html
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.hash_table import ChainedHashTable
from src.linear_probing import LinearProbingHashTable
from src.shortener import URLShortener


_MAX_FORM_BYTES = 65536
_FORM_CONTENT_TYPE = "application/x-www-form-urlencoded"
_STYLES = """
<style>
:root {
  color-scheme: light;
  font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  color: #172554;
  background: #f5f8ff;
}
* { box-sizing: border-box; }
body { margin: 0; min-height: 100vh; background: #f5f8ff; }
a { color: #1d4ed8; }
.page { width: min(100% - 32px, 1040px); margin: 0 auto; padding: 48px 0; }
.card {
  background: #fff;
  border: 1px solid #dbeafe;
  border-radius: 16px;
  box-shadow: 0 12px 32px #1e3a8a12;
  padding: clamp(20px, 5vw, 40px);
  margin-bottom: 24px;
}
h1, h2 { color: #163b7a; line-height: 1.2; }
h1 { margin-top: 0; font-size: clamp(2rem, 5vw, 2.8rem); }
h2 { margin-top: 0; }
p { line-height: 1.6; }
label { display: block; font-weight: 650; margin: 20px 0 8px; }
input[type="url"], input[readonly], select {
  width: 100%;
  min-width: 0;
  border: 1px solid #bfdbfe;
  border-radius: 9px;
  padding: 13px 14px;
  color: #172554;
  font: inherit;
}
input:focus { outline: 3px solid #bfdbfe; border-color: #2563eb; }
.actions { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 18px; }
.button, button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 0;
  border-radius: 9px;
  padding: 11px 17px;
  background: #2563eb;
  color: #fff;
  font: inherit;
  font-weight: 650;
  text-decoration: none;
  cursor: pointer;
}
.button.secondary { background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; }
.error { color: #b91c1c; background: #fef2f2; border: 1px solid #fecaca; padding: 12px; border-radius: 8px; }
.result { margin-top: 24px; padding: 18px; border-radius: 12px; background: #eff6ff; }
.result-link { overflow-wrap: anywhere; font-weight: 650; }
.copy-status { display: block; min-height: 1.5em; color: #166534; margin-top: 8px; }
.table-card { padding: clamp(16px, 3vw, 28px); }
.table-summary { color: #475569; }
.table-scroll { overflow-x: auto; margin: 16px 0 28px; }
table { width: 100%; border-collapse: collapse; background: #fff; }
th, td { padding: 12px; border: 1px solid #dbeafe; text-align: left; vertical-align: top; }
th { color: #1e3a8a; background: #eff6ff; }
td.bucket-number { width: 90px; white-space: nowrap; font-weight: 700; }
.chain { min-width: 280px; }
.chain-node { overflow-wrap: anywhere; }
.chain-node code { white-space: pre-wrap; overflow-wrap: anywhere; }
.chain-node small { display: block; color: #475569; margin-top: 6px; }
.chain-arrow { color: #2563eb; font-size: 1.2em; font-weight: 750; padding: 0 8px; }
.empty { color: #94a3b8; font-style: italic; }
@media (max-width: 600px) {
  .page { width: min(100% - 20px, 1040px); padding: 24px 0; }
  .actions { flex-direction: column; }
  .actions > * { width: 100%; }
  th, td { padding: 9px; }
}
</style>
"""


def _render_page(content: str) -> str:
    return (
        "<!doctype html>\n"
        '<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>URL Shortener</title>"
        f"{_STYLES}</head><body><main class=\"page\">{content}</main></body></html>"
    )


def render_home(
    short_url: str | None = None,
    error_message: str | None = None,
    strategy: str = "chaining",
) -> str:
    error_html = ""
    if error_message is not None:
        error_html = (
            '<p class="error" role="alert">'
            f"{html.escape(error_message)}"
            "</p>"
        )

    result_html = ""
    if short_url is not None:
        escaped_short_url = html.escape(short_url, quote=True)
        result_html = (
            '<section class="result" aria-live="polite">'
            "<h2>Your short URL</h2>"
            f'<p><a class="result-link" href="{escaped_short_url}">'
            f"{escaped_short_url}</a></p>"
            f'<input id="short-url" type="text" readonly value="{escaped_short_url}" '
            'aria-label="Generated short URL">'
            '<div class="actions"><button id="copy-button" type="button">'
            "Copy short URL</button></div>"
            '<span id="copy-status" class="copy-status" aria-live="polite"></span>'
            "</section>"
            "<script>"
            'const link = document.querySelector(".result-link"); '
            'const field = document.getElementById("short-url"); '
            "const shortUrl = window.location.origin + link.getAttribute('href'); "
            "link.href = shortUrl; link.textContent = shortUrl; "
            "field.value = shortUrl; "
            'document.getElementById("copy-button").addEventListener("click", '
            "function () { "
            'navigator.clipboard.writeText(field.value).then(function () { '
            'document.getElementById("copy-status").textContent = "Copied."; '
            '}); });'
            "</script>"
        )

    chaining_selected = " selected" if strategy == "chaining" else ""
    linear_selected = " selected" if strategy == "linear_probing" else ""
    content = (
        '<section class="card">'
        "<h1>URL Shortener</h1>"
        "<p>Enter a valid HTTP or HTTPS URL to create a short link.</p>"
        f"{error_html}"
        '<form action="/shorten" method="post">'
        '<label for="url">Original URL</label>'
        '<input id="url" name="url" type="url" maxlength="2048" '
        'placeholder="https://example.com/page" required>'
        '<label for="strategy">Hash table strategy</label>'
        '<select id="strategy" name="strategy">'
        f'<option value="chaining"{chaining_selected}>Chaining</option>'
        f'<option value="linear_probing"{linear_selected}>Linear Probing</option>'
        "</select>"
        '<div class="actions">'
        '<button type="submit">Create Short URL</button>'
        '<a class="button secondary" href="/table">View hash tables</a>'
        "</div></form>"
        f"{result_html}"
        "</section>"
    )
    return _render_page(content)


def _render_hash_trace(
    table: ChainedHashTable[str] | LinearProbingHashTable[str],
    key: str,
    storage_index: int,
) -> str:
    previous_value = 0
    steps = ["h = 0"]
    for character, value in table.hash_trace(key):
        steps.append(
            f"h = (31 * {previous_value} + ord({character!r})) "
            f"% {table.capacity} = {value}"
        )
        previous_value = value
    trace = html.escape("; ".join(steps))
    bucket_index = table.hash_index(key)
    if isinstance(table, LinearProbingHashTable):
        probe_path = " → ".join(str(index) for index in table.probe_trace(key))
        return (
            f"<small><strong>Horner hash:</strong> {trace}<br>"
            f"<strong>Initial hash index:</strong> {bucket_index}<br>"
            f"<strong>Probe path:</strong> {html.escape(probe_path)}<br>"
            f"<strong>Final storage index:</strong> {storage_index}</small>"
        )
    return (
        f"<small><strong>Horner hash:</strong> {trace}<br>"
        f"<strong>Final bucket index:</strong> {storage_index}</small>"
    )


def render_table(
    shorteners: tuple[tuple[str, URLShortener], ...],
) -> str:
    sections = []
    for strategy_name, shortener in shorteners:
        for table_name, table in shortener.tables():
            if table_name == "url_to_code":
                title = "URL to code"
                key_label = "Original URL"
                value_label = "Short code"
            else:
                title = "Code to URL"
                key_label = "Short code"
                value_label = "Original URL"

            bucket_rows = []
            for bucket_index, chain in table.iter_buckets():
                if chain:
                    nodes = []
                    for key, value in chain:
                        nodes.append(
                            '<div class="chain-node">'
                            f"<strong>{key_label}:</strong> "
                            f"<code>{html.escape(key)}</code><br>"
                            f"<strong>{value_label}:</strong> "
                            f"<code>{html.escape(value)}</code>"
                            f"{_render_hash_trace(table, key, bucket_index)}"
                            "</div>"
                        )
                    bucket_content = (
                        '<span class="chain">'
                        + ' <span class="chain-arrow">→</span> '.join(nodes)
                        + "</span>"
                    )
                else:
                    bucket_content = '<span class="empty">Empty bucket</span>'
                bucket_rows.append(
                    "<tr>"
                    f'<td class="bucket-number">{bucket_index}</td>'
                    f"<td>{bucket_content}</td>"
                    "</tr>"
                )

            bucket_column = (
                "Slot" if isinstance(table, LinearProbingHashTable) else "Bucket"
            )
            value_column = (
                "Entry" if isinstance(table, LinearProbingHashTable) else "Chain"
            )
            sections.append(
                '<section class="card table-card">'
                f"<h2>{strategy_name} - {title}</h2>"
                '<p class="table-summary">'
                f"Bucket count: {table.capacity} · "
                f"Entry count: {table.size} · "
                f"Load factor: {table.load_factor:.3f}"
                "</p>"
                '<div class="table-scroll"><table>'
                f"<thead><tr><th>{bucket_column}</th><th>{value_column}</th></tr></thead>"
                f"<tbody>{''.join(bucket_rows)}</tbody>"
                "</table></div>"
                "</section>"
            )

    content = (
        '<section class="card">'
        "<h1>Hash table visualization</h1>"
        "<p>Hash table entries and Horner hash calculations for both strategies.</p>"
        f"{''.join(sections)}"
        '<div class="actions"><a class="button secondary" href="/">'
        "Back to URL Shortener</a></div>"
        "</section>"
    )
    return _render_page(content)


class ShortenerHandler(BaseHTTPRequestHandler):
    shortener = URLShortener()
    linear_shortener = URLShortener(strategy="linear_probing")

    def _send_html(
        self,
        status: int,
        body: str,
        allow: str | None = None,
    ) -> None:
        encoded_body = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded_body)))
        if allow is not None:
            self.send_header("Allow", allow)
        self.end_headers()
        self.wfile.write(encoded_body)

    def _send_error_page(
        self,
        status: int,
        heading: str,
        message: str,
        allow: str | None = None,
    ) -> None:
        body = _render_page(
            '<section class="card">'
            f"<h1>{html.escape(heading)}</h1>"
            f'<p class="error" role="alert">{html.escape(message)}</p>'
            '<a class="button secondary" href="/">Back to URL Shortener</a>'
            "</section>"
        )
        self._send_html(status, body, allow)

    def _request_path(self) -> str:
        try:
            return urlsplit(self.path).path
        except ValueError:
            return ""

    def _read_form(self) -> tuple[str, str]:
        if self.headers.get_content_type() != _FORM_CONTENT_TYPE:
            raise ValueError("request must use URL-encoded form data")

        raw_length = self.headers.get("Content-Length")
        if raw_length is None:
            raise ValueError("request body length is required")
        try:
            content_length = int(raw_length)
        except ValueError as error:
            raise ValueError("request body length is invalid") from error
        if content_length < 0 or content_length > _MAX_FORM_BYTES:
            raise ValueError("request body length is invalid")

        encoded_body = self.rfile.read(content_length)
        if len(encoded_body) != content_length:
            raise ValueError("request body is incomplete")
        try:
            form_body = encoded_body.decode("utf-8")
            fields = parse_qsl(
                form_body,
                keep_blank_values=True,
                strict_parsing=True,
                max_num_fields=10,
            )
        except (UnicodeDecodeError, ValueError) as error:
            raise ValueError("request form data is invalid") from error

        urls = [value for name, value in fields if name == "url"]
        if len(urls) != 1:
            raise ValueError("request must include exactly one URL")
        strategies = [value for name, value in fields if name == "strategy"]
        if len(strategies) > 1:
            raise ValueError("request must include at most one strategy")
        strategy = strategies[0] if strategies else "chaining"
        if strategy not in ("chaining", "linear_probing"):
            raise ValueError("request strategy is invalid")
        return urls[0], strategy

    def do_GET(self) -> None:
        path = self._request_path()
        if path == "/":
            self._send_html(200, render_home())
            return
        if path == "/table":
            self._send_html(
                200,
                render_table(
                    (
                        ("Chaining", self.shortener),
                        ("Linear Probing", self.linear_shortener),
                    )
                ),
            )
            return
        if path == "/shorten":
            self._send_error_page(
                405,
                "Method not allowed",
                "Use POST to create a short URL.",
                "POST",
            )
            return
        if path.startswith("/r/"):
            code = path[len("/r/") :]
            shortener = self.shortener
            if code.startswith("linear/"):
                code = code[len("linear/") :]
                shortener = self.linear_shortener
            try:
                url = shortener.expand(code)
            except (KeyError, ValueError):
                self._send_error_page(
                    404,
                    "Short URL not found",
                    "This short URL does not exist.",
                )
                return
            self.send_response(302)
            self.send_header("Location", url)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        self._send_error_page(404, "Not found", "The requested page was not found.")

    def do_POST(self) -> None:
        path = self._request_path()
        if path != "/shorten":
            if path in ("/", "/table") or path.startswith("/r/"):
                self._send_error_page(
                    405,
                    "Method not allowed",
                    "Use GET for this page.",
                    "GET",
                )
            else:
                self._send_error_page(
                    404,
                    "Not found",
                    "The requested page was not found.",
                )
            return

        strategy = "chaining"
        try:
            url, strategy = self._read_form()
            shortener = (
                self.linear_shortener
                if strategy == "linear_probing"
                else self.shortener
            )
            code = shortener.shorten(url)
        except ValueError:
            self.close_connection = True
            self._send_html(
                400,
                render_home(
                    error_message=(
                        "Please enter a valid URL, select a strategy, and submit "
                        "a URL-encoded form."
                    ),
                    strategy=strategy,
                ),
            )
            return

        short_path = f"/r/{code}"
        if strategy == "linear_probing":
            short_path = f"/r/linear/{code}"
        self._send_html(
            200,
            render_home(short_url=short_path, strategy=strategy),
        )

    def do_PUT(self) -> None:
        self._send_error_page(
            405,
            "Method not allowed",
            "Use GET or POST.",
            "GET, POST",
        )

    def do_DELETE(self) -> None:
        self.do_PUT()

    def do_PATCH(self) -> None:
        self.do_PUT()

    def do_OPTIONS(self) -> None:
        self.do_PUT()

    def do_HEAD(self) -> None:
        self.send_response(405)
        self.send_header("Allow", "GET, POST")
        self.send_header("Content-Length", "0")
        self.end_headers()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the URL shortener web server.")
    parser.add_argument("--port", type=int, default=8000)
    arguments = parser.parse_args()

    server = ThreadingHTTPServer(("0.0.0.0", arguments.port), ShortenerHandler)
    print(f"URL Shortener listening on port {arguments.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
