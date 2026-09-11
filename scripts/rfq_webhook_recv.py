"""W0: webhook receiver — run when a push provider exists (REAL source).

  python3 scripts/rfq_webhook_recv.py --port 3901 [--token SHARED_SECRET] \
      [--field-map quant_arb/rfq/providers/example_field_map.json]

POST /rfq with a provider payload → FieldMap normalize → schema validate →
immutable journal append. Binds 127.0.0.1 by default; use --token whenever
the listener is exposed beyond localhost. See webhook.py for details.

v0.6.4 (sealed docs/w0-webhook-hardening.md): every ACCEPTED record also
refreshes the derived status artifact (rfq-status.json — the tower reads it
read-only), so the command center stays live while the always-on path
ingests. Honest cost: a refresh is a full chain walk, O(journal lines) per
accepted record — milliseconds at desk volumes; --no-status-refresh disables
it for pathological bursts. A refresh failure never masquerades as an
ingestion failure: the response says status_refresh="stale", the journal is
the source of truth.
"""

from __future__ import annotations

import argparse
import os
import sys
import threading

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from quant_arb.rfq.ingest import (DEFAULT_JOURNAL, DEFAULT_STATUS,
                                  load_field_map, write_status)
from quant_arb.rfq.journal import RawRFQJournal
from quant_arb.rfq.providers.webhook import WebhookReceiver

EXAMPLE_MAP = os.path.join("quant_arb", "rfq", "providers",
                           "example_field_map.json")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--journal", default=DEFAULT_JOURNAL)
    ap.add_argument("--status", default=DEFAULT_STATUS,
                    help="derived status artifact path (refreshed per append)")
    ap.add_argument("--no-status-refresh", action="store_true",
                    help="disable the per-append status refresh (pathological "
                         "volume bursts; the tower will show stale status)")
    ap.add_argument("--field-map", default=None,
                    help=f"JSON field map (example: {EXAMPLE_MAP})")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=3901)
    ap.add_argument("--token", default=None, help="shared secret (X-RFQ-Token header)")
    args = ap.parse_args()

    field_map = load_field_map(args.field_map)
    journal = RawRFQJournal(args.journal)

    on_append = None
    if not args.no_status_refresh:
        _refresh_lock = threading.Lock()   # H-1: serialize thread-per-request

        def on_append(line: dict) -> None:
            with _refresh_lock:
                write_status(journal, args.status,
                             extra={"op": "webhook-append", "seq": line["seq"]})

    receiver = WebhookReceiver(journal, field_map, token=args.token,
                               on_append=on_append)
    mode = ("status-refresh per append" if on_append is not None
            else "NO status refresh (--no-status-refresh)")
    print(f"[rfq-webhook] journal: {journal.path}", flush=True)
    print(f"[rfq-webhook] status: {args.status} ({mode})", flush=True)
    receiver.serve(host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
