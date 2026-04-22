export const queryKeys = {
  scoring: {
    all: ["agent", "scoring"] as const,
    byQuery: (city: string, service: string) =>
      ["agent", "scoring", city, service] as const,
  },
  metros: {
    suggest: (q: string, limit?: number) =>
      ["agent", "metros", "suggest", q, limit ?? 5] as const,
  },
  reports: {
    all: ["reports"] as const,
    list: () => ["reports", "list"] as const,
    detail: (id: string) => ["reports", "detail", id] as const,
  },
} as const;
