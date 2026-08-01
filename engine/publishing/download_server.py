from __future__ import annotations

import argparse
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from .document_store import DocumentStore, DocumentStoreError


class DocumentDownloadHandler(BaseHTTPRequestHandler):
    store: DocumentStore

    def do_GET(self) -> None:
        parsed = urlparse(self.path)

        if parsed.path == "/health":
            self._send_text(
                HTTPStatus.OK,
                "LEGAL KURAL DOCUMENT SERVICE READY\n",
            )
            return

        parts = [
            unquote(part)
            for part in parsed.path.split("/")
            if part
        ]

        if len(parts) != 3 or parts[0] != "documents":
            self._send_text(
                HTTPStatus.NOT_FOUND,
                "Not found\n",
            )
            return

        _, document_id, filename = parts

        try:
            document = self.store.resolve(
                document_id,
                filename,
            )
        except DocumentStoreError as exc:
            self._send_text(
                HTTPStatus.NOT_FOUND,
                f"{exc}\n",
            )
            return

        content_type = (
            mimetypes.guess_type(document.filename)[0]
            or "application/pdf"
        )
        size = document.public_path.stat().st_size

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(size))
        self.send_header(
            "Content-Disposition",
            f'attachment; filename="{document.filename}"',
        )
        self.send_header(
            "Cache-Control",
            "public, max-age=3600",
        )
        self.end_headers()

        with document.public_path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                self.wfile.write(chunk)

    def _send_text(
        self,
        status: HTTPStatus,
        body: str,
    ) -> None:
        payload = body.encode("utf-8")
        self.send_response(status)
        self.send_header(
            "Content-Type",
            "text/plain; charset=utf-8",
        )
        self.send_header(
            "Content-Length",
            str(len(payload)),
        )
        self.end_headers()
        self.wfile.write(payload)

    def log_message(
        self,
        format: str,
        *args: object,
    ) -> None:
        return


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="legalkural-document-server",
        description="Serve approved LegalKural source documents.",
    )
    parser.add_argument(
        "--store-root",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8787,
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    store = DocumentStore(args.store_root)

    handler = type(
        "ConfiguredDocumentDownloadHandler",
        (DocumentDownloadHandler,),
        {"store": store},
    )

    server = ThreadingHTTPServer(
        (args.host, args.port),
        handler,
    )

    print("=" * 72)
    print("LEGALKURAL DOCUMENT DOWNLOAD SERVER")
    print("=" * 72)
    print(f"Store : {store.root}")
    print(f"URL   : http://{args.host}:{args.port}")
    print("=" * 72)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
