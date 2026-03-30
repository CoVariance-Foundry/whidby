export function Footer() {
  return (
    <footer data-section="footer" className="py-8 border-t border-gray-200 bg-white">
      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        <div className="flex flex-col md:flex-row items-center justify-between gap-4">
          {/* Logo */}
          <div className="flex items-center gap-2.5">
            <div className="w-6 h-6 rounded-md bg-dark flex items-center justify-center">
              <svg width="12" height="12" viewBox="0 0 16 16" fill="none">
                <circle cx="8" cy="8" r="6" stroke="#10B981" strokeWidth="2" />
                <circle cx="8" cy="8" r="2.5" fill="#10B981" />
              </svg>
            </div>
            <span className="font-sans font-semibold text-sm text-dark">
              Rankread
            </span>
          </div>

          {/* Links */}
          <div className="flex items-center gap-6">
            <a
              href="#"
              className="text-sm text-neutral-400 hover:text-dark transition-colors"
            >
              Privacy
            </a>
            <a
              href="#"
              className="text-sm text-neutral-400 hover:text-dark transition-colors"
            >
              Terms
            </a>
            <a
              href="#"
              className="text-sm text-neutral-400 hover:text-dark transition-colors"
            >
              Contact
            </a>
          </div>

          {/* Copyright */}
          <p className="text-sm text-neutral-400">
            &copy; {new Date().getFullYear()} Rankread. All rights reserved.
          </p>
        </div>
      </div>
    </footer>
  );
}
