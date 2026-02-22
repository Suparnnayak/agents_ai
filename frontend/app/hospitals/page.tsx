"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import ProtectedRoute from "@/components/ProtectedRoute";
import Navbar from "@/components/layout/Navbar";
import Footer from "@/components/layout/Footer";
import Container from "@/components/layout/Container";
import api from "@/lib/api";

interface HospitalRow {
  hospital_id: string;
  name: string | null;
  region: string | null;
  capacity: number | null;
}

export default function HospitalsPage() {
  return (
    <ProtectedRoute>
      <HospitalsContent />
    </ProtectedRoute>
  );
}

function HospitalsContent() {
  const router = useRouter();
  const [hospitals, setHospitals] = useState<HospitalRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  useEffect(() => {
    loadHospitals();
  }, []);

  const loadHospitals = async () => {
    try {
      const res = await api.get("/hospitals");
      const ids: string[] = res.data.hospitals || [];
      // Map to full objects — the /hospitals endpoint returns IDs only
      const rows: HospitalRow[] = ids.map((id) => ({
        hospital_id: id,
        name: id.replace("_", " "),
        region: null,
        capacity: null,
      }));
      setHospitals(rows);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  };

  const filtered = hospitals.filter((h) =>
    h.hospital_id.toLowerCase().includes(search.toLowerCase())
  );

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
              <span className="gradient-text">Hospitals</span>
            </h1>
            <p className="text-slate-400 mt-1">
              Select a hospital to view its forecast dashboard
            </p>
          </motion.div>

          {/* Search */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="mb-6"
          >
            <input
              type="text"
              placeholder="Search hospitals..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="input-field max-w-md"
            />
          </motion.div>

          {/* Table */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="glass-card rounded-xl overflow-hidden"
          >
            {loading ? (
              <div className="p-8 space-y-3">
                {[...Array(5)].map((_, i) => (
                  <div key={i} className="h-12 bg-white/5 rounded-lg animate-pulse" />
                ))}
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-white/5">
                      <th className="px-6 py-4 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                        Hospital ID
                      </th>
                      <th className="px-6 py-4 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                        Name
                      </th>
                      <th className="px-6 py-4 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                        Region
                      </th>
                      <th className="px-6 py-4 text-right text-xs font-medium text-slate-400 uppercase tracking-wider">
                        Capacity
                      </th>
                      <th className="px-6 py-4 text-right text-xs font-medium text-slate-400 uppercase tracking-wider">
                        Action
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {filtered.map((h, i) => (
                      <motion.tr
                        key={h.hospital_id}
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: i * 0.03 }}
                        onClick={() => router.push(`/dashboard?hospital=${h.hospital_id}`)}
                        className="border-b border-white/[0.03] hover:bg-white/[0.03] transition-colors cursor-pointer group"
                      >
                        <td className="px-6 py-4">
                          <span className="text-sm font-mono text-cyan">{h.hospital_id}</span>
                        </td>
                        <td className="px-6 py-4 text-sm text-slate-200">{h.name || "—"}</td>
                        <td className="px-6 py-4 text-sm text-slate-400">{h.region || "—"}</td>
                        <td className="px-6 py-4 text-sm text-right text-slate-400 font-mono">
                          {h.capacity ?? "—"}
                        </td>
                        <td className="px-6 py-4 text-right">
                          <span className="text-xs text-cyan opacity-0 group-hover:opacity-100 transition-opacity">
                            View Dashboard →
                          </span>
                        </td>
                      </motion.tr>
                    ))}
                  </tbody>
                </table>

                {filtered.length === 0 && (
                  <div className="p-8 text-center text-slate-500 text-sm">
                    No hospitals found
                  </div>
                )}
              </div>
            )}
          </motion.div>
        </Container>
      </div>

      <Footer />
    </main>
  );
}

