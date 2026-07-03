"""volo-shadow — production shadow: corpus bank, drift sentinel, trends (newplan P2/M13-M14)."""

from volo_shadow.alerts import post_webhook, webhook_payload
from volo_shadow.corpus import CorpusBank, CorpusEntry, content_digest
from volo_shadow.drift import DriftFinding, DriftReport, compare, snapshot
from volo_shadow.history import SnapshotHistory
from volo_shadow.ingest import PullResult, adopt, pull

__all__ = [
    "CorpusBank",
    "CorpusEntry",
    "DriftFinding",
    "DriftReport",
    "PullResult",
    "SnapshotHistory",
    "adopt",
    "compare",
    "content_digest",
    "post_webhook",
    "pull",
    "snapshot",
    "webhook_payload",
]
