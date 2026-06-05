"use client";

import { Reveal, Stagger, StaggerItem } from "@/components/motion/Reveal";

const WITHOUT = [
  "Production logs surface the bug.",
  "Flaky tests burn API budget.",
  "30 manual reruns to “check determinism”.",
  "Failure mode lost three tool calls ago.",
];

const WITH = [
  "PR fails three milliseconds after diff.",
  "Replays at $0 — record-time pays the bill.",
  "Seven scenarios × four metrics on every push.",
  "Pinpoint the breaking step + commit.",
];

export function Comparison() {
  return (
    <section className="relative max-w-7xl mx-auto px-6 md:px-10 py-28">
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-start">
        <Reveal className="lg:col-span-4">
          <div className="chip chip-failure mb-5">old way</div>
          <h2 className="font-display text-display-md font-semibold text-text-hi tracking-tighter mb-5">
            Agents fail.<br />
            <span className="text-signal-failure">Tests don't.</span>
          </h2>
          <p className="text-text-mid leading-relaxed">
            80 % to 99 % takes 100×. Nothing in your toolbox treats agents like real software.
          </p>
        </Reveal>

        <Stagger className="lg:col-span-8 grid grid-cols-1 md:grid-cols-2 gap-4">
          <StaggerItem>
            <div className="hairline bg-surface-1 p-7 shadow-elev-1 h-full">
              <div className="chip chip-failure mb-5">without</div>
              <ul className="space-y-3.5">
                {WITHOUT.map((line) => (
                  <li key={line} className="flex gap-3 text-text-mid leading-relaxed">
                    <span className="text-signal-failure font-mono leading-7 text-lg">×</span>
                    <span>{line}</span>
                  </li>
                ))}
              </ul>
            </div>
          </StaggerItem>
          <StaggerItem>
            <div className="relative hairline-2 bg-surface-1 p-7 shadow-elev-2 h-full overflow-hidden" style={{ borderColor: "var(--signal-nominal-soft)" }}>
              <div className="chip chip-nominal mb-5">with Volo</div>
              <ul className="space-y-3.5">
                {WITH.map((line) => (
                  <li key={line} className="flex gap-3 text-text-mid leading-relaxed">
                    <span className="text-signal-nominal font-mono leading-7 text-lg">✓</span>
                    <span>{line}</span>
                  </li>
                ))}
              </ul>
              <span aria-hidden className="absolute -inset-px pointer-events-none" style={{ background: "radial-gradient(60% 60% at 50% 0%, rgba(61,224,184,0.08), transparent 60%)" }} />
            </div>
          </StaggerItem>
        </Stagger>
      </div>
    </section>
  );
}
