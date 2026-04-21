"use client";

export default function ProtectedError() {
  if (typeof window !== "undefined") {
    window.location.href = "/login";
  }
  return null;
}
