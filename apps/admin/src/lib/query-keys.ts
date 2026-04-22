export const queryKeys = {
  scoring: {
    all: ["agent", "scoring"] as const,
    byQuery: (city: string, service: string) =>
      ["agent", "scoring", city, service] as const,
  },
  exploration: {
    all: ["agent", "exploration"] as const,
    byQuery: (city: string, service: string) =>
      ["agent", "exploration", city, service] as const,
  },
  metros: {
    suggest: (q: string, limit?: number) =>
      ["agent", "metros", "suggest", q, limit ?? 5] as const,
  },
  sessions: {
    all: ["agent", "sessions"] as const,
    detail: (runId: string) => ["agent", "sessions", runId] as const,
  },
  experiments: {
    byRun: (runId: string) => ["agent", "experiments", runId] as const,
  },
  graph: {
    all: ["agent", "graph"] as const,
  },
} as const;
