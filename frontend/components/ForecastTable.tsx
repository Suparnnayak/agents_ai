"use client";

import { motion } from "framer-motion";

interface ForecastResult {
  hospital_id: string;
  horizon: number;
  prediction: number;
}

interface Props {
  data: ForecastResult[];
}

export default function ForecastTable({ data }: Props) {
  if (!data || data.length === 0) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, delay: 0.3 }}
      className="glass-card rounded-xl overflow-hidden"
    >
      <div className="px-6 py-4 border-b border-white/5">
        <h3 className="text-sm uppercase tracking-widest text-cyan font-medium">Forecast Results</h3>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-white/5">
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                Hospital
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                Horizon
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-slate-400 uppercase tracking-wider">
                Predicted Admissions
              </th>
            </tr>
          </thead>
          <tbody>
            {data.map((row, i) => (
              <motion.tr
                key={`${row.hospital_id}-${row.horizon}`}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.03 }}
                className="border-b border-white/[0.03] hover:bg-white/[0.02] transition-colors"
              >
                <td className="px-6 py-3 text-sm text-slate-200 font-medium">{row.hospital_id}</td>
                <td className="px-6 py-3 text-sm text-slate-400">
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-500/10 text-blue-400 border border-blue-500/20">
                    Day {row.horizon}
                  </span>
                </td>
                <td className="px-6 py-3 text-sm text-right font-mono text-cyan">
                  {row.prediction.toFixed(2)}
                </td>
              </motion.tr>
            ))}
          </tbody>
        </table>
      </div>
    </motion.div>
  );
}

