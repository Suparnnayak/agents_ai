"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import Navbar from "@/components/layout/Navbar";
import Footer from "@/components/layout/Footer";
import Container from "@/components/layout/Container";

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.1, duration: 0.6, ease: [0.16, 1, 0.3, 1] },
  }),
};

const TEAM_SKILLS = [
  "Machine Learning & LightGBM",
  "FastAPI & Python Backend",
  "Next.js & React Frontend",
  "PostgreSQL & Database Design",
  "Serverless Deployment (Vercel)",
  "LLM Integration (Groq)",
  "CI/CD with GitHub Actions",
  "Healthcare Domain Knowledge",
];

export default function AboutPage() {
  return (
    <main className="min-h-screen bg-navy grid-overlay bg-gradient-animated">
      <Navbar />

      <div className="pt-20 pb-12">
        <Container>
          {/* Hero */}
          <motion.div
            initial="hidden"
            animate="visible"
            className="pt-4 mb-16 max-w-3xl"
          >
            <motion.h1 variants={fadeUp} custom={0} className="text-4xl lg:text-5xl font-bold leading-tight">
              About <span className="gradient-text">HealthFlow AI</span>
            </motion.h1>
            <motion.p variants={fadeUp} custom={1} className="mt-4 text-lg text-slate-400 leading-relaxed">
              HealthFlow AI is an end-to-end AI-powered hospital operations intelligence platform.
              We combine machine learning forecasting, real-time external signals, and LLM-powered
              reasoning to help hospital administrators make data-driven decisions.
            </motion.p>
          </motion.div>

          {/* Mission */}
          <motion.section
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, amount: 0.3 }}
            className="mb-16"
          >
            <div className="grid lg:grid-cols-2 gap-8">
              <motion.div variants={fadeUp} custom={0} className="glass-card-hover rounded-2xl p-8">
                <div className="w-12 h-12 rounded-xl bg-cyan/10 border border-cyan/20 flex items-center justify-center text-cyan mb-4">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
                  </svg>
                </div>
                <h3 className="text-xl font-semibold mb-3">Our Mission</h3>
                <p className="text-slate-400 leading-relaxed">
                  To democratize hospital operations intelligence by providing open-source,
                  production-grade AI tools that help healthcare facilities forecast demand,
                  optimize staffing, and prepare for surges — all without expensive proprietary solutions.
                </p>
              </motion.div>

              <motion.div variants={fadeUp} custom={1} className="glass-card-hover rounded-2xl p-8">
                <div className="w-12 h-12 rounded-xl bg-teal/10 border border-teal/20 flex items-center justify-center text-teal mb-4">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
                  </svg>
                </div>
                <h3 className="text-xl font-semibold mb-3">How It Works</h3>
                <p className="text-slate-400 leading-relaxed">
                  Our pipeline runs automated daily: GitHub Actions fetch external signals (weather, AQI),
                  compute forecasts using a LightGBM model, and store results in Neon PostgreSQL.
                  The AI agent then explains trends using Groq&apos;s LLM reasoning engine.
                </p>
              </motion.div>
            </div>
          </motion.section>

          {/* Tech stack */}
          <motion.section
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, amount: 0.3 }}
            className="mb-16"
          >
            <motion.h2 variants={fadeUp} custom={0} className="text-2xl font-bold mb-6">
              Tech <span className="gradient-text">Stack</span>
            </motion.h2>
            <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
              {TEAM_SKILLS.map((skill, i) => (
                <motion.div
                  key={skill}
                  variants={fadeUp}
                  custom={i * 0.5}
                  className="flex items-center gap-2.5 glass-card rounded-lg px-4 py-3"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-cyan flex-shrink-0">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                  <span className="text-sm text-slate-300">{skill}</span>
                </motion.div>
              ))}
            </div>
          </motion.section>

          {/* CTA */}
          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            variants={fadeUp}
            custom={0}
            className="glass-card rounded-2xl p-8 text-center relative overflow-hidden"
          >
            <div className="absolute inset-0 bg-gradient-to-br from-cyan/5 to-teal/5 pointer-events-none" />
            <h3 className="relative text-2xl font-bold mb-3">Ready to Explore?</h3>
            <p className="relative text-slate-400 mb-6 max-w-md mx-auto">
              Start using the dashboard, query the AI agent, or dive into the system details.
            </p>
            <div className="relative flex flex-col sm:flex-row justify-center gap-3">
              <Link href="/dashboard" className="btn-primary">Go to Dashboard</Link>
              <Link href="/contact" className="btn-secondary">Get in Touch</Link>
            </div>
          </motion.div>
        </Container>
      </div>

      <Footer />
    </main>
  );
}

