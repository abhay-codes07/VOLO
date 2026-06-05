"""volo-simulator — Environment Simulator (bible §4 subsystem 2, the moat).

Two tiers (bible §9.2):

* **Tier 1** — deterministic cache-replay (ADR-0003 + ADR-0004). Shipped.
* **Tier 2** — hybrid synthesis with flag-on-unknown (ADR-0009). (a) Ollama constrained
  generation shipped in M5; (b) source-informed synthesis lands in M5.1.

Both implement ``SimulatedEnvironment`` from ``volo_core.interfaces``.
"""

from volo_simulator.replayer import (
    ReplayMiss,
    ReplayModelProvider,
    ReplayToolRegistry,
    Tier1Replayer,
)
from volo_simulator.tier2 import (
    OllamaConstrainedSynthesizer,
    SourceInformedSynthesizer,
    Synthesizer,
    Tier2Miss,
    Tier2Replayer,
    Tier2Stats,
)

__all__ = [
    "OllamaConstrainedSynthesizer",
    "ReplayMiss",
    "ReplayModelProvider",
    "ReplayToolRegistry",
    "SourceInformedSynthesizer",
    "Synthesizer",
    "Tier1Replayer",
    "Tier2Miss",
    "Tier2Replayer",
    "Tier2Stats",
]
