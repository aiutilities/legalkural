import json

import pytest

import journal.cli as cli


@pytest.mark.parametrize(
    "command",
    (
        "archive-register",
        "archive-list",
        "archive-inspect",
        "archive-verify",
    ),
)
def test_archive_command_help_is_available(command, capsys):
    parser = cli.build_parser()

    with pytest.raises(SystemExit) as exit_info:
        parser.parse_args([command, "--help"])

    assert exit_info.value.code == 0
    assert (
        f"legalkural-journal {command}"
        in capsys.readouterr().out
    )


def test_archive_register_dispatches_explicit_paths(
    tmp_path,
    monkeypatch,
    capsys,
):
    captured = {}

    def fake_register(**arguments):
        captured.update(arguments)
        return {
            "journal_id": "LK-JOURNAL-2026-W34",
            "verification_status": "VERIFIED",
            "archive_verification_status": "VERIFIED",
        }

    monkeypatch.setattr(
        cli,
        "register_verified_edition",
        fake_register,
    )

    archive_root = tmp_path / "archive"
    edition = tmp_path / "edition"
    assert cli.main(
        [
            "archive-register",
            "--archive-root",
            str(archive_root),
            "--edition-directory",
            str(edition),
            "--archived-at-utc",
            "2026-08-18T15:00:00Z",
        ]
    ) == 0

    result = json.loads(capsys.readouterr().out)
    assert result["archive_verification_status"] == "VERIFIED"
    assert captured == {
        "archive_root": archive_root,
        "edition_directory": edition,
        "archived_at_utc": "2026-08-18T15:00:00Z",
    }


def test_archive_list_dispatches(tmp_path, monkeypatch, capsys):
    archive_root = tmp_path / "archive"
    monkeypatch.setattr(
        cli,
        "list_archived_editions",
        lambda supplied: {
            "schema_version": "1.0",
            "archive_root": supplied.as_posix(),
            "edition_count": 0,
            "editions": [],
        },
    )

    assert cli.main(
        [
            "archive-list",
            "--archive-root",
            str(archive_root),
        ]
    ) == 0

    result = json.loads(capsys.readouterr().out)
    assert result["edition_count"] == 0
    assert result["archive_root"] == archive_root.as_posix()


def test_archive_inspect_dispatches_identity(
    tmp_path,
    monkeypatch,
    capsys,
):
    archive_root = tmp_path / "archive"
    captured = {}

    def fake_inspect(root, journal_id):
        captured["root"] = root
        captured["journal_id"] = journal_id
        return {
            "journal_id": journal_id,
            "verification_status": "VERIFIED",
        }

    monkeypatch.setattr(cli, "inspect_archive_entry", fake_inspect)

    assert cli.main(
        [
            "archive-inspect",
            "--archive-root",
            str(archive_root),
            "--journal-id",
            "LK-JOURNAL-2026-W34",
        ]
    ) == 0

    result = json.loads(capsys.readouterr().out)
    assert result["journal_id"] == "LK-JOURNAL-2026-W34"
    assert captured == {
        "root": archive_root,
        "journal_id": "LK-JOURNAL-2026-W34",
    }


def test_archive_verify_dispatches_identity(
    tmp_path,
    monkeypatch,
    capsys,
):
    archive_root = tmp_path / "archive"
    captured = {}

    def fake_verify(root, journal_id):
        captured["root"] = root
        captured["journal_id"] = journal_id
        return {
            "journal_id": journal_id,
            "archive_verification_status": "VERIFIED",
        }

    monkeypatch.setattr(cli, "verify_archived_edition", fake_verify)

    assert cli.main(
        [
            "archive-verify",
            "--archive-root",
            str(archive_root),
            "--journal-id",
            "LK-JOURNAL-2026-W34",
        ]
    ) == 0

    result = json.loads(capsys.readouterr().out)
    assert result["archive_verification_status"] == "VERIFIED"
    assert captured == {
        "root": archive_root,
        "journal_id": "LK-JOURNAL-2026-W34",
    }
