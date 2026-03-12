from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Decision(str, Enum):
    APPROVE = "approve"
    DENY = "deny"


class ApprovalKind(str, Enum):
    COMMAND_EXECUTION = "command_execution"
    FILE_CHANGE = "file_change"


class BrokerDecision(str, Enum):
    ACCEPT = "accept"
    ACCEPT_FOR_SESSION = "acceptForSession"
    DECLINE = "decline"
    CANCEL = "cancel"


@dataclass(frozen=True)
class ApprovalEvent:
    action_id: str
    context: str
    risk_level: RiskLevel
    timestamp: str

    @classmethod
    def now(cls, action_id: str, context: str, risk_level: RiskLevel) -> "ApprovalEvent":
        return cls(
            action_id=action_id,
            context=context,
            risk_level=risk_level,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def to_dict(self) -> Dict[str, str]:
        payload = asdict(self)
        payload["risk_level"] = self.risk_level.value
        return payload


@dataclass(frozen=True)
class ActuationRequest:
    action_id: str
    decision: Decision

    def to_dict(self) -> Dict[str, str]:
        payload = asdict(self)
        payload["decision"] = self.decision.value
        return payload


@dataclass(frozen=True)
class BrokerApprovalRequest:
    request_id: str
    thread_id: str
    turn_id: str
    item_id: str
    kind: ApprovalKind
    summary: str
    available_decisions: List[BrokerDecision]
    timestamp: str
    wire_request_id: str | int = field(repr=False, compare=False)
    approval_id: str | None = field(default=None, repr=False, compare=False)
    method: str = field(default="", repr=False, compare=False)

    def to_dict(self) -> Dict[str, object]:
        return {
            "request_id": self.request_id,
            "thread_id": self.thread_id,
            "turn_id": self.turn_id,
            "item_id": self.item_id,
            "kind": self.kind.value,
            "summary": self.summary,
            "available_decisions": [decision.value for decision in self.available_decisions],
            "timestamp": self.timestamp,
        }


@dataclass(frozen=True)
class BrokerApprovalResponse:
    request_id: str
    decision: BrokerDecision

    def to_dict(self) -> Dict[str, str]:
        payload = asdict(self)
        payload["decision"] = self.decision.value
        return payload


@dataclass
class PendingApproval:
    request: BrokerApprovalRequest
    item_snapshot: Dict[str, object] | None = None
    opened_at: str | None = None
    responded_at: str | None = None
    resolved_at: str | None = None


@dataclass(frozen=True)
class DiscoveryFinding:
    name: str
    path: Path
    exists: bool
    detail: str = ""
    confidence: str = "low"

    def to_dict(self) -> Dict[str, str]:
        return {
            "name": self.name,
            "path": str(self.path),
            "exists": self.exists,
            "detail": self.detail,
            "confidence": self.confidence,
        }


@dataclass
class DiscoveryReport:
    generated_at: str
    findings: List[DiscoveryFinding] = field(default_factory=list)
    selector_hints: List[str] = field(default_factory=list)
    http_hints: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    metadata: Dict[str, Optional[str]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, object]:
        return {
            "generated_at": self.generated_at,
            "findings": [finding.to_dict() for finding in self.findings],
            "selector_hints": self.selector_hints,
            "http_hints": self.http_hints,
            "notes": self.notes,
            "metadata": self.metadata,
        }
