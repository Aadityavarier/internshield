"use client";

import Link from "next/link";

export default function Footer() {
  return (
    <footer className="footer">
      <div className="footer-inner">
        <div className="footer-grid">
          {/* Brand */}
          <div className="footer-brand">
            <div className="footer-logo">
              <div className="logo-icon">🛡️</div>
              <span>InternShield</span>
            </div>
            <p className="footer-tagline">
              Protecting students from fake internship and job offer scams.
              Upload, verify, and stay safe — completely free.
            </p>
          </div>

          {/* Quick Links */}
          <div className="footer-column">
            <h4>Quick Links</h4>
            <ul>
              <li><Link href="/#analyze">Verify Offer Letter</Link></li>
              <li><Link href="/history">Scan History</Link></li>
              <li><Link href="/#education">Learn About Scams</Link></li>
              <li><Link href="/#about">About Us</Link></li>
            </ul>
          </div>

          {/* Resources */}
          <div className="footer-column">
            <h4>Resources</h4>
            <ul>
              <li><a href="https://cybercrime.gov.in" target="_blank" rel="noopener noreferrer">Cyber Crime Portal</a></li>
              <li><a href="https://www.mca.gov.in" target="_blank" rel="noopener noreferrer">MCA Company Search</a></li>
              <li><a href="https://www.glassdoor.co.in" target="_blank" rel="noopener noreferrer">Glassdoor Reviews</a></li>
              <li><a href="https://www.ambitionbox.com" target="_blank" rel="noopener noreferrer">AmbitionBox</a></li>
            </ul>
          </div>

          {/* Legal */}
          <div className="footer-column">
            <h4>Important</h4>
            <ul>
              <li><span className="footer-note">No data stored permanently</span></li>
              <li><span className="footer-note">No signup required</span></li>
              <li><span className="footer-note">Open source project</span></li>
            </ul>
          </div>
        </div>

        {/* Divider */}
        <div className="footer-divider" />

        {/* Bottom Bar */}
        <div className="footer-bottom">
          <p className="footer-disclaimer">
            ⚠️ <strong>Disclaimer:</strong> InternShield provides automated analysis and should not be treated as legal advice.
            Always independently verify offers through official channels. If you suspect fraud,
            report it at <a href="https://cybercrime.gov.in" target="_blank" rel="noopener noreferrer">cybercrime.gov.in</a>.
          </p>
          <p className="footer-copyright">
            © {new Date().getFullYear()} InternShield. Built to protect students.
          </p>
        </div>
      </div>
    </footer>
  );
}
