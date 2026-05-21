import Link from "next/link";

export default function Footer() {
  return (
    <footer className="app-footer" aria-label="Product footer">
      <div className="app-footer-inner">
        <div className="app-footer-status">
          <span className="app-footer-dot" aria-hidden="true" />
          <span>App workspace</span>
        </div>
        <nav className="app-footer-links" aria-label="Footer links">
          <Link href="/explore">Explore</Link>
          <Link href="/strategies">Strategies</Link>
          <Link href="/reports">Reports</Link>
          <Link href="/settings">Settings</Link>
        </nav>
        <div className="app-footer-copy">Widby market discovery</div>
      </div>
    </footer>
  );
}
