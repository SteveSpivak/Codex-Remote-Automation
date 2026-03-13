from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from typing import Any


def random_secret(length: int = 32) -> str:
    return base64.b64encode(secrets.token_bytes(length)).decode("ascii")


def base64_decode(value: str) -> bytes:
    return base64.b64decode(value.encode("ascii"))


def base64_encode(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def _normalize_part(part: str | bytes | int) -> bytes:
    if isinstance(part, bytes):
        return part
    if isinstance(part, int):
        return str(part).encode("utf-8")
    return part.encode("utf-8")


def derive_bytes(secret: str | bytes, *parts: str | bytes | int, length: int = 32) -> bytes:
    key = base64_decode(secret) if isinstance(secret, str) else secret
    output = bytearray()
    counter = 1
    while len(output) < length:
        mac = hmac.new(key, digestmod=hashlib.sha256)
        mac.update(b"cra-bridge-v1|")
        for part in parts:
            normalized = _normalize_part(part)
            mac.update(len(normalized).to_bytes(2, "big"))
            mac.update(normalized)
        mac.update(counter.to_bytes(4, "big"))
        output.extend(mac.digest())
        counter += 1
    return bytes(output[:length])


def derive_secret(secret: str | bytes, *parts: str | bytes | int, length: int = 32) -> str:
    return base64_encode(derive_bytes(secret, *parts, length=length))


def compute_tag(secret: str | bytes, aad: bytes, ciphertext: bytes) -> str:
    key = base64_decode(secret) if isinstance(secret, str) else secret
    mac = hmac.new(key, digestmod=hashlib.sha256)
    mac.update(b"tag|")
    mac.update(aad)
    mac.update(ciphertext)
    return base64_encode(mac.digest())


def verify_tag(secret: str | bytes, aad: bytes, ciphertext: bytes, expected_tag: str) -> bool:
    actual = compute_tag(secret, aad, ciphertext)
    return hmac.compare_digest(actual, expected_tag)


def xor_bytes(left: bytes, right: bytes) -> bytes:
    return bytes(a ^ b for a, b in zip(left, right))


def build_keystream(secret: str | bytes, aad: bytes, size: int) -> bytes:
    output = bytearray()
    counter = 1
    while len(output) < size:
        block = derive_bytes(secret, "stream", aad, counter, length=32)
        output.extend(block)
        counter += 1
    return bytes(output[:size])


def encrypt_text(secret: str | bytes, aad: bytes, plaintext: str) -> tuple[str, str]:
    raw = plaintext.encode("utf-8")
    keystream = build_keystream(secret, aad, len(raw))
    ciphertext = xor_bytes(raw, keystream)
    return base64_encode(ciphertext), compute_tag(secret, aad, ciphertext)


def decrypt_text(secret: str | bytes, aad: bytes, ciphertext_b64: str, tag_b64: str) -> str | None:
    ciphertext = base64_decode(ciphertext_b64)
    if not verify_tag(secret, aad, ciphertext, tag_b64):
        return None
    keystream = build_keystream(secret, aad, len(ciphertext))
    plaintext = xor_bytes(ciphertext, keystream)
    return plaintext.decode("utf-8")


def json_dumps_compact(payload: dict[str, Any]) -> str:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True)
