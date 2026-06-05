import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        surface: {
          0: "var(--surface-0)",
          1: "var(--surface-1)",
          2: "var(--surface-2)",
          3: "var(--surface-3)",
          glass: "var(--surface-glass)",
        },
        border: {
          1: "var(--border-1)",
          2: "var(--border-2)",
          3: "var(--border-3)",
        },
        text: {
          hi: "var(--text-hi)",
          mid: "var(--text-mid)",
          lo: "var(--text-lo)",
          mute: "var(--text-mute)",
          faint: "var(--text-faint)",
        },
        signal: {
          nominal: "var(--signal-nominal)",
          warning: "var(--signal-warning)",
          failure: "var(--signal-failure)",
          info: "var(--signal-info)",
          magenta: "var(--signal-magenta)",
        },
      },
      fontFamily: {
        display: ["var(--font-display)"],
        serif:   ["var(--font-serif)"],
        sans:    ["var(--font-sans)"],
        mono:    ["var(--font-mono)"],
      },
      fontSize: {
        // Tighter display tracking via these custom steps
        "display-sm": ["clamp(2rem, 5vw, 3rem)", { lineHeight: "1.05", letterSpacing: "-0.02em" }],
        "display-md": ["clamp(2.5rem, 6vw, 4.5rem)", { lineHeight: "1.02", letterSpacing: "-0.025em" }],
        "display-lg": ["clamp(3rem, 8vw, 6.5rem)", { lineHeight: "0.98", letterSpacing: "-0.03em" }],
        "display-xl": ["clamp(3.5rem, 10vw, 8.5rem)", { lineHeight: "0.94", letterSpacing: "-0.035em" }],
      },
      letterSpacing: {
        tighter: "-0.04em",
        tightest: "-0.06em",
        "widest-2": "0.18em",
      },
      boxShadow: {
        "glow-nominal": "0 0 32px rgba(61, 224, 184, 0.35)",
        "glow-info": "0 0 32px rgba(111, 170, 255, 0.30)",
        "glow-failure": "0 0 28px rgba(255, 92, 108, 0.40)",
        "elev-1": "0 1px 0 rgba(255,255,255,0.02), 0 12px 30px rgba(0,0,0,0.45)",
        "elev-2": "0 1px 0 rgba(255,255,255,0.03), 0 24px 60px rgba(0,0,0,0.55)",
      },
      backgroundImage: {
        "grid-fine":
          "linear-gradient(to right, rgba(255,255,255,0.03) 1px, transparent 1px), linear-gradient(to bottom, rgba(255,255,255,0.03) 1px, transparent 1px)",
        "mesh-hero":
          "radial-gradient(40% 50% at 18% 35%, rgba(111,170,255,0.20), transparent 70%), radial-gradient(40% 50% at 78% 28%, rgba(61,224,184,0.16), transparent 70%), radial-gradient(45% 60% at 50% 95%, rgba(182,121,255,0.14), transparent 70%)",
      },
    },
  },
  plugins: [],
};

export default config;
