from __future__ import annotations

import argparse
import json
import sys

from .providers import ModelRequest, create_provider


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aidpl-provider",
        description="Inspect and test Legal Kural model providers.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    doctor = sub.add_parser("doctor")
    doctor.add_argument(
        "--providers",
        default="mock,openai,deepseek,qwen",
    )

    smoke = sub.add_parser("smoke")
    smoke.add_argument("--provider", default="mock")

    return parser


def main() -> int:
    args = build_parser().parse_args()

    try:
        if args.command == "doctor":
            results = []

            for name in args.providers.split(","):
                provider = create_provider(name)
                results.append(provider.health())

            print(
                json.dumps(
                    {
                        "status": "COMPLETE",
                        "providers": results,
                    },
                    indent=2,
                )
            )
            return 0

        provider = create_provider(args.provider)
        response = provider.generate(
            ModelRequest(
                agent_id="PROVIDER-SMOKE",
                task="Return provider health confirmation.",
                system_prompt=(
                    "You are a deterministic provider smoke test."
                ),
                user_prompt=(
                    "Return a JSON object with status equal to PASS."
                ),
                response_format="json",
                json_schema={
                    "type": "object",
                    "required": ["status"],
                    "properties": {
                        "status": {
                            "type": "string",
                        }
                    },
                    "additionalProperties": False,
                },
            )
        )

        print(
            json.dumps(
                {
                    "provider": response.provider,
                    "model": response.model,
                    "structured": response.structured,
                    "request_id": response.request_id,
                    "usage": response.usage,
                },
                indent=2,
            )
        )
        return 0

    except (
        ValueError,
        RuntimeError,
        json.JSONDecodeError,
    ) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
