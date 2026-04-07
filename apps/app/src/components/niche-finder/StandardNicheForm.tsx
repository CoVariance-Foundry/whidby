"use client";

import { useState } from "react";
import type { NicheQueryInput } from "@/lib/niche-finder/types";

interface StandardNicheFormProps {
  initialQuery: NicheQueryInput;
  onSubmit: (query: NicheQueryInput) => void;
  disabled?: boolean;
}

export default function StandardNicheForm({
  initialQuery,
  onSubmit,
  disabled = false,
}: StandardNicheFormProps) {
  const [city, setCity] = useState(initialQuery.city);
  const [service, setService] = useState(initialQuery.service);

  return (
    <form
      className="grid gap-3 rounded-lg border border-[var(--color-dark-border)] bg-[var(--color-dark-card)] p-4 md:grid-cols-3"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit({ city, service });
      }}
    >
      <input
        className="rounded-md border border-[var(--color-dark-border)] bg-[var(--color-dark)] px-3 py-2 text-sm"
        placeholder="City (e.g. Phoenix)"
        value={city}
        onChange={(event) => setCity(event.target.value)}
        disabled={disabled}
      />
      <input
        className="rounded-md border border-[var(--color-dark-border)] bg-[var(--color-dark)] px-3 py-2 text-sm"
        placeholder="Service (e.g. roofing)"
        value={service}
        onChange={(event) => setService(event.target.value)}
        disabled={disabled}
      />
      <button
        type="submit"
        disabled={disabled}
        className="rounded-md bg-[var(--color-accent)] px-3 py-2 text-sm font-medium text-white hover:bg-[var(--color-accent-dark)] disabled:cursor-not-allowed disabled:opacity-60"
      >
        Score Niche
      </button>
    </form>
  );
}
