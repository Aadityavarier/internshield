"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getHistory, getVerdictInfo, ScanRecord } from "@/lib/api";
import styles from "./page.module.css";

export default function HistoryPage() {
  const [scans, setScans] = useState<ScanRecord[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchHistory() {
      try {
        const data = await getHistory();
        setScans(data);
      } catch {
        // Silently fail — empty history is fine
      } finally {
        setLoading(false);
      }
    }
    fetchHistory();
  }, []);

  if (loading) {
    return (
      <div className={styles.loadingState}>
        <div className="spinner spinner-lg" style={{ borderTopColor: "var(--primary-500)" }} />
        <p>Loading scan history...</p>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <div className="container">
        <div className={styles.header}>
          <h1 className={styles.title}>Scan History</h1>
          <p className={styles.subtitle}>
            Your past analyses, stored locally by session. No account required.
          </p>
        </div>

        {scans.length === 0 ? (
          <div className={styles.emptyState}>
            <div className={styles.emptyIcon}>📋</div>
            <h2>No scans yet</h2>
            <p>
              Your analysis history will appear here. Scan results are linked to
              your browser session. 
            </p>
            <Link href="/" className="btn btn-primary">
              🔍 Analyze Your First Letter
            </Link>
          </div>
        ) : (
          <div className={styles.tableWrapper}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Company</th>
                  <th>Type</th>
                  <th>Score</th>
                  <th>Verdict</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {scans.map((scan) => {
                  const verdictInfo = getVerdictInfo(scan.verdict);
                  return (
                    <tr key={scan.id} className={styles.row}>
                      <td className={styles.dateCell}>
                        {new Date(scan.created_at).toLocaleDateString("en-IN", {
                          day: "numeric",
                          month: "short",
                          year: "numeric",
                        })}
                        <span className={styles.time}>
                          {new Date(scan.created_at).toLocaleTimeString(
                            "en-IN",
                            {
                              hour: "2-digit",
                              minute: "2-digit",
                            }
                          )}
                        </span>
                      </td>
                      <td className={styles.companyCell}>
                        {scan.company_name || (
                          <span className={styles.unknown}>Unknown</span>
                        )}
                      </td>
                      <td>
                        <span className={styles.typeBadge}>
                          {scan.input_type === "pdf"
                            ? "📑"
                            : scan.input_type === "image"
                              ? "🖼️"
                              : "✏️"}{" "}
                          {scan.input_type.toUpperCase()}
                        </span>
                      </td>
                      <td>
                        <span
                          className={styles.scoreValue}
                          style={{ color: verdictInfo.color }}
                        >
                          {Math.round(scan.confidence_score)}%
                        </span>
                      </td>
                      <td>
                        <span className={`badge ${verdictInfo.badgeClass}`}>
                          {verdictInfo.emoji} {verdictInfo.label}
                        </span>
                      </td>
                      <td>
                        <Link
                          href={`/result/${scan.id}`}
                          className={styles.viewLink}
                        >
                          View →
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
