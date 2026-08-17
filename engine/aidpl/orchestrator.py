from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .manual_tasks import blocking_tasks_open

AGENT_SEQUENCE = [
    "LK-INTAKE",
    "LK-EXTRACT",
    "LK-LAW",
    "LK-REASON",
    "LK-KURAL",
    "LK-EDITOR",
    "LK-QA",
    "LK-LEARN",
]

DEPENDENCIES = {
    "LK-INTAKE": [],
    "LK-EXTRACT": ["LK-INTAKE"],
    "LK-LAW": ["LK-EXTRACT"],
    "LK-REASON": ["LK-EXTRACT", "LK-LAW"],
    "LK-KURAL": ["LK-REASON"],
    "LK-EDITOR": ["LK-KURAL", "LK-REASON"],
    "LK-QA": ["LK-INTAKE", "LK-EXTRACT", "LK-LAW", "LK-REASON", "LK-KURAL", "LK-EDITOR"],
    "LK-LEARN": ["LK-QA"],
}

OUTPUTS = {
    "LK-INTAKE": ["manifest.json", "evidence/source-integrity.txt"],
    "LK-EXTRACT": [
        "output/01-metadata/metadata.json",
        "output/02-timeline/timeline.json",
        "output/03-facts/facts.json",
        "output/04-issues/issues.json",
        "output/05-evidence/evidence.json",
    ],
    "LK-LAW": ["output/06-law/law.json"],
    "LK-REASON": [
        "output/07-reasoning/reasoning.json",
        "output/08-decision/decision.json",
    ],
    "LK-KURAL": ["output/09-kural/kural.md"],
    "LK-EDITOR": ["output/10-article/article.md"],
    "LK-QA": ["evidence/validation-report.json"],
    "LK-LEARN": ["output/11-learning/thinking-review.md"],
}

VALID_STATUSES = {
    "PENDING",
    "READY",
    "IN_PROGRESS",
    "BLOCKED",
    "COMPLETE",
    "FAILED",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_plan(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Plan does not exist: {path}")

    return json.loads(path.read_text(encoding="utf-8"))


def save_plan(path: Path, plan: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    plan["updated_at_utc"] = utc_now()
    path.write_text(
        json.dumps(plan, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def build_plan(case_id: str, case_root: Path) -> dict[str, Any]:
    agents: list[dict[str, Any]] = []

    for agent_id in AGENT_SEQUENCE:
        dependencies = DEPENDENCIES[agent_id]
        status = "READY" if not dependencies else "PENDING"

        agents.append(
            {
                "agent_id": agent_id,
                "status": status,
                "dependencies": dependencies,
                "outputs": OUTPUTS[agent_id],
                "started_at_utc": None,
                "completed_at_utc": None,
                "reviewed_by": None,
                "verdict": None,
                "notes": [],
            }
        )

    return {
        "schema_version": "1.0",
        "orchestrator": "AI-CEO",
        "product": "Legal Kural",
        "case_id": case_id,
        "case_root": str(case_root),
        "sprint_id": f"{case_id}-AIDPL-001",
        "status": "ACTIVE",
        "created_at_utc": utc_now(),
        "updated_at_utc": utc_now(),
        "publication": {
            "qa_status": "PENDING",
            "founder_authorization": "PENDING",
            "ready": False,
        },
        "agents": agents,
    }


def agent_map(plan: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {agent["agent_id"]: agent for agent in plan["agents"]}


def refresh_readiness(plan: dict[str, Any]) -> None:
    agents = agent_map(plan)

    for agent_id in AGENT_SEQUENCE:
        agent = agents[agent_id]

        if agent["status"] in {"COMPLETE", "FAILED", "IN_PROGRESS"}:
            continue

        deps = agent["dependencies"]

        if any(agents[dep]["status"] == "FAILED" for dep in deps):
            agent["status"] = "BLOCKED"
        elif all(agents[dep]["status"] == "COMPLETE" for dep in deps):
            agent["status"] = "READY"
        else:
            agent["status"] = "PENDING"

    qa = agents["LK-QA"]

    if qa["status"] == "COMPLETE":
        plan["publication"]["qa_status"] = qa.get("verdict") or "PENDING"
    elif qa["status"] == "FAILED":
        plan["publication"]["qa_status"] = "FAIL"
    else:
        plan["publication"]["qa_status"] = "PENDING"
    plan["publication"]["ready"] = (
        plan["publication"]["qa_status"] == "PASS"
        and plan["publication"]["founder_authorization"] == "AUTHORIZED"
        and not manual_gate_open(plan)
    )

    if all(agent["status"] == "COMPLETE" for agent in plan["agents"]):
        plan["status"] = "COMPLETE"
    elif any(agent["status"] == "FAILED" for agent in plan["agents"]):
        plan["status"] = "ATTENTION_REQUIRED"
    else:
        plan["status"] = "ACTIVE"


def find_agent(plan: dict[str, Any], agent_id: str) -> dict[str, Any]:
    agents = agent_map(plan)

    if agent_id not in agents:
        raise ValueError(f"Unknown agent: {agent_id}")

    return agents[agent_id]


def manual_gate_open(plan: dict[str, Any]) -> bool:
    case_root = Path(plan["case_root"]).expanduser().resolve()
    return blocking_tasks_open(case_root)


def assert_manual_execution_allowed(
    plan: dict[str, Any],
) -> None:
    if manual_gate_open(plan):
        raise ValueError(
            "OPEN blocking manual task prevents execution."
        )


def start_agent(plan: dict[str, Any], agent_id: str) -> None:
    refresh_readiness(plan)
    agent = find_agent(plan, agent_id)

    try:
        assert_manual_execution_allowed(plan)
    except ValueError as exc:
        raise ValueError(
            "OPEN blocking manual task prevents agent execution."
        ) from exc

    if agent["status"] != "READY":
        raise ValueError(
            f"Agent {agent_id} is {agent['status']}, not READY."
        )

    agent["status"] = "IN_PROGRESS"
    agent["started_at_utc"] = utc_now()
    agent["notes"].append("Execution started by AI CEO.")


def complete_agent(
    plan: dict[str, Any],
    agent_id: str,
    reviewer: str,
    note: str | None,
    verdict: str | None = None,
) -> None:
    agent = find_agent(plan, agent_id)

    if agent["status"] != "IN_PROGRESS":
        raise ValueError(
            f"Agent {agent_id} is {agent['status']}, not IN_PROGRESS."
        )

    if reviewer == agent_id:
        raise ValueError("An agent cannot review its own output.")

    agent["status"] = "COMPLETE"
    agent["completed_at_utc"] = utc_now()
    agent["reviewed_by"] = reviewer
    agent["verdict"] = verdict

    if note:
        agent["notes"].append(note)

    refresh_readiness(plan)


def fail_agent(plan: dict[str, Any], agent_id: str, note: str) -> None:
    agent = find_agent(plan, agent_id)
    agent["status"] = "FAILED"
    agent["notes"].append(note)
    refresh_readiness(plan)


def authorize_founder(plan: dict[str, Any]) -> None:
    plan["publication"]["founder_authorization"] = "AUTHORIZED"
    refresh_readiness(plan)


def print_status(plan: dict[str, Any]) -> None:
    print("=" * 76)
    print("LEGAL KURAL AIDPL EXECUTION STATUS")
    print("=" * 76)
    print(f"Case      : {plan['case_id']}")
    print(f"Sprint    : {plan['sprint_id']}")
    print(f"Status    : {plan['status']}")
    print()

    for agent in plan["agents"]:
        deps = ", ".join(agent["dependencies"]) or "-"
        print(
            f"{agent['agent_id']:<12} "
            f"{agent['status']:<12} "
            f"Dependencies: {deps}"
        )

    print()
    print(f"QA        : {plan['publication']['qa_status']}")
    print(
        "Founder   : "
        f"{plan['publication']['founder_authorization']}"
    )
    print(f"Publish   : {plan['publication']['ready']}")
    print("=" * 76)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aidpl-orchestrator",
        description="Legal Kural AIDPL orchestration state machine.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    init_parser = sub.add_parser("init")
    init_parser.add_argument("--case-id", required=True)
    init_parser.add_argument("--case-root", type=Path, required=True)
    init_parser.add_argument("--plan", type=Path, required=True)

    status_parser = sub.add_parser("status")
    status_parser.add_argument("--plan", type=Path, required=True)

    start_parser = sub.add_parser("start")
    start_parser.add_argument("--plan", type=Path, required=True)
    start_parser.add_argument("--agent", required=True)

    complete_parser = sub.add_parser("complete")
    complete_parser.add_argument("--plan", type=Path, required=True)
    complete_parser.add_argument("--agent", required=True)
    complete_parser.add_argument("--reviewer", required=True)
    complete_parser.add_argument("--note")
    complete_parser.add_argument("--verdict")

    fail_parser = sub.add_parser("fail")
    fail_parser.add_argument("--plan", type=Path, required=True)
    fail_parser.add_argument("--agent", required=True)
    fail_parser.add_argument("--note", required=True)

    authorize_parser = sub.add_parser("authorize-founder")
    authorize_parser.add_argument("--plan", type=Path, required=True)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        if args.command == "init":
            if args.plan.exists():
                raise FileExistsError(f"Plan already exists: {args.plan}")

            plan = build_plan(
                case_id=args.case_id,
                case_root=args.case_root,
            )
            save_plan(args.plan, plan)
            print_status(plan)
            return 0

        plan = load_plan(args.plan)

        if args.command == "status":
            refresh_readiness(plan)
        elif args.command == "start":
            start_agent(plan, args.agent)
        elif args.command == "complete":
            complete_agent(
                plan,
                args.agent,
                args.reviewer,
                args.note,
                args.verdict,
            )
        elif args.command == "fail":
            fail_agent(plan, args.agent, args.note)
        elif args.command == "authorize-founder":
            authorize_founder(plan)
        else:
            raise ValueError(f"Unsupported command: {args.command}")

        save_plan(args.plan, plan)
        print_status(plan)
        return 0

    except (
        FileExistsError,
        FileNotFoundError,
        json.JSONDecodeError,
        ValueError,
    ) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
