from datetime import datetime, timedelta

from aidpl.sprint_contract import SprintContract


def test_deadline():
    contract = SprintContract(
        project="LegalKural",
        sprint="51.1-A",
        title="Execution Contract",
        owner="AI CTO",
        estimate_hours=2,
        started_at=datetime(2026, 8, 3, 10, 0),
    )

    assert contract.deadline == datetime(2026, 8, 3, 12, 0)


def test_not_overdue():
    contract = SprintContract(
        project="LegalKural",
        sprint="51.1-A",
        title="Execution Contract",
        owner="AI CTO",
        estimate_hours=2,
        started_at=datetime(2026, 8, 3, 10, 0),
    )

    assert not contract.is_overdue(datetime(2026, 8, 3, 11, 0))


def test_overdue():
    contract = SprintContract(
        project="LegalKural",
        sprint="51.1-A",
        title="Execution Contract",
        owner="AI CTO",
        estimate_hours=2,
        started_at=datetime(2026, 8, 3, 10, 0),
    )

    assert contract.is_overdue(datetime(2026, 8, 3, 12, 1))
