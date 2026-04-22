import type { CSSProperties } from "react";

export const I = {
  search: "M21 21l-4.3-4.3M17 11a6 6 0 11-12 0 6 6 0 0112 0z",
  clock: "M12 8v4l3 2M21 12a9 9 0 11-18 0 9 9 0 0118 0z",
  arrow: "M5 12h14M13 6l6 6-6 6",
  star: "M12 3l2.9 6 6.6.9-4.8 4.5 1.2 6.6L12 17.9 6.1 21l1.2-6.6L2.5 9.9 9.1 9z",
  map: "M9 20l-6-2V4l6 2m0 14V6m0 14l6-2m-6-12l6 2m0 0v14m0-14l6-2v14l-6 2",
  mapPin:
    "M12 21s-7-7-7-12a7 7 0 1114 0c0 5-7 12-7 12zm0-9a3 3 0 100-6 3 3 0 000 6z",
  sliders: "M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12M20 18h0M14 4v4M8 10v4M16 16v4",
  filter: "M4 6h16M7 12h10M10 18h4",
  list: "M4 6h16M4 12h16M4 18h16",
  grid: "M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z",
  check: "M5 13l4 4L19 7",
  x: "M6 6l12 12M18 6L6 18",
  bell: "M15 17h5l-1.4-1.4A2 2 0 0118 14.2V11a6 6 0 10-12 0v3.2c0 .5-.2 1-.6 1.4L4 17h5m6 0v1a3 3 0 01-6 0v-1m6 0H9",
  plus: "M12 5v14M5 12h14",
  save: "M19 21H5a2 2 0 01-2-2V5a2 2 0 012-2h11l5 5v11a2 2 0 01-2 2zM17 21v-8H7v8M7 3v5h8",
  home: "M3 11l9-8 9 8v10a2 2 0 01-2 2h-3v-7h-8v7H5a2 2 0 01-2-2V11z",
  sparkle:
    "M12 3l1.8 4.5L18 9l-4.2 1.5L12 15l-1.8-4.5L6 9l4.2-1.5zM19 2l.8 2L22 5l-2.2 1L19 8l-.8-2L16 5l2.2-1z",
  target:
    "M12 12m-9 0a9 9 0 1118 0 9 9 0 11-18 0M12 12m-5 0a5 5 0 1110 0 5 5 0 11-10 0M12 12m-1 0a1 1 0 112 0 1 1 0 11-2 0",
  info: "M12 22a10 10 0 110-20 10 10 0 010 20zM12 16v-4M12 8h.01",
  arrowUp: "M12 19V5M5 12l7-7 7 7",
  arrowDown: "M12 5v14M19 12l-7 7-7-7",
  chevronDown: "M6 9l6 6 6-6",
} as const;

export function Icon({
  d,
  size = 14,
  sw = 1.6,
  fill = "none",
  style,
}: {
  d: string;
  size?: number;
  sw?: number;
  fill?: string;
  style?: CSSProperties;
}) {
  return (
    <svg
      viewBox="0 0 24 24"
      width={size}
      height={size}
      fill={fill}
      stroke="currentColor"
      strokeWidth={sw}
      strokeLinecap="round"
      strokeLinejoin="round"
      style={style}
    >
      <path d={d} />
    </svg>
  );
}
