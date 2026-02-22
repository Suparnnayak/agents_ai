"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import ProtectedRoute from "@/components/ProtectedRoute";
import Navbar from "@/components/layout/Navbar";
import Footer from "@/components/layout/Footer";
import Container from "@/components/layout/Container";
import api from "@/lib/api";

interface SystemStatus {
  model_version: string;
  last_forecast_run: string | null;
  last_signal_update: string | null;
  hospitals_count: number;
  total_forecasts?: number;
}

const STATUS_CARDS = [
  { key: "model_version", label: "Model Version", icon: "M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" },
  { key: "last_forecast_run", label: "Last Forecast Run", icon: "M12 2v4M12 18v4M2 12h4M18 12h4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" },
  { key: "last_signal_update", label: "Last Signal Update", icon: "M12 6v6l4 2M12 2a10 10 0 100 20 10 10 0 000-20z" },
  { key: "hospitals_count", label: "Total Hospitals", icon: "M3 21h18M3 10h18M3 7l9-4 9 4M4 10v11M20 10v11M8 14v3M12 14v3M16 14v3" },
];

export default function SystemPage() {
  return (
    <ProtectedRoute>
      <SystemContent />
    </ProtectedRoute>
  );
}

function SystemContent() {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [dbHealthy, setDbHealthy] = useState<boolean | null>(null);

  useEffect(() => {
    loadStatus();
    checkDb();
  }, []);

  const loadStatus = async () => {
    try {
      const res = await api.get("/system/status");
      setStatus(res.data);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  };

  const checkDb = async () => {
    try {
      const res = await api.get("/health");
      setDbHealthy(res.data?.status === "healthy");
    } catch {
      setDbHealthy(false);
    }
  };

  const getValue = (key: string): string => {
    if (!status) return "—";
    const v = (status as unknown as Record<string, unknown>)[key];
    if (v === null || v === undefined) return "—";
    if (typeof v === "number") return v.toString();
    return String(v);
  };

  return (
    <main className="min-h-screen bg-navy grid-overlay bg-gradient-animated">
      <Navbar />

      <div className="pt-20 pb-12">
        <Container>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-8 pt-4"
          >
            <h1 className="text-3xl font-bold">
              <span className="gradient-text">System Status</span>
            </h1>
            <p className="text-slate-400 mt-1">
              Overview of the HealthFlow AI infrastructure
            </p>
          </motion.div>

          {/* DB Health Card */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="glass-card rounded-xl p-5 mb-6"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className={`w-3 h-3 rounded-full ${
                  dbHealthy === null ? "bg-slate-500 animate-pulse" :
                  dbHealthy ? "bg-emerald-500" : "bg-red-500"
                }`} />
                <div>
                  <h3 className="text-sm font-semibold">Database Health</h3>
                  <p className="text-xs text-slate-500">Neon PostgreSQL</p>
                </div>
              </div>
              <span className={`text-xs font-medium px-3 py-1 rounded-full border ${
                dbHealthy === null
                  ? "text-slate-400 bg-slate-500/10 border-slate-500/20"
                  : dbHealthy
                    ? "text-emerald-400 bg-emerald-500/10 border-emerald-500/20"
                    : "text-red-400 bg-red-500/10 border-red-500/20"
              }`}>
                {dbHealthy === null ? "Checking..." : dbHealthy ? "Healthy" : "Unreachable"}
              </span>
            </div>
          </motion.div>

          {/* Status cards */}
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {STATUS_CARDS.map((card, i) => (
              <motion.div
                key={card.key}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.15 + i * 0.05 }}
                className="glass-card-hover rounded-xl p-5"
              >
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-10 h-10 rounded-lg bg-cyan/10 border border-cyan/20 flex items-center justify-center">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-cyan">
                      <path d={card.icon} />
                    </svg>
                  </div>
                  <span className="text-xs text-slate-400 uppercase tracking-wider font-medium">
                    {card.label}
                  </span>
                </div>
                {loading ? (
                  <div className="h-7 w-24 bg-white/5 rounded animate-pulse" />
                ) : (
                  <p className="text-lg font-semibold font-mono text-slate-200 truncate">
                    {getValue(card.key)}
                  </p>
                )}
              </motion.div>
            ))}
          </div>

          {/* Architecture info */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="glass-card rounded-xl p-6 mt-6"
          >
            <h3 className="text-sm uppercase tracking-widest text-cyan mb-4 font-medium">
              Infrastructure
            </h3>
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 text-sm">
              {[
                { label: "Backend", value: "FastAPI on Vercel (Serverless)" },
                { label: "Database", value: "Neon PostgreSQL" },
                { label: "Frontend", value: "Next.js on Vercel" },
                { label: "ML Model", value: "LightGBM (retrained weekly)" },
                { label: "AI Agent", value: "Groq LLM (Llama 3.3 70B)" },
                { label: "External Data", value: "Open-Meteo (Free APIs)" },
              ].map((item) => (
                <div key={item.label} className="flex justify-between py-2 border-b border-white/5 last:border-0">
                  <span className="text-slate-400">{item.label}</span>
                  <span className="text-slate-200 font-medium">{item.value}</span>
                </div>
              ))}
            </div>
          </motion.div>
        </Container>
      </div>

      <Footer />
    </main>
  );
}

