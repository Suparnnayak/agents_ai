"use client";

import { motion } from "framer-motion";

const features = [
  {
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
      </svg>
    ),
    title: "Sub-Second Inference",
    description: "LightGBM model optimized for real-time predictions. No cold starts, no batching delays.",
  },
  {
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
        <rect x="3" y="3" width="18" height="18" rx="2" />
        <path d="M3 9h18M9 21V9" />
      </svg>
    ),
    title: "Frozen Feature Schema",
    description: "Zero feature drift. ModelBundle locks features at training time and enforces at inference.",
  },
  {
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
      </svg>
    ),
    title: "Secure by Design",
    description: "JWT authentication, role-based access, and transaction-safe PostgreSQL persistence.",
  },
];

export default function FeatureSection() {
  return (
    <section id="features" className="relative py-32 px-6 md:px-12">
      <div className="max-w-6xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <span className="text-xs uppercase tracking-widest text-cyan font-medium">Platform Features</span>
          <h2 className="text-3xl md:text-5xl font-bold mt-4 mb-4">
            Built for <span className="gradient-text">Production</span>
          </h2>
          <p className="text-slate-400 max-w-xl mx-auto">
            Enterprise-grade ML infrastructure designed for healthcare systems
          </p>
        </motion.div>

        <div className="grid md:grid-cols-3 gap-6">
          {features.map((feat, i) => (
            <motion.div
              key={feat.title}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.15, duration: 0.6 }}
              whileHover={{ y: -8, scale: 1.02 }}
              className="glass-card rounded-xl p-8 group cursor-pointer"
            >
              <div className="w-12 h-12 rounded-lg bg-cyan/10 text-cyan flex items-center justify-center mb-5 group-hover:bg-cyan/20 group-hover:border-cyan/30 border border-cyan/10 transition-all">
                {feat.icon}
              </div>
              <h3 className="text-lg font-semibold text-off-white mb-2">{feat.title}</h3>
              <p className="text-sm text-slate-400 leading-relaxed">{feat.description}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

