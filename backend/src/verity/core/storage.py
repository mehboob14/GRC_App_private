"""Object storage behind one small seam.

Evidence files arrive from a browser, so everything a client says about them is a
claim, not a fact: the declared content type, the declared size, the filename. All
three are checked here, above the driver, so no driver can be the place the check
was forgotten — the hash is computed over the bytes *we* received, the cap is
enforced while reading, the type is sniffed from the leading bytes rather than taken
from the header or the extension, and the filename is never allowed to be a path.

Every entry point is tenant-scoped: ``put`` writes under the tenant's prefix and
``open``/``signed_url`` refuse a key that does not resolve inside it, so one tenant
cannot address another's object even holding its key. A key from the wrong tenant is
``NotFound``, not ``PermissionDenied`` — a 403 would confirm the object exists.

The driver itself is a deployment choice (``STORAGE_DRIVER``). ``LocalObjectStore``
is the development and test one; the production driver is a class, not a rewrite.
"""

from __future__ import annotations

import codecs
import hashlib
import io
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path, PurePosixPath
from typing import Final, Protocol
from uuid import UUID

from verity.core.config import StorageSettings, get_settings
from verity.core.errors import InvalidInput, NotFound
from verity.core.logging import get_logger
from verity.shared.ids import uuid7

logger = get_logger(__name__)

# Distinct codes on one error type: core/errors.py lets an instance override `code`,
# so the client can tell "too big" from "wrong kind" without a new exception class.
FILE_TOO_LARGE_CODE: Final = "file_too_large"
UNSUPPORTED_FILE_TYPE_CODE: Final = "unsupported_file_type"

_CHUNK_BYTES: Final = 64 * 1024
_MAX_FILENAME_CHARS: Final = 100
_UNSAFE_FILENAME_CHARS: Final = re.compile(r"[^A-Za-z0-9._-]+")

# A head that opens a markup tag is not plain text. Without this the text branch below
# would make the allow-list meaningless: any NUL-free UTF-8 head would pass as
# text/plain, including HTML, SVG and XML — exactly the shapes that render or execute
# when a browser is handed the file back. Matches `<x`, `</x`, `<!x`, `<?x`.
_MARKUP_OPENING: Final = re.compile(rb"<[!?/]?[A-Za-z]")

# The allow-list, expressed as the only things the sniffer can return. Anything that
# does not match one of these is refused, which is the right default for a store whose
# contents are later handed back to auditors.
_SIGNATURES: Final[tuple[tuple[bytes, str], ...]] = (
    (b"%PDF-", "application/pdf"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
)
_OOXML_MARKERS: Final[tuple[tuple[bytes, str], ...]] = (
    (b"word/", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
    (b"xl/", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
    (b"ppt/", "application/vnd.openxmlformats-officedocument.presentationml.presentation"),
)
# WebP is a RIFF container — "RIFF", a 4-byte size, then "WEBP". The form tag sits at
# offset 8, past where a prefix match reaches, so it is sniffed separately below rather
# than added to _SIGNATURES. A static raster like PNG/JPEG: no script surface.
WEBP_CONTENT_TYPE: Final = "image/webp"
ALLOWED_CONTENT_TYPES: Final[frozenset[str]] = frozenset(
    [value for _, value in (*_SIGNATURES, *_OOXML_MARKERS)]
    + ["text/plain", "application/json", WEBP_CONTENT_TYPE]
)


@dataclass(frozen=True, slots=True)
class StoredObject:
    """What was stored, as the store saw it — never as the client described it."""

    key: str
    """Tenant-scoped storage key. The only handle; nothing else addresses an object."""

    sha256: str
    """Hex digest computed here over the received bytes."""

    size_bytes: int
    content_type: str
    """Sniffed from the magic bytes. Not the submitted header, not the extension."""

    original_filename: str
    """The client's filename, sanitised. Kept for display; never used as a path."""


class ObjectStore(Protocol):
    def put(self, tenant_id: UUID, filename: str, data: bytes | io.BufferedIOBase) -> StoredObject:
        """Store ``data``. A *buffered* stream, never a raw one — see ``_buffered``."""
        ...

    def open(self, tenant_id: UUID, ref: str) -> bytes:
        """The object's bytes, or ``NotFound`` if ``ref`` is not this tenant's."""
        ...

    def signed_url(self, tenant_id: UUID, ref: str, ttl_seconds: int | None = None) -> str:
        """A URL for the object, or ``NotFound`` if ``ref`` is not this tenant's."""
        ...


def sanitise_filename(filename: str) -> str:
    """Reduce a client filename to a display name that cannot be a path.

    Directory parts are dropped rather than escaped, so "../../etc/passwd" and
    "C:\\Windows\\system32\\x" both become their last segment; leading dots go, so
    ".." cannot survive as a name and nothing is stored hidden.
    """
    name = PurePosixPath(filename.replace("\\", "/")).name
    name = _UNSAFE_FILENAME_CHARS.sub("_", name).lstrip(".")
    return name[:_MAX_FILENAME_CHARS] or "unnamed"


def _decode_utf8_prefix(head: bytes) -> str | None:
    """``head`` as text, or None if it is not UTF-8 text.

    An incremental decoder holds back a multi-byte character split by the chunk
    boundary, so a truncated read does not look like binary.
    """
    if b"\x00" in head:
        return None
    try:
        return codecs.getincrementaldecoder("utf-8")().decode(head, final=False)
    except UnicodeDecodeError:
        return None


def sniff_content_type(head: bytes) -> str:
    """The content type of the leading bytes, or raise if it is not on the allow-list.

    Text is the loose end of any magic-byte allow-list, so it is bounded here rather
    than left as "whatever decodes": a head whose first non-space character is ``{`` or
    ``[`` is json, any other NUL-free UTF-8 head that does not open a markup tag is
    text/plain, and everything else — including html, svg and xml — is refused.
    """
    if not head:
        # A zero-byte upload otherwise decodes as text/plain and is recorded as
        # satisfied evidence carrying the well-known empty-string digest.
        raise InvalidInput(
            "That file is empty.",
            code=UNSUPPORTED_FILE_TYPE_CODE,
            detail="the upload contained no bytes",
        )
    for signature, content_type in _SIGNATURES:
        if head.startswith(signature):
            return content_type
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return WEBP_CONTENT_TYPE
    if head.startswith(b"PK\x03\x04"):
        # ponytail: OOXML is a zip, and the entry naming it lives past the head. Local
        # file headers store names uncompressed, so Word and Excel output carry "word/"
        # or "xl/" within the first few KB. A zip that carries neither is refused. If a
        # real file is ever misjudged, read the central directory with `zipfile` instead.
        for marker, content_type in _OOXML_MARKERS:
            if marker in head:
                return content_type
    elif (text := _decode_utf8_prefix(head)) is not None:
        # csv and txt are both text/plain: nothing in the bytes distinguishes them,
        # and the extension is a client claim. json is recognised by its opening
        # token only — the head is usually truncated, so it cannot be parsed.
        if text.lstrip()[:1] in {"{", "["}:
            return "application/json"
        # The markup check is only on the text/plain path: json is not rendered by a
        # browser, so an html fragment inside a legitimate json export stays legitimate.
        if not _MARKUP_OPENING.search(head):
            return "text/plain"
    raise InvalidInput(
        "That file type is not accepted.",
        code=UNSUPPORTED_FILE_TYPE_CODE,
        detail=f"magic bytes matched no allowed type: {head[:8]!r}",
    )


def _buffered(data: object) -> io.BufferedIOBase:
    """``data`` as a stream whose ``read(n)`` means "n bytes, or EOF".

    Takes ``object`` so the check survives an untyped caller. Only ``BufferedIOBase``
    carries that guarantee: on a raw or non-blocking stream an empty read means "no
    data yet", not "end of file", and the writer below would store the prefix it
    happened to get and record its digest as the file's. A raw stream is a caller
    bug, so it is a ``TypeError`` — wrap it in ``io.BufferedReader`` at the caller.
    """
    if isinstance(data, bytes):
        return io.BytesIO(data)
    if isinstance(data, io.BufferedIOBase):
        return data
    raise TypeError(f"put needs bytes or a buffered stream, not {type(data).__name__}")


def _stream_to_file(
    path: Path, first: bytes, stream: io.BufferedIOBase, max_bytes: int
) -> tuple[str, int]:
    """Write the stream to ``path``, hashing as it goes and stopping at the cap.

    An empty read ends the loop, which is only sound because ``stream`` is buffered.
    """
    digest = hashlib.sha256()
    size = 0
    chunk = first
    with path.open("wb") as handle:
        while chunk:
            size += len(chunk)
            if size > max_bytes:
                raise InvalidInput(
                    f"That file is larger than the {max_bytes // (1024 * 1024)} MB limit.",
                    code=FILE_TOO_LARGE_CODE,
                    detail=f"upload exceeded {max_bytes} bytes",
                )
            digest.update(chunk)
            handle.write(chunk)
            chunk = stream.read(_CHUNK_BYTES)
    return digest.hexdigest(), size


class LocalObjectStore:
    """Objects on the filesystem, under a per-tenant directory. Development and test."""

    def __init__(self, settings: StorageSettings) -> None:
        self._settings = settings
        self._root = Path(settings.local_root).resolve()

    def _resolve(self, tenant_id: UUID, ref: str) -> Path:
        """The path for a key, proven to be inside *this tenant's* prefix.

        Keys are built here and cannot escape, but ``open`` and ``signed_url`` take one
        back from a caller, and a stored key is only as trustworthy as whatever held it.
        Resolving against the tenant prefix rather than the root covers both escapes at
        once: ``../`` out of the root, and a sibling tenant's key.
        """
        try:
            candidate = (self._root / ref).resolve()
        except (OSError, ValueError) as exc:
            # A NUL byte, an over-long name or a reserved device name makes resolve()
            # raise. Rule 10: that leaves this seam as a typed 404, never as a 500.
            raise NotFound(detail=f"object key is not a usable path: {ref!r}") from exc
        if not candidate.is_relative_to(self._root / str(tenant_id)):
            raise NotFound(detail=f"object key is outside tenant {tenant_id}: {ref!r}")
        return candidate

    def put(self, tenant_id: UUID, filename: str, data: bytes | io.BufferedIOBase) -> StoredObject:
        stream = _buffered(data)
        first = stream.read(_CHUNK_BYTES)
        # Type first: a refused file must never have reached the disk.
        content_type = sniff_content_type(first)
        safe_name = sanitise_filename(filename)
        # The uuid7 prefix makes the key unique per object and the tenant prefix makes
        # it unique across tenants, so two tenants uploading "evidence.pdf" cannot
        # collide and one tenant's key can never name another's object.
        key = f"{tenant_id}/{uuid7()}-{safe_name}"
        path = self._resolve(tenant_id, key)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            sha256, size = _stream_to_file(
                path, first, stream, self._settings.max_upload_mb * 1024 * 1024
            )
        except Exception:
            path.unlink(missing_ok=True)
            raise
        logger.info("storage.put", key=key, size_bytes=size, content_type=content_type)
        return StoredObject(
            key=key,
            sha256=sha256,
            size_bytes=size,
            content_type=content_type,
            original_filename=safe_name,
        )

    def open(self, tenant_id: UUID, ref: str) -> bytes:
        try:
            return self._resolve(tenant_id, ref).read_bytes()
        except OSError as exc:
            raise NotFound(detail=f"object not readable: {ref!r}") from exc

    def signed_url(
        self,
        tenant_id: UUID,
        ref: str,
        ttl_seconds: int | None = None,  # noqa: ARG002
    ) -> str:
        """A ``file://`` URI. A local disk has no signing key and no expiry, so
        ``ttl_seconds`` is accepted for the protocol and ignored; development
        downloads stream through the API using ``open``."""
        return self._resolve(tenant_id, ref).as_uri()


class S3ObjectStore:
    """Not implemented.

    The store is still an open decision — real S3, MinIO in front of it, or Azure
    Blob if the client's tenancy lands there — and it changes the client library and
    the URL signing, not this seam. Credentials for it already exist as
    ``S3Settings``. Implementing this class is the whole of that change.
    """

    def __init__(self, settings: StorageSettings) -> None:
        self._settings = settings

    def put(self, tenant_id: UUID, filename: str, data: bytes | io.BufferedIOBase) -> StoredObject:
        raise NotImplementedError(_PENDING_DRIVER)

    def open(self, tenant_id: UUID, ref: str) -> bytes:
        raise NotImplementedError(_PENDING_DRIVER)

    def signed_url(self, tenant_id: UUID, ref: str, ttl_seconds: int | None = None) -> str:
        raise NotImplementedError(_PENDING_DRIVER)


_PENDING_DRIVER: Final = "the s3 object store driver is not implemented yet"


@lru_cache(maxsize=1)
def get_object_store() -> ObjectStore:
    settings = get_settings().storage
    if settings.driver == "s3":
        return S3ObjectStore(settings)
    return LocalObjectStore(settings)


def reset_object_store_cache() -> None:
    get_object_store.cache_clear()
