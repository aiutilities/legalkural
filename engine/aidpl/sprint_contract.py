from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum


class SprintStatus(str, Enum):
    COMMITTED = "COMMITTED"
    IN_PROGRESS = "IN_PROGRESS"
    BLOCKED = "BLOCKED"
    MAYDAY = "MAYDAY"
    COMPLETE = "COMPLETE"


@dataclass
class SprintContract:
    project: str
    sprint: str
    title: str
    owner: str
    estimate_hours: int
    started_at: datetime

    @property
    def deadline(self) -> datetime:
        return self.started_at + timedelta(hours=self.estimate_hours)

    def is_overdue(self, now: datetime) -> bool:
        return now > self.deadline
