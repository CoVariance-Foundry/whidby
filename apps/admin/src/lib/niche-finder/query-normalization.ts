import type { NicheQueryInput, NormalizedNicheQuery } from "@/lib/niche-finder/types";

function normalizeToken(value: string): string {
  return value.trim().toLowerCase().replace(/\s+/g, " ");
}

export function normalizeQueryInput(input: NicheQueryInput): NormalizedNicheQuery {
  const normalizedCity = normalizeToken(input.city);
  const normalizedService = normalizeToken(input.service);

  return {
    cityInput: input.city.trim(),
    serviceInput: input.service.trim(),
    normalizedCity,
    normalizedService,
    queryKey: `${normalizedCity}::${normalizedService}`,
  };
}
