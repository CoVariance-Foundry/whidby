/**
 * Type guard for post-auth redirect destinations.
 *
 * A safe `next` value must:
 * - be a non-empty string
 * - start with "/" (site-relative)
 * - NOT start with "//" (protocol-relative URLs like `//evil.com` resolve to
 *   external origins when passed to `new URL()` or the browser)
 * - NOT start with "/\\" (backslash-smuggled external URLs like `/\evil.com`
 *   also resolve to external origins)
 *
 * Pure string predicate — safe to use in edge middleware and client components.
 */
export const isSafeNext = (v: string | null | undefined): v is string =>
  !!v && v.startsWith("/") && !v.startsWith("//") && !v.startsWith("/\\");
