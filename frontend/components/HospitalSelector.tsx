"use client";

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";

interface Props {
  hospitals: string[];
  selected: string[];
  onChange: (ids: string[]) => void;
}

export default function HospitalSelector({ hospitals, selected, onChange }: Props) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const toggle = (id: string) => {
    onChange(selected.includes(id) ? selected.filter((s) => s !== id) : [...selected, id]);
  };

  return (
    <div ref={ref} className="relative w-full">
      <label className="block text-xs uppercase tracking-widest text-cyan mb-2 font-medium">
        Select Hospitals
      </label>
      <button
        onClick={() => setOpen(!open)}
        className="w-full glass-card px-4 py-3 text-left flex items-center justify-between rounded-lg hover:border-cyan/30 transition-all"
      >
        <span className="text-sm text-slate-300">
          {selected.length === 0
            ? "Choose hospitals..."
            : `${selected.length} hospital${selected.length > 1 ? "s" : ""} selected`}
        </span>
        <motion.svg
          animate={{ rotate: open ? 180 : 0 }}
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          className="text-slate-400"
        >
          <polyline points="6 9 12 15 18 9" />
        </motion.svg>
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -8, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8, scale: 0.98 }}
            transition={{ duration: 0.2 }}
            className="absolute z-30 mt-2 w-full glass-card p-2 max-h-60 overflow-y-auto rounded-lg shadow-xl"
          >
            {hospitals.map((h, i) => (
              <motion.button
                key={h}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.03 }}
                onClick={() => toggle(h)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all ${
                  selected.includes(h)
                    ? "bg-cyan/10 text-cyan"
                    : "text-slate-300 hover:bg-white/5"
                }`}
              >
                <div
                  className={`w-4 h-4 rounded border-2 flex items-center justify-center ${
                    selected.includes(h) ? "border-cyan bg-cyan" : "border-slate-500"
                  }`}
                >
                  {selected.includes(h) && (
                    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#0B1120" strokeWidth="3">
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                  )}
                </div>
                <span>{h}</span>
              </motion.button>
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      {selected.length > 0 && (
        <div className="flex flex-wrap gap-2 mt-3">
          {selected.map((h) => (
            <motion.span
              key={h}
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.8, opacity: 0 }}
              className="inline-flex items-center gap-1.5 px-3 py-1 text-xs font-medium bg-cyan/10 text-cyan border border-cyan/20 rounded-full"
            >
              {h}
              <button onClick={() => toggle(h)} className="hover:text-white transition-colors">
                ×
              </button>
            </motion.span>
          ))}
        </div>
      )}
    </div>
  );
}

