"""volo-runner — the deterministic CI runner core (bible §4 subsystem 5).

Orchestrates: Recording -> Scenarios -> Replayer -> agent -> per-scenario aggregation ->
``ReliabilityReport``. The Typer CLI ``volo run`` is a thin wrapper around ``orchestrate``.
"""

from volo_runner.orchestrator import OrchestratorConfig, orchestrate, resolve_agent

__all__ = ["OrchestratorConfig", "orchestrate", "resolve_agent"]
