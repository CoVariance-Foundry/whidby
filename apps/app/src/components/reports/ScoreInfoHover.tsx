"use client";

import { useCallback, useEffect, useId, useRef, useState } from "react";
import { Icon, I } from "@/lib/icons";
import type { ScoreKey } from "@/lib/reports/score-explainers";
import { SCORE_EXPLAINERS } from "@/lib/reports/score-explainers";

interface Props {
  scoreKey: ScoreKey;
}

export default function ScoreInfoHover({ scoreKey }: Props) {
  const explainer = SCORE_EXPLAINERS[scoreKey];
  const tooltipId = useId();
  const wrapperRef = useRef<HTMLSpanElement>(null);
  const [pinned, setPinned] = useState(false);
  const [hovered, setHovered] = useState(false);
  const open = pinned || hovered;

  const handleClick = useCallback(() => setPinned((p) => !p), []);

  useEffect(() => {
    if (!pinned) return;
    function handleOutside(e: MouseEvent | TouchEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setPinned(false);
      }
    }
    function handleEscape(e: KeyboardEvent) {
      if (e.key === "Escape") setPinned(false);
    }
    document.addEventListener("mousedown", handleOutside);
    document.addEventListener("touchstart", handleOutside);
    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("mousedown", handleOutside);
      document.removeEventListener("touchstart", handleOutside);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [pinned]);

  return (
    <span
      ref={wrapperRef}
      style={{ position: "relative", display: "inline-flex", alignItems: "center" }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <button
        type="button"
        aria-describedby={open ? tooltipId : undefined}
        aria-label={`What is ${explainer.title}?`}
        onClick={handleClick}
        style={{
          display: "inline-grid",
          placeItems: "center",
          width: 16,
          height: 16,
          padding: 0,
          margin: 0,
          marginLeft: 4,
          border: "none",
          borderRadius: 999,
          background: "transparent",
          color: "var(--ink-3)",
          cursor: "help",
          opacity: open ? 1 : 0.5,
          transition: "opacity 0.15s",
          verticalAlign: "middle",
          flexShrink: 0,
        }}
      >
        <Icon d={I.info} size={13} sw={1.8} />
      </button>

      {open && (
        <div
          id={tooltipId}
          role="tooltip"
          style={{
            position: "absolute",
            bottom: "calc(100% + 8px)",
            left: "50%",
            transform: "translateX(-50%)",
            width: 260,
            padding: "14px 16px",
            background: "var(--card)",
            border: "1px solid var(--rule-strong)",
            borderRadius: 10,
            boxShadow: "0 8px 24px rgba(31, 27, 22, 0.14)",
            zIndex: 200,
            pointerEvents: "auto",
          }}
        >
          <div
            style={{
              fontFamily: "var(--serif)",
              fontWeight: 600,
              fontSize: 13,
              color: "var(--ink)",
              marginBottom: 6,
            }}
          >
            {explainer.title}
          </div>

          <p
            style={{
              fontFamily: "var(--sans)",
              fontSize: 12,
              lineHeight: 1.5,
              color: "var(--ink-2)",
              margin: "0 0 8px",
            }}
          >
            {explainer.definition}
          </p>

          <div
            style={{
              fontFamily: "var(--serif)",
              fontStyle: "italic",
              fontSize: 11,
              color: "var(--ink-3)",
              marginBottom: 8,
            }}
          >
            {explainer.howToRead}
          </div>

          <div style={{ display: "flex", gap: 6 }}>
            {explainer.bands.map((band) => (
              <div
                key={band.label}
                style={{
                  flex: 1,
                  padding: "4px 0",
                  borderRadius: 6,
                  background: band.bg,
                  textAlign: "center",
                }}
              >
                <div
                  style={{
                    fontFamily: "var(--sans)",
                    fontSize: 10,
                    fontWeight: 600,
                    color: band.color,
                    textTransform: "uppercase",
                    letterSpacing: "0.04em",
                  }}
                >
                  {band.label}
                </div>
                <div
                  style={{
                    fontFamily: "var(--mono)",
                    fontSize: 10,
                    color: band.color,
                    opacity: 0.8,
                    marginTop: 1,
                  }}
                >
                  {band.range}
                </div>
              </div>
            ))}
          </div>

          {/* Arrow nub */}
          <div
            style={{
              position: "absolute",
              bottom: -5,
              left: "50%",
              transform: "translateX(-50%) rotate(45deg)",
              width: 10,
              height: 10,
              background: "var(--card)",
              borderRight: "1px solid var(--rule-strong)",
              borderBottom: "1px solid var(--rule-strong)",
            }}
          />
        </div>
      )}
    </span>
  );
}
