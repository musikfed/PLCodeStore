"""Portable vitrine metadata and publication-safe normalization."""
from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlsplit
from jsonschema import Draft202012Validator

SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "PL Code Store vitrine/meta.json",
    "type": "object",
    "required": ["schema_version", "id", "title", "version", "description", "tags", "visibility", "publication"],
    "properties": {
        "schema_version": {"const": "1.0"},
        "id": {"type": "string", "pattern": "^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$"},
        "title": {"type": "string", "minLength": 1, "maxLength": 180},
        "version": {"type": "string", "minLength": 1, "maxLength": 80},
        "description": {"type": "string", "minLength": 1, "maxLength": 4000},
        "tags": {"type": "array", "items": {"type": "string", "maxLength": 60}, "maxItems": 30},
        "visibility": {"enum": ["public", "private", "internal"]},
        "publication": {"enum": ["disabled", "review_required", "approved"]},
        "repo_url": {"type": ["string", "null"], "maxLength": 500},
        "demo_url": {"type": ["string", "null"], "maxLength": 500},
        "screenshots": {"type": "array", "items": {"type": "string", "maxLength": 500}},
        "status": {"type": "string", "maxLength": 150},
        "updated_at": {"type": "string"},
        "source_evidence": {"type": "object"},
        "public_private_approved": {"type": "boolean"}
    },
    "additionalProperties": True
}
_VALIDATOR = Draft202012Validator(SCHEMA)
PUBLIC_KEYS = ("schema_version", "id", "title", "version", "description", "tags", "visibility", "repo_url", "demo_url", "screenshots", "status")

def validate(meta: dict) -> dict:
    errors = sorted(_VALIDATOR.iter_errors(meta), key=lambda e: list(map(str, e.path)))
    if errors:
        raise ValueError("; ".join(f"{'/'.join(map(str, e.path))}: {e.message}" for e in errors))
    return meta

def content_hash(meta: dict) -> str:
    clean = json.dumps(meta, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(clean.encode("utf-8")).hexdigest()

def safe_url(value: str | None) -> str | None:
    if not value:
        return None
    parsed = urlsplit(value)
    if parsed.scheme not in ("https", "http") or not parsed.hostname or parsed.username or parsed.password:
        return None
    if parsed.hostname in ("localhost", "127.0.0.1", "::1") or parsed.hostname.endswith((".local", ".internal")):
        return None
    return value

def public_snapshot(meta: dict) -> dict:
    validate(meta)
    if meta["publication"] != "approved":
        raise ValueError("Author has not enabled publication")
    if meta["visibility"] == "internal":
        raise ValueError("Internal projects cannot be published")
    if meta["visibility"] == "private" and meta.get("public_private_approved") is not True:
        raise ValueError("Private project needs explicit public-metadata consent")
    pub = {k: meta[k] for k in PUBLIC_KEYS if k in meta}
    for name in ("repo_url", "demo_url"):
        pub[name] = safe_url(pub.get(name))
    if meta["visibility"] == "private":
        pub["repo_url"] = None
    # Only site-owned relative images or public HTTPS images, never file URLs or path traversal.
    pub["screenshots"] = [
        x for x in pub.get("screenshots", [])
        if isinstance(x, str)
        and (x.startswith("https://") or (not x.startswith(("/", "\\")) and ".." not in Path(x).parts and not re.match(r"^[a-z]+:", x, re.I)))
    ]
    return pub
