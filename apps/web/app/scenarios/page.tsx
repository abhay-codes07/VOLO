import { TopNav } from "@/components/TopNav";
import { PageHeader } from "@/components/PageHeader";
import { ScenariosWall } from "@/components/ScenariosWall";
import { Footer } from "@/components/Footer";
import { listScenarios, safe } from "@/lib/api";

export default async function ScenariosPage() {
  const ops = (await safe(listScenarios())) ?? [];

  return (
    <>
      <TopNav />
      <PageHeader
        eyebrow="SCENARIO LIBRARY · ADR-0005"
        title={
          <>
            Storms in the
            <br />
            <span className="shimmer-text">simulator</span>.
          </>
        }
        description="Seven typed adversarial mutations applied to every baseline. Each is seeded, reproducible, and labeled with the failure class it probes."
        right={
          <div className="font-mono text-xs text-text-mute uppercase tracking-widest">
            {ops.length} operators · default seed 0
          </div>
        }
      />

      <ScenariosWall />

      <section className="max-w-7xl mx-auto px-6 md:px-10 pb-24">
        <div className="hairline bg-surface-1 p-7 shadow-elev-1">
          <div className="chip chip-info mb-4">RESEARCH</div>
          <h2 className="font-display text-2xl font-semibold text-text-hi tracking-tighter mb-3">
            Why these seven?
          </h2>
          <p className="text-text-mid leading-relaxed mb-3 max-w-3xl">
            The taxonomy is governed by ADR-0005 in the repo and aligns with the failure-class
            literature on multi-step agents. Each operator is a pure function from one Recording
            to a mutated Recording — no LLM, no randomness beyond a seeded RNG.
          </p>
          <p className="text-text-lo text-sm max-w-3xl">
            Adding an operator means amending the ADR. That's deliberate: a reliability report
            from one commit must be reproducible from any future commit, given the same seed.
          </p>
        </div>
      </section>

      <Footer />
    </>
  );
}
