"""The object-storage seam, against a real filesystem root and real bytes.

No database: the seam is a trust boundary, not a table. What is asserted here is what
the store refuses to believe about a file, that two tenants can never address each
other's objects, and that the cap and the digest hold against a *stream* — a payload
handed over as `bytes` is already whole, so it proves nothing about either.
"""

from __future__ import annotations

import hashlib
import io
import zipfile
from pathlib import Path
from uuid import UUID

import pytest

from verity.core.config import StorageSettings
from verity.core.errors import InvalidInput, NotFound
from verity.core.storage import (
    ALLOWED_CONTENT_TYPES,
    FILE_TOO_LARGE_CODE,
    UNSUPPORTED_FILE_TYPE_CODE,
    LocalObjectStore,
    sniff_content_type,
)

TENANT_A = UUID("0198f0c0-0000-7000-8000-00000000000a")
TENANT_B = UUID("0198f0c0-0000-7000-8000-00000000000b")

PDF = b"%PDF-1.7\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n%%EOF\n"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
WINDOWS_EXECUTABLE = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00"
HTML = b"<!DOCTYPE html><html><body>looks like a report</body></html>"
SVG = b'<svg xmlns="http://www.w3.org/2000/svg"><script>steal()</script></svg>'

MEGABYTE = 1024 * 1024
CHUNK = 64 * 1024


def zipped(entry: str) -> bytes:
    """A minimal OOXML-shaped archive — or, with any other entry, a plain zip."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr(entry, "<x/>")
    return buffer.getvalue()


class CountingStream(io.BufferedIOBase):
    """Serves ``total`` bytes without materialising them, counting what it handed over."""

    def __init__(self, first: bytes, total: int) -> None:
        self.served = 0
        self._pending = first
        self._filler = total - len(first)

    def read(self, size: int | None = -1, /) -> bytes:
        assert size is not None, "the store must never read() unbounded"
        assert size > 0, "the store must read in bounded chunks"
        chunk = self._pending[:size]
        self._pending = self._pending[len(chunk) :]
        if not chunk and self._filler > 0:
            chunk = b"a" * min(size, self._filler)
            self._filler -= len(chunk)
        self.served += len(chunk)
        return chunk


class StingyStream(io.BufferedIOBase):
    """Buffered and honest, but hands back far less than asked for on every read."""

    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def read(self, size: int | None = -1, /) -> bytes:
        take = 7 if size is None or size < 0 else min(7, size)
        chunk, self._payload = self._payload[:take], self._payload[take:]
        return chunk


class RawTricklingStream(io.RawIOBase):
    """Unbuffered: an empty read means "nothing ready yet", not "end of file".

    This is the shape that truncated a 109-byte payload to its first 16 bytes and
    recorded the digest of the truncation as the file's own.
    """

    def __init__(self, payload: bytes) -> None:
        self._chunks = [payload[:16], b"", payload[16:], b""]

    def read(self, size: int = -1, /) -> bytes:
        return self._chunks.pop(0) if self._chunks else b""


@pytest.fixture
def store(tmp_path: Path) -> LocalObjectStore:
    return LocalObjectStore(StorageSettings(local_root=tmp_path, max_upload_mb=1))


def files_under(root: Path) -> list[Path]:
    return [path for path in root.rglob("*") if path.is_file()]


def test_put_then_open_returns_the_same_bytes(store: LocalObjectStore) -> None:
    stored = store.put(TENANT_A, "evidence.pdf", PDF)
    assert store.open(TENANT_A, stored.key) == PDF
    assert stored.size_bytes == len(PDF)
    assert stored.content_type == "application/pdf"


def test_digest_is_computed_over_the_received_bytes(store: LocalObjectStore) -> None:
    """The client never supplies this, so the test computes it independently."""
    stored = store.put(TENANT_A, "screenshot.png", PNG)
    assert stored.sha256 == hashlib.sha256(PNG).hexdigest()


def test_a_partial_read_is_not_mistaken_for_the_end_of_the_file(
    store: LocalObjectStore,
) -> None:
    """A buffered stream may still return less than asked; that is not EOF."""
    payload = PDF + b"a" * 300
    stored = store.put(TENANT_A, "evidence.pdf", StingyStream(payload))

    assert stored.size_bytes == len(payload)
    assert stored.sha256 == hashlib.sha256(payload).hexdigest()
    assert store.open(TENANT_A, stored.key) == payload


def test_an_unbuffered_stream_is_refused_rather_than_silently_truncated(
    store: LocalObjectStore, tmp_path: Path
) -> None:
    """Only a buffered stream promises read(n) is "n bytes or EOF".

    A raw stream's empty read means "not yet". Accepting one is how a 109-byte payload
    became a 16-byte object whose recorded digest matched the truncation — so it is
    refused outright rather than guessed at.
    """
    payload = PDF + b"a" * 48

    with pytest.raises(TypeError):
        store.put(TENANT_A, "evidence.pdf", RawTricklingStream(payload))

    assert files_under(tmp_path) == []


def test_a_file_over_the_cap_is_refused_before_it_has_all_been_read(
    store: LocalObjectStore, tmp_path: Path
) -> None:
    """The cap must bound the read, not just the result.

    Handed `bytes`, a naive fully-buffering implementation passes this identically, so
    the payload is a stream that reports 64 MB against a 1 MB cap and counts what it
    actually served.
    """
    stream = CountingStream(PDF, 64 * MEGABYTE)

    with pytest.raises(InvalidInput) as raised:
        store.put(TENANT_A, "huge.pdf", stream)

    assert raised.value.code == FILE_TOO_LARGE_CODE
    # the cap plus at most the one chunk that tripped it — nowhere near the whole 64 MB
    assert stream.served <= MEGABYTE + CHUNK
    assert files_under(tmp_path) == []


def test_an_empty_upload_is_refused(store: LocalObjectStore, tmp_path: Path) -> None:
    """Zero bytes is not evidence.

    It used to sniff as text/plain and be recorded as satisfied, carrying the
    well-known digest of the empty string.
    """
    with pytest.raises(InvalidInput) as raised:
        store.put(TENANT_A, "evidence.txt", b"")

    assert raised.value.code == UNSUPPORTED_FILE_TYPE_CODE
    assert files_under(tmp_path) == []


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param(WINDOWS_EXECUTABLE, id="executable"),
        pytest.param(zipped("payload.exe"), id="plain zip, not ooxml"),
        pytest.param(HTML, id="html"),
        pytest.param(SVG, id="svg"),
        pytest.param(b'<?xml version="1.0"?><report/>', id="xml"),
    ],
)
def test_a_disallowed_type_is_refused_however_it_is_named(
    store: LocalObjectStore, payload: bytes
) -> None:
    """The name says pdf, the bytes say otherwise. The bytes decide.

    html, svg and xml are all valid UTF-8, so a text fallback that only checks decoding
    would wave them through as text/plain — an allow-list that admits markup is not one.
    """
    with pytest.raises(InvalidInput) as raised:
        store.put(TENANT_A, "totally-a-report.pdf", payload)
    assert raised.value.code == UNSUPPORTED_FILE_TYPE_CODE


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        pytest.param(PDF, "application/pdf", id="pdf"),
        pytest.param(PNG, "image/png", id="png"),
        pytest.param(
            zipped("word/document.xml"),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            id="docx",
        ),
        pytest.param(
            zipped("xl/workbook.xml"),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            id="xlsx",
        ),
        pytest.param(
            zipped("ppt/presentation.xml"),
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            id="pptx",
        ),
        pytest.param(b"RIFF\x2c\x00\x00\x00WEBP" + b"\x00" * 16, "image/webp", id="webp"),
        pytest.param(b"control,owner\nCC6.1,alice\n", "text/plain", id="csv"),
        pytest.param(b'{"finding": "closed"}', "application/json", id="json"),
        pytest.param(b'{"note": "<b>see attached</b>"}', "application/json", id="json with markup"),
    ],
)
def test_the_type_is_sniffed_not_declared(payload: bytes, expected: str) -> None:
    assert sniff_content_type(payload) == expected
    assert expected in ALLOWED_CONTENT_TYPES


def test_a_traversal_filename_cannot_escape_the_root(
    store: LocalObjectStore, tmp_path: Path
) -> None:
    stored = store.put(TENANT_A, "../../etc/passwd", PDF)

    assert stored.original_filename == "passwd"
    assert ".." not in stored.key
    assert "/" not in stored.key.removeprefix(f"{TENANT_A}/")
    written = list(tmp_path.rglob("*"))
    assert all(path.is_relative_to(tmp_path) for path in written)
    assert (tmp_path / stored.key).read_bytes() == PDF


def test_two_tenants_storing_the_same_filename_get_different_keys(
    store: LocalObjectStore,
) -> None:
    first = store.put(TENANT_A, "evidence.pdf", PDF)
    second = store.put(TENANT_B, "evidence.pdf", PDF)

    assert first.key != second.key
    assert first.key.startswith(f"{TENANT_A}/")
    assert second.key.startswith(f"{TENANT_B}/")
    assert store.open(TENANT_A, first.key) == PDF


def test_one_tenant_cannot_read_another_tenants_key(store: LocalObjectStore) -> None:
    """Holding the key is not authorisation. 404, never 403 — see core/errors.py."""
    stored = store.put(TENANT_A, "evidence.pdf", PDF)

    with pytest.raises(NotFound):
        store.open(TENANT_B, stored.key)
    with pytest.raises(NotFound):
        store.signed_url(TENANT_B, stored.key)
    # and not by walking out of its own prefix either
    with pytest.raises(NotFound):
        store.open(TENANT_B, f"{TENANT_B}/../{stored.key}")

    assert store.open(TENANT_A, stored.key) == PDF


def test_an_unusable_key_is_a_typed_not_found_not_a_crash(store: LocalObjectStore) -> None:
    """A NUL byte makes Path.resolve() raise ValueError, which is not a VerityError.

    Rule 10: every error crossing this seam is typed, so that reaches a client as a
    404 with a stable code rather than as a 500.
    """
    with pytest.raises(NotFound):
        store.open(TENANT_A, f"{TENANT_A}/eviden\x00ce.pdf")
