export function formatInteger(value: number | null | undefined): string {
  return value == null ? "-" : Math.round(value).toLocaleString("en-US");
}

export function formatCurrency(value: number | null | undefined): string {
  if (value == null) return "-";
  return value.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  });
}

export function formatPercent(value: number | null | undefined): string {
  if (value == null) return "-";
  const normalized = Math.abs(value) <= 1 ? value * 100 : value;
  return `${normalized.toFixed(1)}%`;
}

export function formatDecimal(value: number | null | undefined, digits = 1): string {
  return value == null ? "-" : value.toFixed(digits);
}

export function formatDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function humanize(value: string): string {
  return value
    .replace(/_/g, " ")
    .replace(/-/g, " ")
    .toLowerCase()
    .replace(/^\w/, (c) => c.toUpperCase());
}
