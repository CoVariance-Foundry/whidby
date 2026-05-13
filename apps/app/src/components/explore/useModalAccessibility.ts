"use client";

import { type RefObject, useEffect, useRef } from "react";

let bodyLockCount = 0;
let bodyOverflowBeforeLock = "";

const FOCUSABLE_SELECTOR = [
  "a[href]",
  "button:not([disabled])",
  "input:not([disabled]):not([type='hidden'])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  "iframe",
  "object",
  "embed",
  "[contenteditable='true']",
  "[tabindex]:not([tabindex='-1'])",
].join(",");

function lockBodyScroll() {
  if (bodyLockCount === 0) {
    bodyOverflowBeforeLock = document.body.style.overflow;
    document.body.style.overflow = "hidden";
  }
  bodyLockCount += 1;
}

function unlockBodyScroll() {
  bodyLockCount = Math.max(0, bodyLockCount - 1);
  if (bodyLockCount === 0) {
    document.body.style.overflow = bodyOverflowBeforeLock;
    bodyOverflowBeforeLock = "";
  }
}

function isFocusableElement(element: HTMLElement) {
  if (element.hidden || element.getAttribute("aria-hidden") === "true") {
    return false;
  }

  const style = window.getComputedStyle(element);
  return style.display !== "none" && style.visibility !== "hidden";
}

function getFocusTrapRoot(focusTarget: HTMLElement | null) {
  return focusTarget?.closest<HTMLElement>("[role='dialog']") ?? focusTarget;
}

function getFocusableElements(container: HTMLElement) {
  const candidates = [
    ...(container.matches(FOCUSABLE_SELECTOR) ? [container] : []),
    ...Array.from(container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)),
  ];

  return candidates.filter(isFocusableElement);
}

interface ModalAccessibilityOptions<T extends HTMLElement> {
  isOpen: boolean;
  isTopLayer?: boolean;
  onClose: () => void;
  focusRef: RefObject<T | null>;
  restoreFocusRef?: RefObject<HTMLElement | null>;
}

export function useModalAccessibility<T extends HTMLElement>({
  isOpen,
  isTopLayer = true,
  onClose,
  focusRef,
  restoreFocusRef,
}: ModalAccessibilityOptions<T>) {
  const previousFocusRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!isOpen) return;

    previousFocusRef.current =
      restoreFocusRef?.current ??
      (document.activeElement instanceof HTMLElement ? document.activeElement : null);

    lockBodyScroll();
    focusRef.current?.focus();

    return () => {
      unlockBodyScroll();

      const previousFocus = previousFocusRef.current;
      if (previousFocus && document.contains(previousFocus)) {
        previousFocus.focus();
      }
    };
  }, [focusRef, isOpen, restoreFocusRef]);

  useEffect(() => {
    if (!isOpen || !isTopLayer) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
        return;
      }

      if (event.key !== "Tab") {
        return;
      }

      const trapRoot = getFocusTrapRoot(focusRef.current);
      if (!trapRoot) {
        return;
      }

      const focusableElements = getFocusableElements(trapRoot);
      if (focusableElements.length === 0) {
        event.preventDefault();
        trapRoot.focus();
        return;
      }

      const firstElement = focusableElements[0];
      const lastElement = focusableElements[focusableElements.length - 1];
      const activeElement =
        document.activeElement instanceof HTMLElement ? document.activeElement : null;
      const activeElementIndex = activeElement
        ? focusableElements.indexOf(activeElement)
        : -1;

      if (event.shiftKey) {
        if (activeElementIndex <= 0) {
          event.preventDefault();
          lastElement.focus();
        }
        return;
      }

      if (activeElementIndex === -1 || activeElementIndex === focusableElements.length - 1) {
        event.preventDefault();
        firstElement.focus();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [focusRef, isOpen, isTopLayer, onClose]);
}
