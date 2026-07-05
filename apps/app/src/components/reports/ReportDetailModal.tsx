"use client";

import { useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import { Icon, I } from "@/lib/icons";
import type { FullReportData } from "@/lib/niche-finder/types";
import ReportActions from "@/components/reports/ReportActions";
import ReportV11Detail from "@/components/reports/ReportV11Detail";

interface Props {
  report: FullReportData;
  onClose: () => void;
  onDelete?: (reportId: string) => Promise<void>;
}

export default function ReportDetailModal({ report, onClose, onDelete }: Props) {
  const closeBtnRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    closeBtnRef.current?.focus();
  }, []);

  useEffect(() => {
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, []);

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [onClose]);

  const closeButton = (
    <button
      ref={closeBtnRef}
      onClick={onClose}
      aria-label="Close"
      style={{
        position: "absolute",
        top: 16,
        right: 16,
        width: 32,
        height: 32,
        borderRadius: 8,
        display: "grid",
        placeItems: "center",
        color: "var(--ink-2)",
        border: "1px solid var(--rule-strong)",
        background: "var(--card)",
        cursor: "pointer",
        zIndex: 2,
      }}
    >
      <Icon d={I.x} size={14} />
    </button>
  );

  return createPortal(
    <div
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
      role="dialog"
      aria-modal="true"
      aria-label={`Report: ${report.niche_keyword}`}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(31, 27, 22, 0.35)",
        zIndex: 100,
        display: "grid",
        placeItems: "center",
        padding: 24,
      }}
    >
      <div
        style={{
          background: "var(--card)",
          border: "1px solid var(--rule-strong)",
          borderRadius: 14,
          boxShadow: "0 20px 60px rgba(31, 27, 22, 0.22)",
          width: "100%",
          maxWidth: 860,
          maxHeight: "calc(100vh - 48px)",
          overflowY: "auto",
          position: "relative",
        }}
      >
        <ReportV11Detail
          report={report}
          variant="modal"
          showBackLink={false}
          headerAccessory={closeButton}
          actions={<ReportActions report={report} onDelete={onDelete} />}
        />
      </div>
    </div>,
    document.body,
  );
}
