"""W0: webhook receiver — run when a push provider exists (REAL source).

  python3 scripts/rfq_webhook_recv.py --port 3901 [--token SHARED_SECRET] \
      [--field-map quant_arb/rfq/providers/example_field_map.json]

POST /rfq with a provider payload → FieldMap normalize → schema validate →
immutable journal append. Binds 127.0.0.1 by default; use --token whenever
the listener is exposed beyond localhost. See webhook.py for details.
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from quant_arb.rfq.ingest import DEFAULT_JOURNAL, load_field_map
from quant_arb.rfq.journal import RawRFQJournal
from quant_arb.rfq.providers.webhook import WebhookReceiver

EXAMPLE_MAP = os.path.join("quant_arb", "rfq", "providers", "example_field_map.json")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--journal", default=DEFAULT_JOURNAL)
    ap.add_argument("--field-map", default=None,
                    help=f"JSON field map (example: {EXAMPLE_MAP})")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=3901)
    ap.add_argument("--token", default=None, help="shared secret (X-RFQ-Token header)")
    args = ap.parse_args()

    field_map = load_field_map(args.field_map)
    journal = RawRFQJournal(args.journal)
    receiver = WebhookReceiver(journal, field_map, token=args.token)
    receiver.serve(host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
