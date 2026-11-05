"""Bounded current-job snapshots. Reconnecting never starts provider work."""
from dataclasses import dataclass, field
import json

from backend.core.response_stream import Cancellation


@dataclass
class JobDelivery:
    revision: int = 0
    evidence_revision: int = 0
    answer: str = ""
    status: str = "success"
    answer_done: bool = False
    notice: str = ""
    evidence: dict = field(default_factory=dict)
    cancelled: Cancellation = field(default_factory=Cancellation)
    subscribers: int = 0

    def update(self, kind, values):
        if kind in {"text", "answer_done"}:
            self.answer = values["answer"]
        if kind == "answer_done":
            self.answer_done = True
            self.status = values["status"]
        if kind == "reset":
            self.answer = ""
            self.notice = values["notice"]
        if kind == "evidence":
            self.evidence = values
            self.evidence_revision += 1
        self.revision += 1

    def snapshot(self, job, include_evidence):
        result = {"id": job["id"], "version": self.revision, "job": dict(job),
                  "answer": self.answer, "status": self.status,
                  "answer_done": self.answer_done, "notice": self.notice}
        if include_evidence:
            result["evidence"] = self.evidence
        return result


def frame(event, data):
    return "event: " + event + "\ndata: " + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n\n"
