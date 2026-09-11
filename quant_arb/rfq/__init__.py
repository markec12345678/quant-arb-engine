"""W0 — the real-world data layer: immutable raw RFQ journal, provider
adapters, deterministic ALL-IN EDGE accounting (paper/research only).

Design record: docs/w0-rfq-ingestion.md (sealed before implementation).

NOT a research round: no estimators, no predictions, no GO/NO-GO. The first
real-data research question requires a NEW sealed decision record (W1).
"""

from .schema import ExternalRFQ, RFQSchemaError, EPISTEMIC_NOTE
from .journal import RawRFQJournal, RFQJournalError

__all__ = [
    "ExternalRFQ", "RFQSchemaError", "EPISTEMIC_NOTE",
    "RawRFQJournal", "RFQJournalError",
]
