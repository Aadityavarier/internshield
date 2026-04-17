"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { analyzeDocument } from "@/lib/api";
import styles from "./page.module.css";

export default function HomePage() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [text, setText] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [companyWebsite, setCompanyWebsite] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  const [mode, setMode] = useState<"upload" | "details">("details");
  const [isDragging, setIsDragging] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState("");

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      setFile(droppedFile);
      setError("");
    }
  }, []);

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    if (selected) {
      if (selected.size > 10 * 1024 * 1024) {
        setError("File size must be under 10MB.");
        return;
      }
      setFile(selected);
      setError("");
    }
  };

  const handleAnalyze = async () => {
    setError("");

    if (mode === "upload" && !file) {
      setError("Please upload a file first.");
      return;
    }
    if (mode === "details" && !text.trim()) {
      setError("Please paste the offer letter text.");
      return;
    }

    setIsAnalyzing(true);
    try {
      const res = await analyzeDocument(
        mode === "upload" ? file : null,
        mode === "details" ? text : null,
        { companyName, companyWebsite, contactEmail }
      );
      router.push(`/result/${res.id}`);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Analysis failed. Please try again."
      );
    } finally {
      setIsAnalyzing(false);
    }
  };

  const removeFile = () => {
    setFile(null);
    setError("");
  };

  const getFileIcon = (f: File) => {
    if (f.type === "application/pdf") return "📑";
    if (f.type.startsWith("image/")) return "🖼️";
    if (f.name.endsWith(".docx") || f.name.endsWith(".doc")) return "📄";
    return "📎";
  };

  return (
    <div className={styles.page}>
      {/* ===== HERO SECTION ===== */}
      <section className={styles.hero}>
        <div className={styles.heroGlow} />
        <div className="container">
          <div className={styles.heroContent}>
            <div className={styles.heroBadge}>
              <span>🛡️</span> Protecting Students from Internship Fraud
            </div>
            <h1 className={styles.heroTitle}>
              Don&apos;t Fall for{" "}
              <span className="gradient-text">Fake Offers.</span>
            </h1>
            <p className={styles.heroSubtitle}>
              Every year, thousands of students in India lose money and personal
              information to fraudulent internship offers. InternShield helps you
              verify any offer letter in seconds — completely free.
            </p>
            <a href="#analyze" className={`btn btn-primary btn-lg ${styles.heroCta}`}>
              Check Your Offer Letter ↓
            </a>

            {/* Stats */}
            <div className={styles.stats}>
              <div className={styles.statItem}>
                <span className={styles.statNumber}>73%</span>
                <span className={styles.statLabel}>of fake offers target students</span>
              </div>
              <div className={styles.statDivider} />
              <div className={styles.statItem}>
                <span className={styles.statNumber}>₹200Cr+</span>
                <span className={styles.statLabel}>lost to job scams in India</span>
              </div>
              <div className={styles.statDivider} />
              <div className={styles.statItem}>
                <span className={styles.statNumber}>8-Point</span>
                <span className={styles.statLabel}>verification system</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ===== ANALYZE SECTION ===== */}
      <section id="analyze" className={styles.analyzeSection}>
        <div className="container">
          <div className={styles.sectionHeader}>
            <h2>Verify Your Offer Letter</h2>
            <p>Upload a document or enter the details below. Our AI will analyze it across 8 dimensions of legitimacy.</p>
          </div>

          <div className={styles.uploadCard}>
            {/* Mode Toggle */}
            <div className={styles.modeToggle}>
              <button
                className={`${styles.modeBtn} ${mode === "details" ? styles.modeBtnActive : ""}`}
                onClick={() => setMode("details")}
              >
                ✏️ Enter Details
              </button>
              <button
                className={`${styles.modeBtn} ${mode === "upload" ? styles.modeBtnActive : ""}`}
                onClick={() => setMode("upload")}
              >
                📁 Upload File
              </button>
            </div>

            {/* Details Mode */}
            {mode === "details" && (
              <div className={styles.detailsForm}>
                <div className={styles.formRow}>
                  <div className={styles.formGroup}>
                    <label htmlFor="company-name">Company Name</label>
                    <input
                      id="company-name"
                      type="text"
                      placeholder="e.g., Infosys, TCS, Unknown Corp..."
                      value={companyName}
                      onChange={(e) => setCompanyName(e.target.value)}
                      className={styles.formInput}
                    />
                  </div>
                  <div className={styles.formGroup}>
                    <label htmlFor="company-website">Company Website</label>
                    <input
                      id="company-website"
                      type="url"
                      placeholder="e.g., https://company.com"
                      value={companyWebsite}
                      onChange={(e) => setCompanyWebsite(e.target.value)}
                      className={styles.formInput}
                    />
                  </div>
                </div>
                <div className={styles.formGroup}>
                  <label htmlFor="contact-email">Contact Email (from the letter)</label>
                  <input
                    id="contact-email"
                    type="email"
                    placeholder="e.g., hr@company.com or recruiter@gmail.com"
                    value={contactEmail}
                    onChange={(e) => setContactEmail(e.target.value)}
                    className={styles.formInput}
                  />
                </div>
                <div className={styles.formGroup}>
                  <label htmlFor="offer-text">
                    Offer Letter Text <span className={styles.required}>*</span>
                  </label>
                  <textarea
                    id="offer-text"
                    className={styles.textarea}
                    placeholder={"Paste the complete text of the offer letter here...\n\nInclude everything — company name, role, stipend, dates, terms, signatures — the more detail, the better our analysis."}
                    value={text}
                    onChange={(e) => {
                      setText(e.target.value);
                      setError("");
                    }}
                    rows={10}
                  />
                  {text && (
                    <div className={styles.charCount}>
                      {text.length.toLocaleString()} characters
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Upload Mode */}
            {mode === "upload" && (
              <>
                {/* Company details for upload mode too */}
                <div className={styles.formRow} style={{ marginBottom: 16 }}>
                  <div className={styles.formGroup}>
                    <label htmlFor="company-name-upload">Company Name (optional)</label>
                    <input
                      id="company-name-upload"
                      type="text"
                      placeholder="e.g., Infosys, TCS..."
                      value={companyName}
                      onChange={(e) => setCompanyName(e.target.value)}
                      className={styles.formInput}
                    />
                  </div>
                  <div className={styles.formGroup}>
                    <label htmlFor="contact-email-upload">Contact Email (optional)</label>
                    <input
                      id="contact-email-upload"
                      type="email"
                      placeholder="e.g., hr@company.com"
                      value={contactEmail}
                      onChange={(e) => setContactEmail(e.target.value)}
                      className={styles.formInput}
                    />
                  </div>
                </div>

                <div
                  className={`${styles.dropzone} ${isDragging ? styles.dropzoneActive : ""} ${file ? styles.dropzoneHasFile : ""}`}
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                  onClick={() =>
                    !file && document.getElementById("file-input")?.click()
                  }
                >
                  <input
                    id="file-input"
                    type="file"
                    accept=".pdf,.jpg,.jpeg,.png,.bmp,.webp,.tiff,.docx,.doc,.txt,.rtf"
                    onChange={handleFileInput}
                    className={styles.hiddenInput}
                  />

                  {file ? (
                    <div className={styles.filePreview}>
                      <div className={styles.fileIcon}>{getFileIcon(file)}</div>
                      <div className={styles.fileInfo}>
                        <span className={styles.fileName}>{file.name}</span>
                        <span className={styles.fileSize}>
                          {(file.size / 1024).toFixed(1)} KB
                        </span>
                      </div>
                      <button
                        className={styles.removeFile}
                        onClick={(e) => {
                          e.stopPropagation();
                          removeFile();
                        }}
                      >
                        ✕
                      </button>
                    </div>
                  ) : (
                    <div className={styles.dropzoneContent}>
                      <div className={styles.dropzoneIcon}>
                        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                          <polyline points="17,8 12,3 7,8" />
                          <line x1="12" y1="3" x2="12" y2="15" />
                        </svg>
                      </div>
                      <p className={styles.dropzoneTitle}>Drop your offer letter here</p>
                      <p className={styles.dropzoneHint}>
                        or click to browse • PDF, DOCX, Images, TXT up to 10MB
                      </p>
                    </div>
                  )}
                </div>
              </>
            )}

            {/* Error */}
            {error && (
              <div className={styles.error}>
                <span>⚠️</span> {error}
              </div>
            )}

            {/* Analyze Button */}
            <button
              className={`btn btn-primary btn-lg ${styles.analyzeBtn}`}
              onClick={handleAnalyze}
              disabled={
                isAnalyzing ||
                (mode === "upload" && !file) ||
                (mode === "details" && !text.trim())
              }
            >
              {isAnalyzing ? (
                <>
                  <div className="spinner" />
                  <span>Analyzing...</span>
                </>
              ) : (
                <>
                  <span>🔍</span>
                  <span>Analyze Letter</span>
                </>
              )}
            </button>
          </div>
        </div>
      </section>

      {/* ===== HOW IT WORKS ===== */}
      <section className={styles.howSection}>
        <div className="container">
          <div className={styles.sectionHeader}>
            <h2>How It Works</h2>
            <p>Three simple steps to verify any offer letter</p>
          </div>
          <div className={styles.stepsGrid}>
            <div className={styles.step}>
              <div className={styles.stepNumber}>1</div>
              <div className={styles.stepIcon}>📤</div>
              <h3>Upload or Paste</h3>
              <p>Upload your offer letter as PDF, DOCX, image — or paste the text directly along with company details.</p>
            </div>
            <div className={styles.stepConnector}>→</div>
            <div className={styles.step}>
              <div className={styles.stepNumber}>2</div>
              <div className={styles.stepIcon}>🤖</div>
              <h3>AI Analyzes</h3>
              <p>Our engine runs 8 rule-based checks, language pattern analysis, and entity verification simultaneously.</p>
            </div>
            <div className={styles.stepConnector}>→</div>
            <div className={styles.step}>
              <div className={styles.stepNumber}>3</div>
              <div className={styles.stepIcon}>📊</div>
              <h3>Get Report</h3>
              <p>Receive a detailed breakdown with confidence score, red flags, and actionable next steps in seconds.</p>
            </div>
          </div>
        </div>
      </section>

      {/* ===== EDUCATION SECTION ===== */}
      <section id="education" className={styles.educationSection}>
        <div className="container">
          <div className={styles.sectionHeader}>
            <h2>How to Spot a Fake Offer Letter</h2>
            <p>Learn the key differences between legitimate and fraudulent internship offers</p>
          </div>

          <div className={styles.comparisonGrid}>
            {/* FAKE column */}
            <div className={`${styles.comparisonCard} ${styles.fakeCard}`}>
              <div className={styles.comparisonHeader}>
                <span className={styles.comparisonIcon}>🚨</span>
                <h3>Signs of a <span style={{ color: "var(--danger-400)" }}>FAKE</span> Offer</h3>
              </div>
              <ul className={styles.comparisonList}>
                <li>
                  <span className={styles.flagDot} style={{ background: "var(--danger-500)" }} />
                  <div>
                    <strong>Personal email domain</strong>
                    <p>Uses gmail.com, yahoo.com instead of a corporate email</p>
                  </div>
                </li>
                <li>
                  <span className={styles.flagDot} style={{ background: "var(--danger-500)" }} />
                  <div>
                    <strong>Demands upfront payment</strong>
                    <p>Asks for &quot;registration fee,&quot; &quot;security deposit,&quot; or &quot;training charges&quot;</p>
                  </div>
                </li>
                <li>
                  <span className={styles.flagDot} style={{ background: "var(--danger-500)" }} />
                  <div>
                    <strong>Generic greeting</strong>
                    <p>&quot;Dear Candidate&quot; or &quot;Dear Student&quot; instead of your name</p>
                  </div>
                </li>
                <li>
                  <span className={styles.flagDot} style={{ background: "var(--danger-500)" }} />
                  <div>
                    <strong>No company registration</strong>
                    <p>Missing CIN number, registered address, or official letterhead</p>
                  </div>
                </li>
                <li>
                  <span className={styles.flagDot} style={{ background: "var(--danger-500)" }} />
                  <div>
                    <strong>Urgency tactics</strong>
                    <p>&quot;Respond in 24 hours,&quot; &quot;Limited slots,&quot; &quot;Seats filling fast&quot;</p>
                  </div>
                </li>
                <li>
                  <span className={styles.flagDot} style={{ background: "var(--danger-500)" }} />
                  <div>
                    <strong>WhatsApp / Telegram for HR</strong>
                    <p>Official communication via personal messaging apps</p>
                  </div>
                </li>
              </ul>
            </div>

            {/* GENUINE column */}
            <div className={`${styles.comparisonCard} ${styles.genuineCard}`}>
              <div className={styles.comparisonHeader}>
                <span className={styles.comparisonIcon}>✅</span>
                <h3>Signs of a <span style={{ color: "var(--accent-400)" }}>GENUINE</span> Offer</h3>
              </div>
              <ul className={styles.comparisonList}>
                <li>
                  <span className={styles.flagDot} style={{ background: "var(--accent-500)" }} />
                  <div>
                    <strong>Corporate email domain</strong>
                    <p>Uses @company.com or @companyname.co.in</p>
                  </div>
                </li>
                <li>
                  <span className={styles.flagDot} style={{ background: "var(--accent-500)" }} />
                  <div>
                    <strong>No upfront payment required</strong>
                    <p>Legitimate companies never charge candidates to join</p>
                  </div>
                </li>
                <li>
                  <span className={styles.flagDot} style={{ background: "var(--accent-500)" }} />
                  <div>
                    <strong>Personalized greeting</strong>
                    <p>Addresses you by your full name</p>
                  </div>
                </li>
                <li>
                  <span className={styles.flagDot} style={{ background: "var(--accent-500)" }} />
                  <div>
                    <strong>Company CIN &amp; registered address</strong>
                    <p>Includes verifiable company registration details</p>
                  </div>
                </li>
                <li>
                  <span className={styles.flagDot} style={{ background: "var(--accent-500)" }} />
                  <div>
                    <strong>Reasonable deadline</strong>
                    <p>Gives you adequate time (7–15 days) to respond</p>
                  </div>
                </li>
                <li>
                  <span className={styles.flagDot} style={{ background: "var(--accent-500)" }} />
                  <div>
                    <strong>Official HR contact</strong>
                    <p>Named HR person with designation, email, and phone</p>
                  </div>
                </li>
              </ul>
            </div>
          </div>

          {/* Quick Tips */}
          <div className={styles.tipsCard}>
            <h3>🔑 Golden Rule</h3>
            <p className={styles.goldenRule}>
              <strong>If a company asks you to pay money to get an internship — it&apos;s a scam. Period.</strong> No legitimate company
              charges registration fees, security deposits, or training costs from interns. If you receive such an offer, report it
              immediately to your college placement cell and the{" "}
              <a href="https://cybercrime.gov.in" target="_blank" rel="noopener noreferrer">National Cyber Crime Portal</a>.
            </p>
          </div>
        </div>
      </section>

      {/* ===== ABOUT SECTION ===== */}
      <section id="about" className={styles.aboutSection}>
        <div className="container">
          <div className={styles.sectionHeader}>
            <h2>About InternShield</h2>
            <p>Why we built this and what problem we&apos;re solving</p>
          </div>

          <div className={styles.aboutGrid}>
            <div className={`glass-card ${styles.aboutCard}`}>
              <div className={styles.aboutIcon}>🎯</div>
              <h3>Our Mission</h3>
              <p>
                InternShield was created with a simple mission: <strong>no student should lose money or personal data to a fake
                internship offer.</strong> We provide a free, anonymous tool that anyone can use to verify an offer letter before
                committing to it.
              </p>
            </div>
            <div className={`glass-card ${styles.aboutCard}`}>
              <div className={styles.aboutIcon}>📢</div>
              <h3>The Problem</h3>
              <p>
                With the rise of remote work and online recruitment, fake offer letters have become increasingly sophisticated.
                Scammers impersonate real companies, create convincing letterheads, and pressure students into paying
                &quot;registration fees&quot; or sharing sensitive documents like Aadhaar and PAN cards.
              </p>
            </div>
            <div className={`glass-card ${styles.aboutCard}`}>
              <div className={styles.aboutIcon}>⚙️</div>
              <h3>How We Help</h3>
              <p>
                Our analysis engine combines <strong>8 rule-based structural checks</strong>, <strong>NLP language pattern
                analysis</strong>, and <strong>named entity verification</strong> to score any offer letter across multiple
                dimensions. The result is a clear, actionable report — no signup required, no data stored permanently.
              </p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
