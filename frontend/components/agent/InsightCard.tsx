"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import api, { getApiErrorMessage } from "@/lib/api";

interface InsightCardProps {
  hospitalCode: string;
}

export default function InsightCard({ hospitalCode }: InsightCardProps) {
  const [analysis, setAnalysis] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [inferenceTime, setInferenceTime] = useState<number | null>(null);

  const fetchInsight = async () => {
    setLoading(true);
    setError("");
    setAnalysis("");
    setInferenceTime(null);

    try {
      const res = await api.post("/agent/query", {
        question: `Analyze the forecast trend and provide recommendations for ${hospitalCode}. What should the hospital prepare for this week?`,
      });
      setAnalysis(res.data.analysis);
      setInferenceTime(res.data.inference_time_seconds);
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, "Failed to get AI analysis."));
    } finally {
      setLoading(false);
    }
  };

  const deriveRisk = (text: string): { level: string; color: string } => {
    const lower = text.toLowerCase();
    if (lower.includes("high risk") || lower.includes("surge") || lower.includes("critical") || lower.includes("unhealthy"))
      return { level: "High", color: "text-red-400 bg-red-500/10 border-red-500/20" };
    if (lower.includes("moderate") || lower.includes("monitor") || lower.includes("caution"))
      return { level: "Moderate", color: "text-amber-400 bg-amber-500/10 border-amber-500/20" };
    return { level: "Low", color: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20" };
  };

  return (
    <div className="glass-card rounded-xl p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm uppercase tracking-widest text-cyan font-medium flex items-center gap-2">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-cyan">
            <path d="M12 2a7 7 0 0 1 7 7c0 2.38-1.19 4.47-3 5.74V17a2 2 0 0 1-2 2h-4a2 2 0 0 1-2-2v-2.26C6.19 13.47 5 11.38 5 9a7 7 0 0 1 7-7z" />
            <path d="M10 21h4" />
          </svg>
          AI Insights
        </h3>
        <button
          onClick={fetchInsight}
          disabled={loading}
          className="px-3 py-1.5 text-xs font-medium btn-primary !py-1.5 !px-3 !text-xs"
        >
          {loading ? (
            <span className="inline-flex items-center gap-1.5">
              <div className="w-3 h-3 border-2 border-navy border-t-transparent rounded-full animate-spin" />
              Analyzing...
            </span>
          ) : (
            "Explain Forecast"
          )}
        </button>
      </div>

      <AnimatePresence mode="wait">
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm"
          >
            {error}
          </motion.div>
        )}

        {analysis && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
            className="space-y-3"
          >
            {/* Risk badge + time */}
            <div className="flex items-center gap-2">
              {(() => {
                const risk = deriveRisk(analysis);
                return (
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${risk.color}`}>
                    Risk: {risk.level}
                  </span>
                );
              })()}
              {inferenceTime && (
                <span className="text-xs text-slate-500">
                  {inferenceTime.toFixed(1)}s inference
                </span>
              )}
            </div>

            {/* Analysis text */}
            <div className="text-sm text-slate-300 leading-relaxed whitespace-pre-wrap">
              {analysis}
            </div>
          </motion.div>
        )}

        {!analysis && !error && !loading && (
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-sm text-slate-500 text-center py-4"
          >
            Click &quot;Explain Forecast&quot; to get AI-powered analysis for {hospitalCode}
          </motion.p>
        )}
      </AnimatePresence>
    </div>
  );
}

