import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Widby — AI Market Intelligence for Rank & Rent",
  description:
    "Score any niche + city for both rankability and rentability before you build a single page. AI market intelligence for rank-and-rent practitioners.",
  openGraph: {
    title: "Widby — AI Market Intelligence for Rank & Rent",
    description:
      "Score any niche + city for both rankability and rentability before you build a single page.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="font-sans antialiased">{children}</body>
    </html>
  );
}
