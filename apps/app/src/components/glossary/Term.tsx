"use client";

import type { ReactNode } from "react";
import InfoTip from "@/components/glossary/InfoTip";
import { resolveGlossaryTerm } from "@/lib/glossary";

interface TermProps {
  termKey?: string;
  label?: string;
  fallbackDefinition?: string;
  fallbackContext?: string;
  children?: ReactNode;
}

function stringChild(children: ReactNode): string | undefined {
  return typeof children === "string" ? children : undefined;
}

export default function Term({
  termKey,
  label,
  fallbackDefinition,
  fallbackContext,
  children,
}: TermProps) {
  const childLabel = stringChild(children);
  const lookup = termKey ?? childLabel ?? label ?? "";
  const term = resolveGlossaryTerm(lookup, {
    label: label ?? childLabel,
    definition: fallbackDefinition,
    context: fallbackContext,
  });
  const displayLabel = children ?? label ?? term.label;

  return (
    <span
      data-glossary-key={term.key}
      style={{
        display: "inline-flex",
        alignItems: "center",
        minWidth: 0,
        verticalAlign: "baseline",
      }}
    >
      <span
        style={{
          color: "inherit",
          textDecoration: "underline dotted var(--rule-strong)",
          textUnderlineOffset: 3,
        }}
      >
        {displayLabel}
      </span>
      <InfoTip title={term.label} ariaLabel={`What is ${term.label}?`}>
        <span>{term.definition}</span>
        {term.context ? (
          <span style={{ display: "block", marginTop: 6, color: "var(--ink-3)" }}>
            {term.context}
          </span>
        ) : null}
      </InfoTip>
    </span>
  );
}
