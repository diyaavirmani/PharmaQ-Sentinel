from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_hexdigest(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()
