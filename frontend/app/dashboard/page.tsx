"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import ProtectedRoute from "@/components/ProtectedRoute";
import Navbar from "@/components/Navbar";
import HospitalSelector from "@/components/HospitalSelector";
import ForecastChart from "@/components/ForecastChart";
import ForecastTable from "@/components/ForecastTable";
import api, { getApiErrorMessage } from "@/lib/api";
import { getUser } from "@/lib/auth";

interface ForecastResult {
  hospital_id: string;
  horizon: number;
  prediction: number;
}

export default function DashboardPage() {
  return (
    <ProtectedRoute>
      <DashboardContent />
    </ProtectedRoute>
  );
}

function DashboardContent() {
  const [hospitals, setHospitals] = useState<string[]>([]);
  const [selectedHospitals, setSelectedHospitals] = useState<string[]>([]);
  const [selectedHorizons, setSelectedHorizons] = useState<number[]>([1, 2, 3, 4, 5, 6, 7]);
  const [forecasts, setForecasts] = useState<ForecastResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [user, setUser] = useState<{ email: string; name?: string } | null>(null);

  useEffect(() => {
    setUser(getUser());
    loadHospitals();
  }, []);

  const loadHospitals = async () => {
    try {
      const res = await api.get("/hospitals");
      setHospitals(res.data.hospitals || []);
    } catch (err) {
      console.error("Failed to load hospitals:", err);
    }
  };

  const handleGenerate = async () => {
    if (selectedHospitals.length === 0) {
      setError("Please select at least one hospital");
      return;
    }
    if (selectedHorizons.length === 0) {
      setError("Please select at least one horizon");
      return;
    }

    setError("");
    setLoading(true);

    try {
      const res = await api.post("/predict", {
        hospital_ids: selectedHospitals,
        horizons: selectedHorizons,
      });
      setForecasts(res.data.forecasts || []);
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, "Failed to generate forecast"));
    } finally {
      setLoading(false);
    }
  };

  const exportCSV = () => {
    if (forecasts.length === 0) return;
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
    <main className="min-h-screen bg-navy grid-overlay">
      <Navbar />
      <div className="max-w-7xl mx-auto px-6 md:px-12 py-24">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <h1 className="text-3xl md:text-4xl font-bold mb-2">
            Welcome back, <span className="gradient-text">{user?.name || user?.email}</span>
          </h1>
          <p className="text-slate-400">Generate 7-day hospital admission forecasts</p>
        </motion.div>

        <div className="grid lg:grid-cols-3 gap-6 mb-8">
          <div className="lg:col-span-1 space-y-6">
            <HospitalSelector
              hospitals={hospitals}
              selected={selectedHospitals}
              onChange={setSelectedHospitals}
            />

            <div>
              <label className="block text-xs uppercase tracking-widest text-cyan mb-2 font-medium">
                Select Horizons
              </label>
              <div className="glass-card rounded-lg p-4 space-y-2">
                {[1, 2, 3, 4, 5, 6, 7].map((h) => (
                  <label
                    key={h}
                    className="flex items-center gap-3 cursor-pointer hover:bg-white/5 p-2 rounded-lg transition-colors"
                  >
                    <input
                      type="checkbox"
                      checked={selectedHorizons.includes(h)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedHorizons([...selectedHorizons, h]);
                        } else {
                          setSelectedHorizons(selectedHorizons.filter((x) => x !== h));
                        }
                      }}
                      className="w-4 h-4 rounded border-2 border-slate-500 text-cyan focus:ring-cyan/50"
                    />
                    <span className="text-sm text-slate-300">Day {h}</span>
                  </label>
                ))}
              </div>
            </div>

            <button
              onClick={handleGenerate}
              disabled={loading || selectedHospitals.length === 0}
              className="w-full px-4 py-3 bg-gradient-to-r from-cyan to-blue-600 text-white font-medium rounded-lg hover:shadow-lg hover:shadow-cyan/25 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <span className="inline-flex items-center gap-2">
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
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
          </div>

          <div className="lg:col-span-2">
            {forecasts.length > 0 && (
              <>
                <div className="mb-6 flex items-center justify-between">
                  <h2 className="text-xl font-semibold">Forecast Results</h2>
                  <button
                    onClick={exportCSV}
                    className="px-4 py-2 text-sm font-medium glass-card rounded-lg hover:border-cyan/30 transition-all"
                  >
                    Export CSV
                  </button>
                </div>
                <ForecastChart data={forecasts} />
              </>
            )}
          </div>
        </div>

        {forecasts.length > 0 && (
          <div className="mt-8">
            <ForecastTable data={forecasts} />
          </div>
        )}
      </div>
    </main>
  );
}

