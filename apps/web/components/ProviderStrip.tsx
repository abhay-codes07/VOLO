"use client";

import { Reveal } from "@/components/motion/Reveal";

const PROVIDERS = [
  "OpenAI",
  "Anthropic",
  "Google",
  "Mistral",
  "Ollama",
  "LangGraph",
  "OpenAI Agents SDK",
  "CrewAI",
];

export function ProviderStrip() {
  return (
    <section className="relative max-w-7xl mx-auto px-6 md:px-10 py-16">
      <Reveal>
        <div className="font-mono text-[11px] uppercase tracking-widest text-text-mute mb-6 text-center">
          Works with what you already ship
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-px bg-border-1">
          {PROVIDERS.map((p) => (
            <div
              key={p}
              className="bg-surface-1 px-5 py-6 text-center font-display text-lg tracking-tighter text-text-mute hover:text-text-hi hover:bg-surface-2 transition-colors cursor-default"
            >
              {p}
            </div>
          ))}
        </div>
      </Reveal>
    </section>
  );
}
