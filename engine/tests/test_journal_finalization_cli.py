import json

import pytest

import journal.cli as cli


def test_candidate_finalize_help_is_available(capsys):
    parser = cli.build_parser()

    with pytest.raises(SystemExit) as exit_info:
        parser.parse_args(["candidate-finalize", "--help"])

    assert exit_info.value.code == 0
    output = capsys.readouterr().out
    assert "legalkural-journal candidate-finalize" in output
    assert "--storage-root" in output
    assert "--candidate-id" in output
    assert "--selected-by" in output
    assert "--finalized-at-utc" in output


def test_candidate_finalize_dispatches_deliberately(
    tmp_path,
    monkeypatch,
    capsys,
):
    captured = {}

    def fake_finalize_candidate(**arguments):
        captured.update(arguments)
        return {
            "candidate_id": arguments["candidate_id"],
            "revision_number": 2,
            "candidate_sha256": "a" * 64,
            "journal_id": "LK-JOURNAL-2026-W34",
            "manifest_sha256": "b" * 64,
            "manifest_file": (
                "LK-CANDIDATE-2026-W34/"
                "finalization/manifest.json"
            ),
            "status": "FINALIZED",
        }

    monkeypatch.setattr(
        cli,
        "finalize_candidate",
        fake_finalize_candidate,
    )

    assert cli.main(
        [
            "candidate-finalize",
            "--storage-root",
            str(tmp_path / "candidates"),
            "--generated-root",
            str(tmp_path / "generated"),
            "--candidate-id",
            "LK-CANDIDATE-2026-W34",
            "--selected-by",
            "Founder",
            "--finalized-at-utc",
            "2026-08-18T13:30:00Z",
        ]
    ) == 0

    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "FINALIZED"
    assert result["revision_number"] == 2
    assert captured == {
        "storage_root": tmp_path / "candidates",
        "generated_root": tmp_path / "generated",
        "candidate_id": "LK-CANDIDATE-2026-W34",
        "selected_by": "Founder",
        "finalized_at_utc": "2026-08-18T13:30:00Z",
    }


def test_candidate_finalize_requires_explicit_approval_fields():
    parser = cli.build_parser()

    with pytest.raises(SystemExit) as exit_info:
        parser.parse_args(
            [
                "candidate-finalize",
                "--storage-root",
                "candidates",
                "--candidate-id",
                "LK-CANDIDATE-2026-W34",
            ]
        )

    assert exit_info.value.code == 2
