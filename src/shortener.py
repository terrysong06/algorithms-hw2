import unicodedata
from typing import Literal
from urllib.parse import urlsplit

from src.base62 import decode, encode
from src.hash_table import ChainedHashTable
from src.linear_probing import LinearProbingHashTable


class URLShortener:
    def __init__(
        self,
        initial_capacity: int = 8,
        max_load: int | float | None = 0.75,
        strategy: Literal["chaining", "linear_probing"] = "chaining",
    ) -> None:
        self.strategy = strategy
        if strategy == "chaining":
            self._url_to_code: ChainedHashTable[str] | LinearProbingHashTable[str] = (
                ChainedHashTable(initial_capacity, max_load)
            )
            self._code_to_url: ChainedHashTable[str] | LinearProbingHashTable[str] = (
                ChainedHashTable(initial_capacity, max_load)
            )
        elif strategy == "linear_probing":
            self._url_to_code = LinearProbingHashTable(initial_capacity, max_load)
            self._code_to_url = LinearProbingHashTable(initial_capacity, max_load)
        else:
            raise ValueError("strategy must be 'chaining' or 'linear_probing'")
        self._next_serial = 1

    def shorten(self, url: str) -> str:
        if not isinstance(url, str):
            raise TypeError("url must be a string")
        if len(url) > 2048:
            raise ValueError("url must be at most 2048 characters")
        if any(
            character.isspace() or unicodedata.category(character) == "Cc"
            for character in url
        ):
            raise ValueError("url must not contain whitespace or control characters")

        try:
            parsed = urlsplit(url)
            port = parsed.port
        except ValueError as error:
            raise ValueError("url is not valid") from error

        if parsed.scheme.lower() not in ("http", "https") or not parsed.hostname:
            raise ValueError("url must have an HTTP or HTTPS scheme and a hostname")
        if port is not None and not 1 <= port <= 65535:
            raise ValueError("url port must be between 1 and 65535")

        existing_code = self._url_to_code.get(url)
        if existing_code is not None:
            return existing_code

        code = encode(self._next_serial)
        self._url_to_code.put(url, code)
        self._code_to_url.put(code, url)
        self._next_serial += 1
        return code

    def expand(self, code: str) -> str:
        if not isinstance(code, str):
            raise TypeError("code must be a string")
        decode(code)

        url = self._code_to_url.get(code)
        if url is None:
            raise KeyError(code)
        return url

    def tables(
        self,
    ) -> tuple[
        tuple[str, ChainedHashTable[str] | LinearProbingHashTable[str]],
        tuple[str, ChainedHashTable[str] | LinearProbingHashTable[str]],
    ]:
        return (
            ("url_to_code", self._url_to_code),
            ("code_to_url", self._code_to_url),
        )
