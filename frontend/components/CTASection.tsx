"use client";

import { motion } from "framer-motion";
import Link from "next/link";

export default function CTASection() {
  return (
    <section id="about" className="relative py-32 px-6 md:px-12">
      <div className="max-w-3xl mx-auto text-center">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
        >
          <h2 className="text-3xl md:text-5xl font-bold mb-4">
            Ready to <span className="gradient-text">Forecast</span>?
          </h2>
          <p className="text-slate-400 mb-8 max-w-lg mx-auto">
            Deploy hospital admission predictions in minutes.
            <br />
            No infrastructure setup required.
          </p>
          <Link
            href="/register"
            className="inline-flex items-center gap-2 px-8 py-4 bg-gradient-to-r from-cyan to-blue-600 text-white font-medium rounded-lg text-sm hover:shadow-lg hover:shadow-cyan/25 transition-all"
          >
            Create Free Account
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M5 12h14M12 5l7 7-7 7" />
            </svg>
          </Link>
        </motion.div>
      </div>
    </section>
  );
}

