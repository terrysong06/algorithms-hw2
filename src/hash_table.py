from __future__ import annotations

import math
from typing import Generic, Iterator, TypeVar


_Value = TypeVar("_Value")


class Node(Generic[_Value]):
    def __init__(
        self,
        key: str,
        value: _Value,
        next_node: Node[_Value] | None = None,
    ) -> None:
        self.key = key
        self.value = value
        self.next = next_node


class ChainedHashTable(Generic[_Value]):
    def __init__(
        self,
        initial_capacity: int = 8,
        max_load: int | float | None = 0.75,
    ) -> None:
        if (
            isinstance(initial_capacity, bool)
            or not isinstance(initial_capacity, int)
            or initial_capacity <= 0
        ):
            raise ValueError("initial_capacity must be a positive integer")
        if max_load is not None:
            is_positive_finite_number = (
                isinstance(max_load, int)
                and not isinstance(max_load, bool)
                and max_load > 0
            ) or (
                isinstance(max_load, float)
                and math.isfinite(max_load)
                and max_load > 0
            )
            if not is_positive_finite_number:
                raise ValueError("max_load must be None or a positive finite number")

        self._buckets: list[Node[_Value] | None] = [None] * initial_capacity
        self._size = 0
        self._max_load = max_load

    @property
    def size(self) -> int:
        return self._size

    @property
    def capacity(self) -> int:
        return len(self._buckets)

    @property
    def load_factor(self) -> float:
        return self._size / self.capacity

    @staticmethod
    def _advance_hash(value: int, character: str, capacity: int) -> int:
        return (31 * value + ord(character)) % capacity

    @staticmethod
    def _validate_key(key: str) -> None:
        if not isinstance(key, str):
            raise TypeError("key must be a string")

    def _bucket_index(self, key: str, capacity: int) -> int:
        value = 0
        for character in key:
            value = self._advance_hash(value, character, capacity)
        return value

    def hash_index(self, key: str) -> int:
        self._validate_key(key)
        return self._bucket_index(key, self.capacity)

    def hash_trace(self, key: str) -> tuple[tuple[str, int], ...]:
        self._validate_key(key)
        value = 0
        steps = []
        for character in key:
            value = self._advance_hash(value, character, self.capacity)
            steps.append((character, value))
        return tuple(steps)

    def put(self, key: str, value: _Value) -> None:
        self._validate_key(key)
        index = self._bucket_index(key, self.capacity)
        node = self._buckets[index]
        while node is not None:
            if node.key == key:
                node.value = value
                return
            node = node.next

        self._buckets[index] = Node(key, value, self._buckets[index])
        self._size += 1
        if self._max_load is not None and self.load_factor > self._max_load:
            self._resize()

    def get(self, key: str) -> _Value | None:
        value, _ = self.get_with_probes(key)
        return value

    def get_with_probes(self, key: str) -> tuple[_Value | None, int]:
        self._validate_key(key)
        index = self._bucket_index(key, self.capacity)
        probes = 0
        node = self._buckets[index]
        while node is not None:
            probes += 1
            if node.key == key:
                return node.value, probes
            node = node.next
        return None, probes

    def iter_buckets(self) -> Iterator[tuple[int, tuple[tuple[str, _Value], ...]]]:
        for index, head in enumerate(self._buckets):
            chain = []
            node = head
            while node is not None:
                chain.append((node.key, node.value))
                node = node.next
            yield index, tuple(chain)

    def _resize(self) -> None:
        while self._max_load is not None and self.load_factor > self._max_load:
            new_capacity = self.capacity * 2
            new_buckets: list[Node[_Value] | None] = [None] * new_capacity

            for head in self._buckets:
                node = head
                while node is not None:
                    next_node = node.next
                    index = self._bucket_index(node.key, new_capacity)
                    node.next = new_buckets[index]
                    new_buckets[index] = node
                    node = next_node

            self._buckets = new_buckets
