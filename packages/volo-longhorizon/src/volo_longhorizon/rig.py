"""Long-horizon rig — repeat a task for N episodes, watch reliability decay (newplan M18).

Some agents pass every single-shot test and still rot over a long session: memory bloats,
context drifts, small errors accumulate. That failure class is too expensive to test against a
live model — but in the sim it's a for-loop. ``run_long_horizon`` replays the same task ``N``
times, **threading the agent's memory forward** (each episode sees the prior episodes' outputs),
and measures how the reliability surface moves across episodes.

The agent contract is the ordinary ``agent(payload)`` one; each episode's payload is
``{"episode": i, "memory": [prior outputs], **base_input}``. Agents that ignore memory stay
flat; agents that let it corrupt them degrade — and the rig names the episode where it started.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from volo_core import Recording, canonical_json, current_environment, current_recorder
from volo_reliability import faithfulness, trajectory_shape
from volo_sdk import Recorder, RecorderConfig
from volo_simulator import Tier1Replayer

HorizonVerdict = Literal["stable", "degrades"]

_EPS = 1e-9


class EpisodeResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    episode: int
    faithfulness: float
    shape: str  # canonical trajectory shape, for stability comparison
    output: Any = None
    error: str | None = None


class LongHorizonReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    baseline_run_id: str
    agent_name: str | None = None
    episodes: int
    verdict: HorizonVerdict
    stability: float  # fraction of episodes whose trajectory matches episode 0
    output_consistency: float  # fraction whose output matches episode 0
    faithfulness_start: float
    faithfulness_end: float
    faithfulness_slope: float  # least-squares slope over episodes; < 0 = decay
    first_degraded_episode: int | None = None
    results: list[EpisodeResult] = Field(default_factory=list)

    def to_json(self, *, indent: int = 2) -> str:
        return self.model_dump_json(indent=indent)


def _slope(ys: list[float]) -> float:
    n = len(ys)
    if n < 2:
        return 0.0
    xs = list(range(n))
    mx = sum(xs) / n
    my = sum(ys) / n
    den = sum((x - mx) ** 2 for x in xs)
    if den == 0:
        return 0.0
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True))
    return num / den


def _drive_episode(
    agent: Callable[..., Any], recording: Recording, payload: dict[str, Any]
) -> tuple[Any, str | None]:
    env = Tier1Replayer.from_recording(recording)
    rec = Recorder(config=RecorderConfig(apply_redaction=False))
    with current_recorder(rec), current_environment(env):
        try:
            result = agent(payload)
            rec.set_final_output(result)
            return result, None
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            rec.set_final_output({"__error__": error})
            return {"__error__": error}, error


def run_long_horizon(
    baseline: Recording,
    agent: Callable[..., Any],
    *,
    episodes: int = 10,
    base_input: dict[str, Any] | None = None,
    judge: Any | None = None,
    agent_name: str | None = None,
) -> LongHorizonReport:
    """Replay the task ``episodes`` times with memory threaded forward; measure decay."""
    if episodes < 1:
        raise ValueError("episodes must be >= 1")

    memory: list[Any] = []
    results: list[EpisodeResult] = []
    for i in range(episodes):
        payload = {"episode": i, "memory": list(memory), **(base_input or {})}
        output, error = _drive_episode(agent, baseline, payload)
        # Re-score faithfulness on a recording that carries this episode's output.
        scored = Recording.model_validate(baseline.model_dump(mode="python", by_alias=True))
        scored.final_output = output
        results.append(
            EpisodeResult(
                episode=i,
                faithfulness=faithfulness(scored, judge=judge) if error is None else 0.0,
                shape=canonical_json(list(trajectory_shape(scored))),
                output=output,
                error=error,
            )
        )
        memory.append(output)

    return _compose(baseline, results, agent_name=agent_name)


def _compose(
    baseline: Recording, results: list[EpisodeResult], *, agent_name: str | None
) -> LongHorizonReport:
    n = len(results)
    base_shape = results[0].shape
    base_output = canonical_json(results[0].output)
    faiths = [r.faithfulness for r in results]

    stability = sum(1 for r in results if r.shape == base_shape) / n
    output_consistency = sum(1 for r in results if canonical_json(r.output) == base_output) / n
    slope = _slope(faiths)

    first_degraded: int | None = None
    for r in results:
        if r.error is not None or r.faithfulness < faiths[0] - _EPS:
            first_degraded = r.episode
            break

    degrades = (
        first_degraded is not None
        or stability < 1.0 - _EPS
        or output_consistency < 1.0 - _EPS
        or slope < -_EPS
    )
    return LongHorizonReport(
        baseline_run_id=baseline.run_id,
        agent_name=agent_name or baseline.agent_meta.agent_name,
        episodes=n,
        verdict="degrades" if degrades else "stable",
        stability=stability,
        output_consistency=output_consistency,
        faithfulness_start=faiths[0],
        faithfulness_end=faiths[-1],
        faithfulness_slope=slope,
        first_degraded_episode=first_degraded,
        results=results,
    )
