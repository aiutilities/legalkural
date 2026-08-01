from __future__ import annotations

import argparse
import json
from pathlib import Path

from .document_store import DocumentStore, DocumentStoreError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="legalkural-document-store",
        description="Manage LegalKural published source documents.",
    )
    parser.add_argument(
        "--store-root",
        type=Path,
        required=True,
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    register = subparsers.add_parser("register")
    register.add_argument("package_root", type=Path)

    for command in ["approve", "publish", "withdraw"]:
        item = subparsers.add_parser(command)
        item.add_argument("document_id")

    list_parser = subparsers.add_parser("list")
    list_parser.add_argument("--status")

    return parser


def main() -> int:
    args = build_parser().parse_args()
    store = DocumentStore(args.store_root)

    try:
        if args.command == "register":
            result = store.register_package(args.package_root)
        elif args.command == "approve":
            result = store.approve(args.document_id)
        elif args.command == "publish":
            result = store.publish(args.document_id)
        elif args.command == "withdraw":
            result = store.withdraw(args.document_id)
        else:
            result = store.list_documents(args.status)
    except DocumentStoreError as exc:
        print(f"ERROR: {exc}")
        return 1

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
