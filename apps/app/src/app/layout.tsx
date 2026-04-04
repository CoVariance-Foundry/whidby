export const metadata = {
  title: "Widby — Eval Dashboard",
  description: "Internal evaluation dashboard for Widby module testing",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
