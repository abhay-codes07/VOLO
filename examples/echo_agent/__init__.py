"""examples.echo_agent — the simplest possible "agent" for dogfooding.

No LLM calls, no tools. Used as the e2e target for the test suite and the README quickstart.
The real value of having this stub is: it lets the entire pipeline (record → save → load → sim →
score) be exercised end-to-end without paying for an API or installing Ollama.
"""

from examples.echo_agent.agent import run

__all__ = ["run"]
