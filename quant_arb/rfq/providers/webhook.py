"""Webhook receiver (REAL source) — push providers point here (W0 §3).

A stdlib-only HTTP receiver: POST /rfq with a provider payload → FieldMap
normalize → schema validate → immutable journal append. Designed for
Paradigm-style push integrations and desk webhooks; runnable in one command:

    python3 scripts/rfq_webhook_recv.py --port 3901 \
        --journal research/artifacts/rfq/journal.jsonl \
        --field-map quant_arb/rfq/providers/example_field_map.json

Security posture (honest): bind to 127.0.0.1 by default; a shared-secret
token is supported via --token (checked in constant time) and SHOULD be used
whenever the listener is exposed beyond localhost.
"""

from __future__ import annotations

import hmac
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional

from .base import FieldMap, normalize
from ..journal import RawRFQJournal
from ..schema import RFQSchemaError


class WebhookReceiver:
    def __init__(self, journal: RawRFQJournal, field_map: FieldMap,
                 token: Optional[str] = None) -> None:
        self.journal = journal
        self.field_map = field_map
        self.token = token

    def handler(self) -> type:
        receiver = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:  # noqa: N802 (stdlib naming)
                if self.path.split("?")[0] not in ("/rfq", "/rfq/"):
                    self._reply(404, {"error": "unknown path; POST /rfq"})
                    return
                if receiver.token is not None:
                    supplied = self.headers.get("X-RFQ-Token", "")
                    if not hmac.compare_digest(supplied, receiver.token):
                        self._reply(401, {"error": "bad or missing X-RFQ-Token"})
                        return
                length = int(self.headers.get("Content-Length") or 0)
                if length <= 0 or length > 1_000_000:
                    self._reply(400, {"error": "empty or oversized body"})
                    return
                body = self.rfile.read(length)
                try:
                    payload: Dict[str, Any] = json.loads(body)
                    if not isinstance(payload, dict):
                        raise ValueError("payload must be a JSON object")
                except (json.JSONDecodeError, ValueError) as e:
                    self._reply(400, {"error": f"invalid JSON: {e}"})
                    return
                try:
                    rec = normalize(payload, receiver.field_map, provider_source="real")
                    line = receiver.journal.append(rec)
                    self._reply(200, {"ok": True, "seq": line["seq"],
                                      "rfq_id": rec.rfq_id, "hash": line["hash"]})
                except RFQSchemaError as e:
                    # rejected payloads are NOT journaled (fail-closed); the
                    # caller gets the invariant id in the response
                    self._reply(422, {"ok": False, "error": str(e)})

            def _reply(self, code: int, obj: Dict[str, Any]) -> None:
                data = json.dumps(obj).encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, fmt: str, *args: Any) -> None:  # quiet default logging
                print(f"[rfq-webhook] {self.address_string()} {fmt % args}", flush=True)

        return Handler

    def serve(self, host: str = "127.0.0.1", port: int = 3901) -> None:
        srv = ThreadingHTTPServer((host, port), self.handler())
        print(f"[rfq-webhook] listening on http://{host}:{port}/rfq "
              f"(journal: {self.journal.path})", flush=True)
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            print("[rfq-webhook] stopped", flush=True)
        finally:
            srv.server_close()
