"""examples.calc_agent_v2 — calc_agent with a regression injected.

This is the **deliberately broken** version used to demonstrate Volo catching real
regressions:

* v1 (``examples.calc_agent``) returns ``((a+b)*c)``.
* v2 returns ``(a+b)*c + 1`` — off-by-one.

The diff view should pinpoint the divergence at the multiply step; the reliability report
should regress decision_determinism and faithfulness. This is what users will see in the
landing demo.
"""

from examples.calc_agent_v2.agent import run

__all__ = ["run"]
