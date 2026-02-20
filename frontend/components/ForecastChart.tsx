"use client";

import { motion } from "framer-motion";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

interface ForecastResult {
  hospital_id: string;
  horizon: number;
  prediction: number;
}

interface Props {
  data: ForecastResult[];
}

const COLORS = ["#06B6D4", "#3B82F6", "#8B5CF6", "#EC4899", "#F59E0B", "#10B981", "#F43F5E"];

export default function ForecastChart({ data }: Props) {
  if (!data || data.length === 0) return null;

  const hospitals = [...new Set(data.map((d) => d.hospital_id))];
  const horizons = [...new Set(data.map((d) => d.horizon))].sort((a, b) => a - b);

  const chartData = horizons.map((h) => {
    const row: Record<string, number | string> = { horizon: `Day ${h}` };
    hospitals.forEach((hid) => {
      const match = data.find((d) => d.hospital_id === hid && d.horizon === h);
      if (match) row[hid] = Math.round(match.prediction * 100) / 100;
    });
    return row;
  });

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, delay: 0.2 }}
      className="glass-card rounded-xl p-6"
    >
      <h3 className="text-sm uppercase tracking-widest text-cyan mb-4 font-medium">Forecast Trend</h3>
      <div className="h-80">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="rgba(148,163,184,0.06)" strokeDasharray="3 3" />
            <XAxis
              dataKey="horizon"
              stroke="#64748b"
              fontSize={12}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              stroke="#64748b"
              fontSize={12}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v: number) => v.toFixed(0)}
            />
            <Tooltip
              contentStyle={{
                background: "rgba(11, 17, 32, 0.95)",
                border: "1px solid rgba(6, 182, 212, 0.2)",
                borderRadius: "0.75rem",
                color: "#F8FAFC",
                fontSize: "13px",
              }}
            />
            <Legend wrapperStyle={{ fontSize: "12px", color: "#94a3b8" }} />
            {hospitals.map((hid, i) => (
              <Line
                key={hid}
                type="monotone"
                dataKey={hid}
                stroke={COLORS[i % COLORS.length]}
                strokeWidth={2}
                dot={{ r: 4, fill: COLORS[i % COLORS.length] }}
                activeDot={{ r: 6 }}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </motion.div>
  );
}

