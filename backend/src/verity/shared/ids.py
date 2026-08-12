"""UUID version 7 generation.

Every primary key in this system is a UUIDv7 (ADR-0002): time-ordered, so index
locality survives, and collision-free across CSV import, connector sync, and asset
merge.

Generated in the application rather than by the database. Postgres 16 has no
``uuidv7()``, and the audit trail needs the identifier of a row before the insert
that creates it.
"""

from __future__ import annotations

import secrets
import threading
import time
import uuid
from datetime import UTC, datetime
from typing import Final

_UNIX_TS_MS_SHIFT: Final = 80
_VERSION_SHIFT: Final = 76
_COUNTER_SHIFT: Final = 64
_VARIANT_SHIFT: Final = 62

_UNIX_TS_MS_MASK: Final = 0xFFFF_FFFF_FFFF
_COUNTER_MAX: Final = 0xFFF
_VERSION: Final = 0x7
_VARIANT: Final = 0b10


class _Uuid7Generator:
    """Monotonic UUIDv7 source.

    RFC 9562 leaves ``rand_a`` free for a monotonic counter, which is what makes
    two identifiers minted in the same millisecond still sort in generation order.
    Without it, rows created in the same millisecond order arbitrarily, and
    "created_at, id" pagination skips or repeats rows.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._last_ms = -1
        self._counter = 0

    def generate(self) -> uuid.UUID:
        with self._lock:
            now_ms = time.time_ns() // 1_000_000
            if now_ms > self._last_ms:
                self._last_ms = now_ms
                self._counter = 0
            elif self._counter < _COUNTER_MAX:
                # Same millisecond, or the clock stepped backwards. Either way the
                # counter keeps the sequence ordered.
                self._counter += 1
            else:
                # 4096 identifiers inside one millisecond. Borrow from the next.
                self._last_ms += 1
                self._counter = 0
            timestamp_ms = self._last_ms
            counter = self._counter

        value = (timestamp_ms & _UNIX_TS_MS_MASK) << _UNIX_TS_MS_SHIFT
        value |= _VERSION << _VERSION_SHIFT
        value |= counter << _COUNTER_SHIFT
        value |= _VARIANT << _VARIANT_SHIFT
        value |= secrets.randbits(62)
        return uuid.UUID(int=value)


_generator = _Uuid7Generator()


def uuid7() -> uuid.UUID:
    """Return a new time-ordered UUID version 7."""
    return _generator.generate()


def uuid7_timestamp(value: uuid.UUID) -> datetime:
    """Return the UTC instant encoded in a UUIDv7's timestamp field.

    Raises:
        ValueError: if the UUID is not version 7.
    """
    if value.version != _VERSION:
        raise ValueError(f"expected a version 7 UUID, got version {value.version}")
    timestamp_ms = (value.int >> _UNIX_TS_MS_SHIFT) & _UNIX_TS_MS_MASK
    return datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC)
