"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export default function Navbar() {
  const pathname = usePathname();

  return (
    <nav className="navbar">
      <div className="navbar-inner">
        <Link href="/" className="navbar-logo">
          <div className="logo-icon">🛡️</div>
          <span>InternShield</span>
        </Link>
        <div className="navbar-links">
          <Link
            href="/#analyze"
            className={`nav-link ${pathname === "/" ? "active" : ""}`}
          >
            🔍 Verify
          </Link>
          <Link
            href="/#education"
            className="nav-link"
          >
            📖 Learn
          </Link>
          <Link
            href="/#about"
            className="nav-link"
          >
            💡 About
          </Link>
          <Link
            href="/history"
            className={`nav-link ${pathname === "/history" ? "active" : ""}`}
          >
            📋 History
          </Link>
        </div>
      </div>
    </nav>
  );
}
