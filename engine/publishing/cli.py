from __future__ import annotations

import argparse
import json
from pathlib import Path

from .contracts import PublishingContractError, validate_wordpress_post


def main() -> int:
    parser = argparse.ArgumentParser(prog="legalkural-publish-contract")
    parser.add_argument("package", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.package.read_text(encoding="utf-8"))
    try:
        validate_wordpress_post(payload)
    except PublishingContractError as exc:
        print(f"ERROR: {exc}")
        return 1
    print("WORDPRESS PUBLISHING CONTRACT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
