#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys


def main() -> int:
    raw = os.getenv("ADMIN_CIDRS_JSON", "").strip()
    if not raw:
        print("ADMIN_CIDRS_JSON is empty (allowed): runner-only CIDR will be used in workflow")
        return 0

    try:
        cidrs = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"ADMIN_CIDRS_JSON is not valid JSON: {exc}")
        return 1

    if not isinstance(cidrs, list):
        print("ADMIN_CIDRS_JSON must be a JSON array")
        return 1

    blocked = {"0.0.0.0/0", "::/0"}
    if any(item in blocked for item in cidrs):
        print("ADMIN_CIDRS_JSON must not contain world-open CIDRs (0.0.0.0/0 or ::/0)")
        return 1

    print("ADMIN_CIDRS_JSON validation passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
