"""volo-langgraph — wrap a LangGraph runtime and import its OTel traces.

Two public surfaces:

* ``wrap(graph, *, model=None, tools=None)`` — install Volo proxies into the LangGraph
  runtime so a wrapping ``Recorder`` auto-captures every node call. Returns the same graph
  for chaining (LangGraph builders are mutable).
* ``import_langgraph_otel(path)`` — read a LangGraph-emitted OTel JSONL trace file and
  return a Volo ``Recording``. Delegates to ``volo_sdk.import_otel_trace`` with the
  ``framework='langgraph'`` profile.

LangGraph runtime objects are duck-typed — we only require ``.compile()``-style graph that
exposes ``.nodes`` (a mapping of node name → callable). When the real LangGraph package is
installed at runtime, the wrap helper inspects ``langchain_core.runnables`` extension points;
otherwise it falls back to its in-house adapter (sufficient for the bundled example agent and
for tests).
"""

from volo_langgraph.adapter import wrap
from volo_langgraph.otel import import_langgraph_otel

__all__ = ["import_langgraph_otel", "wrap"]
