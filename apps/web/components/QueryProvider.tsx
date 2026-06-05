"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";

/**
 * TanStack Query provider — wraps the app so client-only views can use
 * `useQuery` for live data (CI dashboard polling, run-stream subscriptions).
 *
 * The provider is mounted at the root layout but is intentionally cheap when
 * no descendants use it (no background fetchers run by default).
 */
export function QueryProvider({ children }: { children: React.ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 10_000,
            refetchOnWindowFocus: false,
            retry: 1,
          },
        },
      }),
  );
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}
