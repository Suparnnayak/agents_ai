"use client";

import { motion } from "framer-motion";

const steps = [
  {
    step: "01",
    title: "Ingest",
    description: "Historical admission data with weather, AQI, and demographic features",
  },
  {
    step: "02",
    title: "Engineer",
    description: "Automated lag features and categorical encoding with frozen schema",
  },
  {
    step: "03",
    title: "Predict",
    description: "Iterative 7-day horizon simulation using ModelBundle wrapper",
  },
  {
    step: "04",
    title: "Deliver",
    description: "Secure API response with forecast persistence and audit trail",
  },
];

export default function HowItWorksSection() {
  return (
    <section id="how-it-works" className="relative py-32 px-6 md:px-12">
      <div className="max-w-6xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <span className="text-xs uppercase tracking-widest text-cyan font-medium">How It Works</span>
          <h2 className="text-3xl md:text-5xl font-bold mt-4 mb-4">
            From Raw Data to <span className="gradient-text">Actionable Forecasts</span>
          </h2>
        </motion.div>

        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
          {steps.map((item, i) => (
            <motion.div
              key={item.step}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1, duration: 0.6 }}
              className="glass-card rounded-xl p-6"
            >
              <div className="flex items-center gap-4 mb-4">
                <div className="w-10 h-10 rounded-lg bg-cyan/10 text-cyan flex items-center justify-center text-sm font-bold border border-cyan/20">
                  {item.step}
                </div>
                <h3 className="text-lg font-semibold text-off-white">{item.title}</h3>
              </div>
              <p className="text-sm text-slate-400 leading-relaxed">{item.description}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

