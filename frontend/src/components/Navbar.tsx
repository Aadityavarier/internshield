"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, useEffect } from "react";

export default function Navbar() {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);

  // Close menu when route changes
  useEffect(() => {
    setMenuOpen(false);
  }, [pathname]);

  // Close menu when clicking a hash link (same-page scroll)
  const handleLinkClick = () => {
    setMenuOpen(false);
  };

  // Prevent body scroll when menu is open
  useEffect(() => {
    if (menuOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [menuOpen]);

  return (
    <nav className="navbar">
      <div className="navbar-inner">
        <Link href="/" className="navbar-logo">
          <div className="logo-icon">🛡️</div>
          <span>InternShield</span>
        </Link>

        {/* Hamburger button — only visible on mobile */}
        <button
          className={`hamburger ${menuOpen ? "open" : ""}`}
          onClick={() => setMenuOpen(!menuOpen)}
          aria-label="Toggle navigation menu"
          aria-expanded={menuOpen}
        >
          <span className="hamburger-line" />
          <span className="hamburger-line" />
          <span className="hamburger-line" />
        </button>

        {/* Navigation links */}
        <div className={`navbar-links ${menuOpen ? "navbar-links--open" : ""}`}>
          <Link
            href="/#analyze"
            className={`nav-link ${pathname === "/" ? "active" : ""}`}
            onClick={handleLinkClick}
          >
            🔍 Verify
          </Link>
          <Link
            href="/#education"
            className="nav-link"
            onClick={handleLinkClick}
          >
            📖 Learn
          </Link>
          <Link
            href="/#about"
            className="nav-link"
            onClick={handleLinkClick}
          >
            💡 About
          </Link>
          <Link
            href="/history"
            className={`nav-link ${pathname === "/history" ? "active" : ""}`}
            onClick={handleLinkClick}
          >
            📋 History
          </Link>
        </div>

        {/* Overlay backdrop for mobile menu */}
        {menuOpen && (
          <div
            className="navbar-overlay"
            onClick={() => setMenuOpen(false)}
          />
        )}
      </div>
    </nav>
  );
}
