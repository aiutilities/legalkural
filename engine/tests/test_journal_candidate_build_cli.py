"""Tests for finalized-candidate journal build CLI."""

from pathlib import Path

import pytest

from journal import cli


def test_parser_exposes_candidate_build_command():
    args = cli.build_parser().parse_args(
        [
            "candidate-build",
            "--storage-root",
            "candidates",
            "--output-root",
            "editions",
            "--candidate-id",
            "LK-CANDIDATE-001",
        ]
    )

    assert args.command == "candidate-build"
    assert args.project_root == Path(".")
    assert args.storage_root == Path("candidates")
    assert args.output_root == Path("editions")
    assert args.candidate_id == "LK-CANDIDATE-001"


def test_candidate_build_dispatches_exact_arguments(monkeypatch, capsys):
    captured = {}

    def fake_build(**kwargs):
        captured.update(kwargs)
        return {
            "status": "COMPLETE",
            "candidate_id": kwargs["candidate_id"],
        }

    monkeypatch.setattr(
        cli,
        "build_finalized_candidate_journal",
        fake_build,
    )

    result = cli.main(
        [
            "candidate-build",
            "--project-root",
            "/project",
            "--storage-root",
            "/candidates",
            "--output-root",
            "/editions",
            "--candidate-id",
            "LK-CANDIDATE-001",
        ]
    )

    assert result == 0
    assert captured == {
        "project_root": Path("/project"),
        "candidate_storage_root": Path("/candidates"),
        "output_root": Path("/editions"),
        "candidate_id": "LK-CANDIDATE-001",
    }

    output = capsys.readouterr().out
    assert '"status": "COMPLETE"' in output
    assert '"candidate_id": "LK-CANDIDATE-001"' in output


@pytest.mark.parametrize(
    "missing_option",
    [
        "--storage-root",
        "--output-root",
        "--candidate-id",
    ],
)
def test_candidate_build_requires_explicit_inputs(missing_option):
    arguments = [
        "candidate-build",
        "--storage-root",
        "candidates",
        "--output-root",
        "editions",
        "--candidate-id",
        "LK-CANDIDATE-001",
    ]

    option_index = arguments.index(missing_option)
    del arguments[option_index : option_index + 2]

    with pytest.raises(SystemExit) as raised:
        cli.build_parser().parse_args(arguments)

    assert raised.value.code == 2
