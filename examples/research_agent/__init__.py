"""examples.research_agent — a 3-step web-research style agent for stressing Tier-2 fidelity.

Trajectory shape:

    decision   -> "plan_research"
    tool_call  -> "search"     (returns a JSON list of hits)
    tool_call  -> "fetch"      (returns title + body for one hit)
    model_call -> echo summary

Tool schemas live in ``tools.json`` next to this file so the Tier-2 (a) synthesizer can fall
back to constrained generation on un-recorded queries.
"""

from examples.research_agent.agent import TOOLS_JSON_PATH, run, tool_specs

__all__ = ["TOOLS_JSON_PATH", "run", "tool_specs"]
