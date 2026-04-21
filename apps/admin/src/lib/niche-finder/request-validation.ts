import type { NicheQueryInput } from "@/lib/niche-finder/types";

export interface ValidationResult {
  ok: boolean;
  message?: string;
}

export function validateNicheQueryInput(input: Partial<NicheQueryInput>): ValidationResult {
  const city = input.city?.trim() ?? "";
  const service = input.service?.trim() ?? "";

  if (!city || !service) {
    return {
      ok: false,
      message: "City and service are both required.",
    };
  }

  if (city.length < 2 || service.length < 2) {
    return {
      ok: false,
      message: "City and service must each contain at least 2 characters.",
    };
  }

  return { ok: true };
}

export function getValidationErrorResponse(message: string): {
  status: "validation_error";
  message: string;
} {
  return {
    status: "validation_error",
    message,
  };
}
