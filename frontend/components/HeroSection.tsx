"use client";

import { motion } from "framer-motion";
import Link from "next/link";

export default function HeroSection() {
  return (
    <section className="relative min-h-screen flex items-center overflow-hidden">
      {/* Animated background gradient */}
      <div className="absolute inset-0">
        <motion.div
          animate={{
            backgroundPosition: ["0% 0%", "100% 100%"],
          }}
          transition={{
            duration: 20,
            repeat: Infinity,
            repeatType: "reverse",
          }}
          className="absolute inset-0 bg-gradient-to-br from-cyan/10 via-blue-600/5 to-cyan/10 bg-[length:200%_200%]"
        />
        <div className="absolute inset-0 grid-overlay" />
      </div>

      {/* Parallax glow elements */}
      <motion.div
        animate={{
          x: [0, 30, 0],
          y: [0, -20, 0],
        }}
        transition={{
          duration: 8,
          repeat: Infinity,
          ease: "easeInOut",
        }}
        className="absolute top-20 right-20 w-96 h-96 rounded-full bg-cyan/5 blur-[100px]"
      />
      <motion.div
        animate={{
          x: [0, -25, 0],
          y: [0, 15, 0],
        }}
        transition={{
          duration: 10,
          repeat: Infinity,
          ease: "easeInOut",
        }}
        className="absolute bottom-20 left-20 w-80 h-80 rounded-full bg-blue-600/5 blur-[100px]"
      />

      <div className="relative z-10 max-w-7xl mx-auto px-6 md:px-12 pt-24">
        <div className="max-w-3xl">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
            className="space-y-6"
          >
            <motion.span
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.2, duration: 0.5 }}
              className="inline-block px-4 py-1.5 text-xs font-medium uppercase tracking-widest text-cyan border border-cyan/20 rounded-full bg-cyan/5"
            >
              AI-Powered Healthcare Analytics
            </motion.span>

            <motion.h1
              initial={{ opacity: 0, y: 40 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3, duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
              className="text-5xl md:text-6xl lg:text-7xl font-bold leading-tight tracking-tight"
            >
              <span className="text-off-white">Predict Hospital</span>
              <br />
              <span className="gradient-text">Admissions</span>
              <br />
              <span className="text-slate-400 text-4xl md:text-5xl lg:text-6xl font-light">
                Before They Happen
              </span>
            </motion.h1>

            <motion.p
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5, duration: 0.6 }}
              className="text-lg md:text-xl text-slate-400 max-w-2xl leading-relaxed"
            >
              Enterprise forecasting engine powered by machine learning.
              <br />
              7-day admission predictions with sub-second inference.
              <br />
              Built for hospital operations teams.
            </motion.p>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.7, duration: 0.6 }}
              className="flex flex-wrap gap-4 pt-4"
            >
              <Link
                href="/register"
                className="group px-8 py-4 bg-gradient-to-r from-cyan to-blue-600 text-white font-medium rounded-lg text-sm inline-flex items-center gap-2 hover:shadow-lg hover:shadow-cyan/25 transition-all"
              >
                Start Forecasting
                <svg
                  className="w-4 h-4 group-hover:translate-x-1 transition-transform"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  viewBox="0 0 24 24"
                >
                  <path d="M5 12h14M12 5l7 7-7 7" />
                </svg>
              </Link>
              <a
                href="#features"
                className="px-8 py-4 border border-slate-600 text-slate-300 font-medium rounded-lg text-sm hover:border-slate-400 hover:bg-white/5 transition-all"
              >
                Learn More
              </a>
            </motion.div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}

