"use client";

import Link from "next/link";
import { type RefObject, useRef } from "react";
import { Icon, I } from "@/lib/icons";
import type { ExploreScanTarget } from "@/lib/explore/types";
import { useModalAccessibility } from "./useModalAccessibility";

export interface FreshScanResult {
  service: string;
  status: "success" | "error";
  report_id?: string;
  message?: string;
}

interface FreshScanConfirmationProps {
  cityName: string;
  targets: ExploreScanTarget[];
  results: FreshScanResult[];
  isOpen: boolean;
  isSubmitting: boolean;
  restoreFocusRef?: RefObject<HTMLElement | null>;
  onCancel: () => void;
  onConfirm: (targets: ExploreScanTarget[]) => void | Promise<void>;
}

export default function FreshScanConfirmation({
  cityName,
  targets,
  results,
  isOpen,
  isSubmitting,
  restoreFocusRef,
  onCancel,
  onConfirm,
}: FreshScanConfirmationProps) {
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  useModalAccessibility({
    isOpen,
    onClose: onCancel,
    focusRef: closeButtonRef,
    restoreFocusRef,
  });

  if (!isOpen) return null;

  return (
    <div
      role="presentation"
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 60,
        background: "rgba(31, 27, 22, 0.28)",
        display: "grid",
        placeItems: "center",
        padding: 20,
      }}
      onClick={onCancel}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="fresh-scan-title"
        aria-describedby="fresh-scan-description"
        aria-busy={isSubmitting}
        onClick={(event) => event.stopPropagation()}
        style={{
          width: "min(520px, 100%)",
          background: "var(--card)",
          border: "1px solid var(--rule-strong)",
          borderRadius: 12,
          boxShadow: "0 24px 70px rgba(31, 27, 22, 0.18)",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            padding: "18px 20px",
            borderBottom: "1px solid var(--rule)",
            background: "var(--paper-alt)",
            display: "flex",
            alignItems: "flex-start",
            justifyContent: "space-between",
            gap: 16,
          }}
        >
          <div>
            <h2
              id="fresh-scan-title"
              style={{
                margin: 0,
                fontFamily: "var(--serif)",
                fontSize: 20,
                fontWeight: 600,
                color: "var(--ink)",
              }}
            >
              Confirm fresh scan
            </h2>
            <p
              id="fresh-scan-description"
              style={{
                margin: "6px 0 0",
                fontFamily: "var(--sans)",
                fontSize: 13,
                lineHeight: 1.5,
                color: "var(--ink-2)",
              }}
            >
              {cityName} · {targets.length} fresh scans selected. Uses one monthly fresh scan per selected service.
            </p>
          </div>
          <button
            ref={closeButtonRef}
            type="button"
            className="icon-btn"
            aria-label="Close fresh scan dialog"
            onClick={onCancel}
          >
            <Icon d={I.x} />
          </button>
        </div>

        <div style={{ padding: "16px 20px 18px" }}>
          <div
            aria-label="Selected services"
            style={{
              display: "grid",
              gap: 8,
              marginBottom: 18,
            }}
          >
            {targets.map((target) => (
              <div
                key={target.report_id ?? `${target.source}:${target.service}`}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  gap: 12,
                  padding: "9px 11px",
                  border: "1px solid var(--rule)",
                  borderRadius: 8,
                  background: "var(--paper)",
                  fontFamily: "var(--sans)",
                  fontSize: 13,
                }}
              >
                <span style={{ minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {target.service_label}
                </span>
                <span
                  style={{
                    fontFamily: "var(--mono)",
                    color: "var(--accent-ink)",
                    fontWeight: 600,
                    flexShrink: 0,
                  }}
                >
                  {target.source === "cached" ? "cached" : "new"}
                </span>
              </div>
            ))}
          </div>

          {isSubmitting && (
            <p
              role="status"
              style={{
                margin: "0 0 14px",
                padding: "10px 12px",
                border: "1px solid var(--rule)",
                borderRadius: 8,
                background: "var(--paper-alt)",
                color: "var(--ink-2)",
                fontFamily: "var(--sans)",
                fontSize: 13,
              }}
            >
              Running fresh scans...
            </p>
          )}

          {results.length > 0 && (
            <div
              aria-label="Fresh scan results"
              aria-live="polite"
              style={{
                display: "grid",
                gap: 8,
                margin: "0 0 16px",
              }}
            >
              {results.map((result, index) => (
                <div
                  key={`${result.service}:${result.report_id ?? result.message ?? index}`}
                  role={result.status === "error" ? "alert" : "status"}
                  style={{
                    display: "grid",
                    gap: 5,
                    padding: "10px 12px",
                    border: "1px solid var(--rule)",
                    borderRadius: 8,
                    background:
                      result.status === "success"
                        ? "var(--accent-soft)"
                        : "var(--paper-alt)",
                    color:
                      result.status === "success"
                        ? "var(--accent-ink)"
                        : "var(--ink-2)",
                    fontFamily: "var(--sans)",
                    fontSize: 13,
                  }}
                >
                  <strong style={{ color: "inherit" }}>
                    {result.service} {result.status === "success" ? "scan succeeded" : "scan failed"}
                  </strong>
                  {result.status === "success" && result.report_id ? (
                    <Link
                      href={`/reports?open=${encodeURIComponent(result.report_id)}`}
                      aria-label={`Open fresh report for ${result.service}`}
                      style={{
                        color: "inherit",
                        fontWeight: 700,
                        textDecoration: "underline",
                        textUnderlineOffset: 3,
                      }}
                    >
                      Open report
                    </Link>
                  ) : (
                    <span>
                      {result.message ??
                        (result.status === "success"
                          ? "Scan completed, but no report link was returned."
                          : "Scoring unavailable. Try again shortly.")}
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}

          <div style={{ display: "flex", justifyContent: "flex-end", gap: 10 }}>
            <button
              type="button"
              className="btn-ghost"
              aria-label="Cancel fresh scan"
              onClick={onCancel}
            >
              Cancel
            </button>
            <button
              type="button"
              className="btn-primary"
              aria-label={`Confirm fresh scan for ${targets.length} services`}
              onClick={() => onConfirm(targets)}
              disabled={targets.length === 0 || isSubmitting}
            >
              <Icon d={I.sparkle} />
              {isSubmitting ? "Scanning..." : "Confirm scan"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
