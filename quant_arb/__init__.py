"""quant-arb-engine — multi-strategy arbitrage research engine (paper/research only).

Never submits an order. Never holds capital. Never talks to a live venue.
See README.md for the architecture and docs/ for the decision records.
"""

# Keep in sync with pyproject.toml [project].version — the single source of
# truth for the repo version (the tower reads pyproject; artifacts label their
# own module-level engine_version honestly).
__version__ = "0.7.0"
