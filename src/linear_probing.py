from __future__ import annotations

import math
from typing import Generic, Iterator, TypeVar


_Value = TypeVar("_Value")


class LinearProbingHashTable(Generic[_Value]):
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

        self._slots: list[tuple[str, _Value] | None] = [None] * initial_capacity
        self._size = 0
        self._max_load = max_load

    @property
    def size(self) -> int:
        return self._size

    @property
    def capacity(self) -> int:
        return len(self._slots)

    @property
    def load_factor(self) -> float:
        return self._size / self.capacity

    @staticmethod
    def _validate_key(key: str) -> None:
        if not isinstance(key, str):
            raise TypeError("key must be a string")

    def _bucket_index(self, key: str, capacity: int) -> int:
        value = 0
        for character in key:
            value = (31 * value + ord(character)) % capacity
        return value

    def hash_index(self, key: str) -> int:
        self._validate_key(key)
        return self._bucket_index(key, self.capacity)

    def hash_trace(self, key: str) -> tuple[tuple[str, int], ...]:
        self._validate_key(key)
        value = 0
        steps = []
        for character in key:
            value = (31 * value + ord(character)) % self.capacity
            steps.append((character, value))
        return tuple(steps)

    def _probe_indices(self, key: str) -> Iterator[int]:
        index = self._bucket_index(key, self.capacity)
        for _ in range(self.capacity):
            yield index
            index = (index + 1) % self.capacity

    def probe_trace(self, key: str) -> tuple[int, ...]:
        self._validate_key(key)
        indices = []
        for index in self._probe_indices(key):
            indices.append(index)
            entry = self._slots[index]
            if entry is None or entry[0] == key:
                break
        return tuple(indices)

    def put(self, key: str, value: _Value) -> None:
        self._validate_key(key)
        for index in self._probe_indices(key):
            entry = self._slots[index]
            if entry is not None and entry[0] == key:
                self._slots[index] = (key, value)
                return
            if entry is None:
                if (
                    self._max_load is not None
                    and (self._size + 1) / self.capacity > self._max_load
                ):
                    self._resize()
                    self.put(key, value)
                    return
                self._slots[index] = (key, value)
                self._size += 1
                return

        if self._max_load is None:
            raise OverflowError("hash table is full")
        self._resize()
        self.put(key, value)

    def get(self, key: str) -> _Value | None:
        value, _ = self.get_with_probes(key)
        return value

    def get_with_probes(self, key: str) -> tuple[_Value | None, int]:
        self._validate_key(key)
        for probes, index in enumerate(self._probe_indices(key), start=1):
            entry = self._slots[index]
            if entry is None:
                return None, probes
            if entry[0] == key:
                return entry[1], probes
        return None, self.capacity

    def iter_buckets(self) -> Iterator[tuple[int, tuple[tuple[str, _Value], ...]]]:
        for index, entry in enumerate(self._slots):
            if entry is None:
                yield index, ()
            else:
                yield index, (entry,)

    def _resize(self) -> None:
        old_slots = self._slots
        self._slots = [None] * (self.capacity * 2)
        self._size = 0
        for entry in old_slots:
            if entry is not None:
                self._insert_without_resize(*entry)

    def _insert_without_resize(self, key: str, value: _Value) -> None:
        for index in self._probe_indices(key):
            if self._slots[index] is None:
                self._slots[index] = (key, value)
                self._size += 1
                return
        raise OverflowError("hash table is full")
