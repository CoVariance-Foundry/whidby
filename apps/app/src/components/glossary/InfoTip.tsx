"use client";

import { useCallback, useEffect, useId, useRef, useState } from "react";
import type { CSSProperties, ReactNode } from "react";
import { Icon, I } from "@/lib/icons";

interface InfoTipProps {
  title: string;
  children: ReactNode;
  ariaLabel?: string;
}

interface TooltipPosition {
  top: number;
  left: number;
  width: number;
  placement: "top" | "bottom";
}

const VIEWPORT_MARGIN = 12;
const TARGET_WIDTH = 280;
const MIN_WIDTH = 200;

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

export default function InfoTip({ title, children, ariaLabel }: InfoTipProps) {
  const tooltipId = useId();
  const wrapperRef = useRef<HTMLSpanElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);
  const [pinned, setPinned] = useState(false);
  const [hovered, setHovered] = useState(false);
  const [focused, setFocused] = useState(false);
  const [position, setPosition] = useState<TooltipPosition>({
    top: 0,
    left: VIEWPORT_MARGIN,
    width: TARGET_WIDTH,
    placement: "bottom",
  });
  const [positionReady, setPositionReady] = useState(false);
  const open = pinned || hovered || focused;

  const updatePosition = useCallback(() => {
    if (!triggerRef.current || typeof window === "undefined") return;
    const rect = triggerRef.current.getBoundingClientRect();
    const viewportWidth = window.innerWidth || TARGET_WIDTH + VIEWPORT_MARGIN * 2;
    const viewportHeight = window.innerHeight || 640;
    const width = Math.max(
      MIN_WIDTH,
      Math.min(TARGET_WIDTH, viewportWidth - VIEWPORT_MARGIN * 2),
    );
    const maxLeft = Math.max(VIEWPORT_MARGIN, viewportWidth - width - VIEWPORT_MARGIN);
    const left = clamp(rect.left + rect.width / 2 - width / 2, VIEWPORT_MARGIN, maxLeft);
    const tooltipHeight = tooltipRef.current?.offsetHeight ?? 160;
    const belowTop = rect.bottom + 8;
    const hasRoomBelow = belowTop + tooltipHeight <= viewportHeight - VIEWPORT_MARGIN;
    const hasRoomAbove = rect.top - tooltipHeight - 8 >= VIEWPORT_MARGIN;

    if (!hasRoomBelow && hasRoomAbove) {
      setPosition({
        top: rect.top - 8,
        left,
        width,
        placement: "top",
      });
      setPositionReady(true);
      return;
    }

    const maxBottomPlacementTop = Math.max(
      VIEWPORT_MARGIN,
      viewportHeight - tooltipHeight - VIEWPORT_MARGIN,
    );
    setPosition({
      top: clamp(belowTop, VIEWPORT_MARGIN, maxBottomPlacementTop),
      left,
      width,
      placement: "bottom",
    });
    setPositionReady(true);
  }, []);

  useEffect(() => {
    if (!open) return;
    updatePosition();
    window.addEventListener("resize", updatePosition);
    window.addEventListener("scroll", updatePosition, true);
    return () => {
      window.removeEventListener("resize", updatePosition);
      window.removeEventListener("scroll", updatePosition, true);
    };
  }, [open, updatePosition]);

  useEffect(() => {
    if (!open) return;
    function handleOutside(event: MouseEvent | TouchEvent) {
      if (wrapperRef.current?.contains(event.target as Node)) return;
      setPinned(false);
      setHovered(false);
      setFocused(false);
      setPositionReady(false);
    }
    function handleEscape(event: KeyboardEvent) {
      if (event.key !== "Escape") return;
      event.preventDefault();
      event.stopImmediatePropagation();
      setPinned(false);
      setHovered(false);
      setFocused(false);
      setPositionReady(false);
      triggerRef.current?.blur();
    }
    document.addEventListener("mousedown", handleOutside);
    document.addEventListener("touchstart", handleOutside, { passive: true });
    document.addEventListener("keydown", handleEscape, true);
    return () => {
      document.removeEventListener("mousedown", handleOutside);
      document.removeEventListener("touchstart", handleOutside);
      document.removeEventListener("keydown", handleEscape, true);
    };
  }, [open]);

  const closePinned = useCallback(() => {
    setPinned(false);
    setHovered(false);
    setFocused(false);
    setPositionReady(false);
    triggerRef.current?.blur();
  }, []);

  const handleClick = useCallback(() => {
    if (pinned) {
      closePinned();
      return;
    }
    if (!open) setPositionReady(false);
    setPinned(true);
  }, [closePinned, open, pinned]);

  const tooltipStyle: CSSProperties = {
    position: "fixed",
    top: position.top,
    left: position.left,
    width: position.width,
    transform: position.placement === "top" ? "translateY(-100%)" : undefined,
    padding: "12px 14px",
    background: "var(--card)",
    border: "1px solid var(--rule-strong)",
    borderRadius: 8,
    boxShadow: "0 10px 28px rgba(31, 27, 22, 0.16)",
    zIndex: 250,
    pointerEvents: "auto",
    opacity: positionReady ? 1 : 0,
    maxHeight: "min(260px, calc(100vh - 24px))",
    overflowY: "auto",
    textTransform: "none",
  };

  return (
    <span
      ref={wrapperRef}
      style={{
        position: "relative",
        display: "inline-flex",
        alignItems: "center",
        verticalAlign: "baseline",
      }}
      onMouseEnter={() => {
        if (!open) setPositionReady(false);
        setHovered(true);
      }}
      onMouseLeave={() => setHovered(false)}
    >
      <button
        ref={triggerRef}
        type="button"
        aria-describedby={open ? tooltipId : undefined}
        aria-expanded={open}
        aria-label={ariaLabel ?? `More about ${title}`}
        onBlur={(event) => {
          if (wrapperRef.current?.contains(event.relatedTarget as Node | null)) return;
          if (!pinned) {
            setFocused(false);
            setPositionReady(false);
          }
        }}
        onClick={handleClick}
        onFocus={() => {
          if (!open) setPositionReady(false);
          setFocused(true);
        }}
        style={{
          display: "inline-grid",
          placeItems: "center",
          width: 16,
          height: 16,
          padding: 0,
          margin: "0 0 0 4px",
          border: "1px solid transparent",
          borderRadius: 999,
          background: "transparent",
          color: open ? "var(--accent-ink)" : "var(--ink-3)",
          cursor: "help",
          opacity: open ? 1 : 0.72,
          boxShadow: focused ? "0 0 0 3px var(--accent-soft)" : undefined,
          transition: "color 0.15s, opacity 0.15s, box-shadow 0.15s",
          flexShrink: 0,
        }}
      >
        <Icon d={I.info} size={13} sw={1.8} />
      </button>

      {open ? (
        <div id={tooltipId} ref={tooltipRef} role="tooltip" style={tooltipStyle}>
          <div
            style={{
              fontFamily: "var(--serif)",
              fontWeight: 600,
              fontSize: 13,
              color: "var(--ink)",
              marginBottom: 5,
            }}
          >
            {title}
          </div>
          <div
            style={{
              fontFamily: "var(--sans)",
              fontSize: 12,
              lineHeight: 1.5,
              color: "var(--ink-2)",
            }}
          >
            {children}
          </div>
        </div>
      ) : null}
    </span>
  );
}
