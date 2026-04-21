import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Widby Dev Suite",
  description: "Internal research agent dashboard for scoring engine improvement",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="bg-[var(--color-dark)] text-[var(--color-text-primary)]">
        {children}
      </body>
    </html>
  );
}
