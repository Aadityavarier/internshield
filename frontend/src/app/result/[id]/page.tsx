"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { getResult, getCachedResult, getVerdictInfo, FullScanRecord } from "@/lib/api";
import styles from "./page.module.css";

export default function ResultPage() {
  const params = useParams();
  const scanId = params.id as string;
  const [result, setResult] = useState<FullScanRecord | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function fetchResult() {
      // Try API first (requires Supabase)
      try {
        const data = await getResult(scanId);
        setResult(data);
        setLoading(false);
        return;
      } catch {
        // API failed — try sessionStorage cache
      }

      // Fallback: check sessionStorage cache
      const cached = getCachedResult(scanId);
      if (cached) {
        setResult(cached);
      } else {
        setError("Could not load the analysis result. It may have expired or the database is not configured.");
      }
      setLoading(false);
    }
    fetchResult();
  }, [scanId]);

  if (loading) {
    return (
      <div className={styles.loadingState}>
        <div className={styles.scanAnimation}>
          <div className={styles.scanRing} />
          <div className={styles.scanLine} />
          <div className={styles.scanIcon}>🔍</div>
        </div>
        <p>Loading analysis results...</p>
      </div>
    );
  }

  if (error || !result) {
    return (
      <div className={styles.errorState}>
        <div className={styles.errorIcon}>😕</div>
        <h2>Result Not Found</h2>
        <p>{error || "This analysis result could not be found."}</p>
        <Link href="/" className="btn btn-primary">
          ← Analyze Another Letter
        </Link>
      </div>
    );
  }

  const verdictInfo = getVerdictInfo(result.verdict);
  const scorePercent = Math.round(result.confidence_score);

  return (
    <div className={styles.page}>
      <div className="container">
        {/* Header */}
        <div className={styles.header}>
          <Link href="/" className={styles.backLink}>
            ← New Analysis
          </Link>
          {result.company_name && (
            <h1 className={styles.companyName}>{result.company_name}</h1>
          )}
          <div className={styles.meta}>
            <span className={`badge ${verdictInfo.badgeClass}`}>
              {verdictInfo.emoji} {verdictInfo.label}
            </span>
            <span className={styles.metaItem}>
              📄 {result.input_type.toUpperCase()}
            </span>
            <span className={styles.metaItem}>
              ⚡ {result.processing_time_ms}ms
            </span>
          </div>
        </div>

        {/* Score Section */}
        <div className={styles.scoreSection}>
          <div className={styles.gaugeContainer}>
            <svg viewBox="0 0 200 200" className={styles.gauge}>
              {/* Background circle */}
              <circle
                cx="100"
                cy="100"
                r="85"
                fill="none"
                stroke="rgba(255,255,255,0.05)"
                strokeWidth="12"
              />
              {/* Score arc */}
              <circle
                cx="100"
                cy="100"
                r="85"
                fill="none"
                stroke={verdictInfo.color}
                strokeWidth="12"
                strokeLinecap="round"
                strokeDasharray={`${(scorePercent / 100) * 534} 534`}
                strokeDashoffset="0"
                transform="rotate(-90 100 100)"
                className={styles.gaugeArc}
                style={{
                  filter: `drop-shadow(0 0 8px ${verdictInfo.color})`,
                }}
              />
            </svg>
            <div className={styles.gaugeCenter}>
              <span
                className={styles.gaugeScore}
                style={{ color: verdictInfo.color }}
              >
                {scorePercent}
              </span>
              <span className={styles.gaugeLabel}>confidence</span>
            </div>
          </div>

          <div className={styles.verdictCard} style={{ borderColor: verdictInfo.color }}>
            <span className={styles.verdictEmoji}>{verdictInfo.emoji}</span>
            <div>
              <h2 className={styles.verdictTitle} style={{ color: verdictInfo.color }}>
                {verdictInfo.label}
              </h2>
              <p className={styles.verdictDesc}>
                {result.verdict === "likely_genuine"
                  ? "Our analysis indicates this is likely a legitimate offer letter."
                  : result.verdict === "suspicious"
                    ? "This letter has some concerning characteristics. Verify independently."
                    : "This letter shows strong indicators of being fraudulent. Exercise extreme caution."}
              </p>
            </div>
          </div>
        </div>

        {/* Dimension Scores */}
        <div className={styles.dimensions}>
          <h3 className={styles.sectionTitle}>Analysis Breakdown</h3>
          <div className={styles.dimensionGrid}>
            <DimensionCard
              title="Rule Engine"
              subtitle="Structural checks"
              icon="📐"
              score={result.dimension_scores.rules}
              color="var(--primary-400)"
            />
            <DimensionCard
              title="NLP Classifier"
              subtitle="Language analysis"
              icon="🤖"
              score={result.dimension_scores.nlp}
              color="var(--accent-400)"
            />
            <DimensionCard
              title="Entity Verification"
              subtitle="Company & contact checks"
              icon="🔎"
              score={result.dimension_scores.ner}
              color="var(--warning-400)"
            />
          </div>
        </div>

        {/* Flags */}
        {result.triggered_flags && result.triggered_flags.length > 0 && (
          <div className={styles.flagsSection}>
            <h3 className={styles.sectionTitle}>
              Red Flags Detected ({result.triggered_flags.length})
            </h3>
            <div className={styles.flagsList}>
              {result.triggered_flags.map((flag, i) => (
                <div
                  key={i}
                  className={`${styles.flagItem} ${styles[`flag_${flag.severity}`]}`}
                >
                  <span className={styles.flagSeverity}>
                    {flag.severity === "critical"
                      ? "🔴"
                      : flag.severity === "high"
                        ? "🟠"
                        : flag.severity === "medium"
                          ? "🟡"
                          : "🟢"}
                  </span>
                  <div className={styles.flagContent}>
                    <span className={styles.flagMessage}>{flag.message}</span>
                    <span className={styles.flagRule}>{flag.rule.replace(/_/g, " ")}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Next Steps */}
        {result.next_steps && result.next_steps.length > 0 && (
          <div className={styles.nextSteps}>
            <h3 className={styles.sectionTitle}>Recommended Next Steps</h3>
            <div className={styles.stepsList}>
              {result.next_steps.map((step, i) => (
                <div key={i} className={styles.stepItem}>
                  <span className={styles.stepNumber}>{i + 1}</span>
                  <p>{step}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Actions */}
        <div className={styles.actions}>
          <Link href="/" className="btn btn-primary">
            🔍 Analyze Another Letter
          </Link>
          <Link href="/history" className="btn btn-ghost">
            📋 View History
          </Link>
        </div>
      </div>
    </div>
  );
}

function DimensionCard({
  title,
  subtitle,
  icon,
  score,
  color,
}: {
  title: string;
  subtitle: string;
  icon: string;
  score: number;
  color: string;
}) {
  const percent = Math.round(score * 100);

  return (
    <div className={`glass-card ${styles.dimensionCard}`}>
      <div className={styles.dimHeader}>
        <span className={styles.dimIcon}>{icon}</span>
        <div>
          <h4 className={styles.dimTitle}>{title}</h4>
          <p className={styles.dimSubtitle}>{subtitle}</p>
        </div>
      </div>
      <div className={styles.dimScore}>
        <div className={styles.dimBar}>
          <div
            className={styles.dimBarFill}
            style={{
              width: `${percent}%`,
              background: color,
              boxShadow: `0 0 12px ${color}40`,
            }}
          />
        </div>
        <span className={styles.dimPercent} style={{ color }}>
          {percent}%
        </span>
      </div>
    </div>
  );
}
