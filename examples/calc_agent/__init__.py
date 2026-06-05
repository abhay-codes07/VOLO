"""examples.calc_agent — a multi-step "agent" that plans, calls tools, then summarizes.

Used as a richer e2e target than echo_agent: it makes a planning model call, two tool calls
(add, multiply), and a summary model call. This lets the scenarios + reliability engines have
something interesting to perturb in the test suite.
"""

from examples.calc_agent.agent import run

__all__ = ["run"]
