"""Volo FastAPI service — read-only over local recordings + reports.

Routes:
* ``GET  /healthz``
* ``GET  /recordings``                  list run_ids + brief metadata
* ``GET  /recordings/{run_id}``         full Recording JSON
* ``GET  /reports``                     list ReliabilityReports
* ``GET  /reports/{run_id}``            single report
* ``POST /diff``                        body: ``{baseline_id, candidate_id}`` → Diff JSON

The service reads from ``VOLO_DATA_DIR`` (default ``./.volo``). No writes; ``volo
record/run/ci`` are the writers.
"""

from volo_api.main import app, create_app

__all__ = ["app", "create_app"]
