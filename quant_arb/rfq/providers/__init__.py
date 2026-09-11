"""RFQ provider adapters (W0 §3): file ingest (real), webhook (real),
synthetic (TEST ONLY). normalize-at-the-edge via the declarative FieldMap."""

from .base import FieldMap, RFQProvider, normalize
from .file_ingest import FileRFQProvider
from .synthetic import SyntheticRFQProvider
from .webhook import WebhookReceiver

__all__ = ["FieldMap", "RFQProvider", "normalize",
           "FileRFQProvider", "SyntheticRFQProvider", "WebhookReceiver"]
