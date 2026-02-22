"use client";

import { useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend, Area, AreaChart,
} from "recharts";
import ProtectedRoute from "@/components/ProtectedRoute";
import Navbar from "@/components/layout/Navbar";
import Footer from "@/components/layout/Footer";
import Container from "@/components/layout/Container";
import HospitalSelector from "@/components/HospitalSelector";
import InsightCard from "@/components/agent/InsightCard";
import api, { getApiErrorMessage } from "@/lib/api";
import { getUser } from "@/lib/auth";

/* ── Types ── */
interface ForecastResult {
  hospital_id: string;
  horizon: number;
  prediction: number;
}

interface ExternalSignal {
  date: string;
  temperature: number;
  aqi: number;
  outbreak_index: number;
  mobility_index: number;
}

/* ── Chart colors ── */
const COLORS = ["#00E5FF", "#3B82F6", "#8B5CF6", "#EC4899", "#F59E0B", "#10B981"];

/* ── Skeleton loader ── */
function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse bg-white/5 rounded-lg ${className}`} />;
}

/* ── Custom tooltip ── */
const chartTooltipStyle = {
  background: "rgba(11, 18, 32, 0.95)",
  border: "1px solid rgba(0, 229, 255, 0.15)",
  borderRadius: "0.75rem",
  color: "#F0F4F8",
  fontSize: "13px",
};

export default function DashboardPage() {
  return (
    <ProtectedRoute>
      <DashboardContent />
    </ProtectedRoute>
  );
}

function DashboardContent() {
  const searchParams = useSearchParams();
  const preselected = searchParams.get("hospital");

  const [hospitals, setHospitals] = useState<string[]>([]);
  const [selectedHospitals, setSelectedHospitals] = useState<string[]>(
    preselected ? [preselected] : []
  );
  const [forecasts, setForecasts] = useState<ForecastResult[]>([]);
  const [history, setHistory] = useState<{ date: string; admissions: number }[]>([]);
  const [signals, setSignals] = useState<ExternalSignal | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [error, setError] = useState("");
  const [user, setUser] = useState<{ email: string; name?: string } | null>(null);

  useEffect(() => {
    setUser(getUser());
    loadHospitals();
  }, []);

  useEffect(() => {
    if (preselected && hospitals.includes(preselected) && !selectedHospitals.includes(preselected)) {
      setSelectedHospitals([preselected]);
    }
  }, [preselected, hospitals]); // eslint-disable-line react-hooks/exhaustive-deps

  const loadHospitals = async () => {
    try {
      const res = await api.get("/hospitals");
      setHospitals(res.data.hospitals || []);
    } catch {
      // silent
    }
  };

  const handleGenerate = async () => {
    if (selectedHospitals.length === 0) {
      setError("Please select at least one hospital");
      return;
    }
    setError("");
    setLoading(true);
    setLoadingHistory(true);

    try {
      // Fetch forecasts
      const res = await api.post("/predict", {
        hospital_ids: selectedHospitals,
        horizons: [1, 2, 3, 4, 5, 6, 7],
      });
      setForecasts(res.data.forecasts || []);

      // Fetch admission history (for first selected hospital)
      try {
        const histRes = await api.get(`/forecast/history`, {
          params: { hospitals: selectedHospitals[0], days: 14 },
        });
        const histData = histRes.data?.history || [];
        setHistory(histData);
      } catch {
        setHistory([]);
      }

      // Fetch external signals via system status (signals embedded)
      try {
        const sysRes = await api.get("/system/status");
        if (sysRes.data?.last_signal_update) {
          setSignals({
            date: sysRes.data.last_signal_update,
            temperature: 0,
            aqi: 0,
            outbreak_index: 0,
            mobility_index: 0,
          });
        }
      } catch {
        // silent
      }
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, "Failed to generate forecast"));
    } finally {
      setLoading(false);
      setLoadingHistory(false);
    }
  };

  /* ── Chart data transforms ── */
  const forecastChartData = (() => {
    if (!forecasts.length) return [];
    const hospIds = [...new Set(forecasts.map((f) => f.hospital_id))];
    const horizons = [...new Set(forecasts.map((f) => f.horizon))].sort((a, b) => a - b);
    return horizons.map((h) => {
      const row: Record<string, number | string> = { name: `Day ${h}` };
      hospIds.forEach((hid) => {
        const m = forecasts.find((f) => f.hospital_id === hid && f.horizon === h);
        if (m) row[hid] = Math.round(m.prediction * 100) / 100;
      });
      return row;
    });
  })();

  const forecastHospitals = [...new Set(forecasts.map((f) => f.hospital_id))];

  const exportCSV = () => {
    if (!forecasts.length) return;
    const csv = [
      "Hospital ID,Horizon,Prediction",
      ...forecasts.map((f) => `${f.hospital_id},${f.horizon},${f.prediction.toFixed(2)}`),
    ].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `forecast_${new Date().toISOString().split("T")[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <main className="min-h-screen bg-navy grid-overlay bg-gradient-animated">
      <Navbar />

      <div className="pt-20 pb-12">
        <Container>
          {/* Header */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-8 pt-4"
          >
            <h1 className="text-3xl font-bold">
              Welcome back, <span className="gradient-text">{user?.name || user?.email}</span>
            </h1>
            <p className="text-slate-400 mt-1">7-day hospital admission forecasts powered by AI</p>
          </motion.div>

          {/* Control Panel */}
          <div className="grid lg:grid-cols-4 gap-6">
            {/* Left sidebar */}
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.1 }}
              className="lg:col-span-1 space-y-4"
            >
              <HospitalSelector
                hospitals={hospitals}
                selected={selectedHospitals}
                onChange={setSelectedHospitals}
              />

              <button
                onClick={handleGenerate}
                disabled={loading || selectedHospitals.length === 0}
                className="w-full btn-primary"
              >
                {loading ? (
                  <span className="inline-flex items-center gap-2">
                    <div className="w-4 h-4 border-2 border-navy border-t-transparent rounded-full animate-spin" />
                    Generating...
                  </span>
                ) : (
                  "Generate Forecast"
                )}
              </button>

              {error && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm"
                >
                  {error}
                </motion.div>
              )}

              {/* Stats summary */}
              {forecasts.length > 0 && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.3 }}
                  className="glass-card rounded-xl p-4 space-y-3"
                >
                  <h4 className="text-xs uppercase tracking-widest text-slate-400 font-medium">Summary</h4>
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-slate-400">Hospitals</span>
                      <span className="text-cyan font-mono">{forecastHospitals.length}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-slate-400">Forecast days</span>
                      <span className="text-cyan font-mono">7</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-slate-400">Avg prediction</span>
                      <span className="text-cyan font-mono">
                        {(forecasts.reduce((a, f) => a + f.prediction, 0) / forecasts.length).toFixed(1)}
                      </span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-slate-400">Peak</span>
                      <span className="text-amber-400 font-mono">
                        {Math.max(...forecasts.map((f) => f.prediction)).toFixed(1)}
                      </span>
                    </div>
                  </div>
                  <button
                    onClick={exportCSV}
                    className="w-full mt-2 btn-secondary !py-2 text-xs"
                  >
                    Export CSV
                  </button>
                </motion.div>
              )}
            </motion.div>

            {/* Main content */}
            <div className="lg:col-span-3 space-y-6">
              {/* Forecast chart */}
              {loading ? (
                <div className="glass-card rounded-xl p-6">
                  <Skeleton className="h-5 w-32 mb-4" />
                  <Skeleton className="h-72" />
                </div>
              ) : forecasts.length > 0 ? (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="glass-card rounded-xl p-6"
                >
                  <h3 className="text-sm uppercase tracking-widest text-cyan mb-4 font-medium">
                    7-Day Forecast
                  </h3>
                  <div className="h-72">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={forecastChartData} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
                        <defs>
                          {forecastHospitals.map((_, i) => (
                            <linearGradient key={i} id={`grad-${i}`} x1="0" y1="0" x2="0" y2="1">
                              <stop offset="0%" stopColor={COLORS[i % COLORS.length]} stopOpacity={0.3} />
                              <stop offset="100%" stopColor={COLORS[i % COLORS.length]} stopOpacity={0} />
                            </linearGradient>
                          ))}
                        </defs>
                        <CartesianGrid stroke="rgba(148,163,184,0.05)" />
                        <XAxis dataKey="name" stroke="#475569" fontSize={12} tickLine={false} axisLine={false} />
                        <YAxis stroke="#475569" fontSize={12} tickLine={false} axisLine={false} />
                        <Tooltip contentStyle={chartTooltipStyle} />
                        <Legend wrapperStyle={{ fontSize: "12px", color: "#94a3b8" }} />
                        {forecastHospitals.map((hid, i) => (
                          <Area
                            key={hid}
                            type="monotone"
                            dataKey={hid}
                            stroke={COLORS[i % COLORS.length]}
                            fill={`url(#grad-${i})`}
                            strokeWidth={2}
                            dot={{ r: 3, fill: COLORS[i % COLORS.length] }}
                            activeDot={{ r: 5 }}
                          />
                        ))}
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </motion.div>
              ) : null}

              {/* History chart */}
              {loadingHistory ? (
                <div className="glass-card rounded-xl p-6">
                  <Skeleton className="h-5 w-40 mb-4" />
                  <Skeleton className="h-56" />
                </div>
              ) : history.length > 0 ? (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.1 }}
                  className="glass-card rounded-xl p-6"
                >
                  <h3 className="text-sm uppercase tracking-widest text-cyan mb-4 font-medium">
                    Historical Admissions (Last 14 Days)
                  </h3>
                  <div className="h-56">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={history} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
                        <CartesianGrid stroke="rgba(148,163,184,0.05)" />
                        <XAxis dataKey="date" stroke="#475569" fontSize={11} tickLine={false} axisLine={false} />
                        <YAxis stroke="#475569" fontSize={12} tickLine={false} axisLine={false} />
                        <Tooltip contentStyle={chartTooltipStyle} />
                        <Bar dataKey="admissions" fill="#00E5FF" radius={[4, 4, 0, 0]} opacity={0.7} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </motion.div>
              ) : null}

              {/* External Signals + AI Insights row */}
              {forecasts.length > 0 && (
                <div className="grid md:grid-cols-2 gap-6">
                  {/* External signals */}
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2 }}
                    className="glass-card rounded-xl p-5"
                  >
                    <h3 className="text-sm uppercase tracking-widest text-cyan mb-4 font-medium flex items-center gap-2">
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-cyan">
                        <circle cx="12" cy="12" r="10" />
                        <path d="M12 6v6l4 2" />
                      </svg>
                      External Signals
                    </h3>
                    {signals ? (
                      <div className="space-y-2.5 text-sm">
                        <div className="flex justify-between"><span className="text-slate-400">Signal Date</span><span className="font-mono text-slate-200">{signals.date}</span></div>
                        <div className="flex justify-between"><span className="text-slate-400">Status</span><span className="badge-success">Active</span></div>
                      </div>
                    ) : (
                      <div className="space-y-2.5 text-sm">
                        <div className="flex justify-between"><span className="text-slate-400">Status</span><span className="badge-info">Awaiting fetch</span></div>
                        <p className="text-xs text-slate-500">
                          External signals are updated daily via GitHub Actions cron at 2:00 AM UTC.
                        </p>
                      </div>
                    )}
                  </motion.div>

                  {/* AI Insights */}
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.3 }}
                  >
                    <InsightCard hospitalCode={selectedHospitals[0]} />
                  </motion.div>
                </div>
              )}

              {/* Forecast table */}
              {forecasts.length > 0 && (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.4 }}
                  className="glass-card rounded-xl overflow-hidden"
                >
                  <div className="px-6 py-4 border-b border-white/5">
                    <h3 className="text-sm uppercase tracking-widest text-cyan font-medium">
                      Detailed Results
                    </h3>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead>
                        <tr className="border-b border-white/5">
                          <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">Hospital</th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">Horizon</th>
                          <th className="px-6 py-3 text-right text-xs font-medium text-slate-400 uppercase tracking-wider">Predicted Admissions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {forecasts.map((row) => (
                          <tr
                            key={`${row.hospital_id}-${row.horizon}`}
                            className="border-b border-white/[0.03] hover:bg-white/[0.02] transition-colors"
                          >
                            <td className="px-6 py-3 text-sm text-slate-200 font-medium">{row.hospital_id}</td>
                            <td className="px-6 py-3 text-sm">
                              <span className="badge-info">Day {row.horizon}</span>
                            </td>
                            <td className="px-6 py-3 text-sm text-right font-mono text-cyan">
                              {row.prediction.toFixed(2)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </motion.div>
              )}
            </div>
          </div>
        </Container>
      </div>

      <Footer />
    </main>
  );
}
