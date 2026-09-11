# W0: webhook receiver hardening — live status + honest errors (v0.6.4)

* status: SEALED design record — written 2026-09-11, BEFORE implementation
* version: 0.6.4 · hardens the W0 webhook adapter's sealed path
  (docs/w0-rfq-ingestion.md §3, sealed 0.6.0) · same discipline: no new data
  semantics, no research number, nothing here touches the journal's
  immutability contract.
* what it is NOT: not a new adapter, not a rate-limit policy (the receiver
  binds 127.0.0.1 by default, token-gated when exposed — the sealed posture),
  not a change to R-1..R-13 validation or the fail-closed append.

## 1. The two real gaps (found by reading the shipped code)

1. **Status staleness on the always-on path.** The file-ingest CLI and the
   replay CLI both refresh `research/artifacts/rfq-status.json` — the derived
   artifact the tower reads. The webhook receiver — the component designed to
   run continuously when a push provider exists — appends to the journal but
   never refreshes the status. Consequence: while the most likely real-feed
   lane is actively ingesting, the command center shows a stale chain head,
   line count and census until someone manually runs a replay. The receiver
   is the only W0 path that leaves its own monitor blind.
2. **No honest 500 surface.** The handler catches `RFQSchemaError` (422,
   nothing journaled) and nothing else. An I/O failure, a permission error,
   or an `RFQJournalError` from a corrupted journal escapes as a per-thread
   traceback and a connection reset: the caller gets no response at all.
   Fail-closed is preserved (nothing was journaled) but it is not
   fail-LOUD — the caller cannot distinguish "rejected" from "broken".

A third, subtler detail discovered while designing the fix: `write_status`
writes the artifact with a plain `open(w)` (not atomic), and the receiver is
a thread-per-request server — concurrent refreshes could interleave and
corrupt the artifact. The fix must serialize.

## 2. Sealed rules H-1…H-5

- **H-1 status refresh on append (the fix).** `WebhookReceiver` gains an
  injectable `on_append` hook, called after every successful journal append
  with the written line. The CLI wires it to `write_status` **by default**
  (`--no-status-refresh` disables it for pathological volumes). Honest cost
  note: a refresh is a full chain walk, O(journal lines) per accepted record
  — milliseconds at desk-paper volumes, quadratic only under bursts, which
  is exactly what the escape flag is for. The CLI-wired refresher holds a
  lock so concurrent request threads serialize their refreshes (the plain
  `open(w)` artifact write is not atomic); the module-level hook stays
  generic and knows nothing about status semantics.
- **H-2 response honesty (derived ≠ ingestion).** A 200 reflects the journal
  append ONLY. If the derived status refresh fails after a successful
  append, the response stays `ok=true` with `"status_refresh": "stale"` and
  the failure is logged loudly to stderr — because the record IS journaled
  and the journal is the source of truth; a derived-artifact failure must
  never masquerade as an ingestion failure. With a successful refresh the
  response carries `"status_refresh": "ok"`. With no hook wired, the key is
  absent (the bare module behavior is unchanged for library users).
- **H-3 the 500 surface.** Any non-schema exception during
  normalize/append → `500 {"ok": false, "error": "<class>: <msg>"}` — the
  exception class name travels, the traceback does not. Nothing is journaled
  on that path (append raising = no write — fail-closed preserved, now also
  fail-loud).
- **H-4 unchanged surfaces.** Token gate (constant-time), 1 MB body cap,
  path allowlist, 422-on-schema-violation, 422-on-duplicate (R-1), and the
  journal immutability contract are exactly as sealed in v0.6.0.
- **H-5 additive wiring only.** `on_append=None` default; the receiver
  module's behavior with no hook is byte-for-byte the v0.6.3 behavior. The
  CLI additionally gains `--status PATH` (default the standard artifact)
  mirroring `--journal` — the same additive-CLI-flag precedent as
  `--keep-going`/`--dry-run`/`--smoke-journal`. `journal.py` and
  `ingest.py`'s `write_status` are NOT modified.

## 3. Sealed decisions

1. Refresh-on-every-append by default, escape flag for bursts (H-1) — the
   tower's liveness is worth an O(n) walk per accepted record at honest
   volumes; the flag documents exactly when that stops being true.
2. Response honesty semantics (H-2): derived-artifact failures never
   overwrite the truth about the journal. A "stale" marker + loud stderr log
   beats a lying 500.
3. The 500 surface (H-3) reports the exception class, never a traceback —
   honest to the caller, closed to the attacker.
4. No rate limiting in this record: the receiver's sealed posture is
   localhost-bind + token; a flood policy would be security theater for that
   posture and would belong to its own record if the posture ever changes.
5. The status artifact remains last-operation-wins over whichever journal
   the operator points at (`journal_path` recorded inside the artifact) —
   the existing convention, now honored by all three ingestion paths.
