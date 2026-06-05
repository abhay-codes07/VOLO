import "@testing-library/jest-dom/vitest";

// Stub matchMedia (jsdom doesn't implement it) so motion / cursor primitives don't crash.
if (typeof window !== "undefined" && !window.matchMedia) {
  window.matchMedia = (q: string) =>
    ({
      matches: false,
      media: q,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    }) as unknown as MediaQueryList;
}

// Pointer event helpers absent from jsdom.
if (typeof window !== "undefined" && !window.PointerEvent) {
  // @ts-expect-error — provide a minimal shim so animations don't throw on missing class
  window.PointerEvent = class PointerEvent extends Event {};
}
