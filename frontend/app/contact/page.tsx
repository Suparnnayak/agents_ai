"use client";

import { useState, FormEvent } from "react";
import { motion } from "framer-motion";
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

const CONTACT_INFO = [
  {
    icon: "M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z",
    label: "Email",
    value: "support@healthflow.ai",
  },
  {
    icon: "M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z M15 11a3 3 0 11-6 0 3 3 0 016 0z",
    label: "Location",
    value: "Remote-first team",
  },
  {
    icon: "M12 6v6l4 2M12 2a10 10 0 100 20 10 10 0 000-20z",
    label: "Response Time",
    value: "Within 24 hours",
  },
];

export default function ContactPage() {
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    setSubmitted(true);
  };

  return (
    <main className="min-h-screen bg-navy grid-overlay bg-gradient-animated">
      <Navbar />

      <div className="pt-20 pb-12">
        <Container>
          <motion.div initial="hidden" animate="visible" className="pt-4 mb-12">
            <motion.h1 variants={fadeUp} custom={0} className="text-4xl font-bold">
              <span className="gradient-text">Contact Us</span>
            </motion.h1>
            <motion.p variants={fadeUp} custom={1} className="mt-3 text-slate-400 max-w-xl">
              Have questions about HealthFlow AI? We&apos;d love to hear from you.
            </motion.p>
          </motion.div>

          <div className="grid lg:grid-cols-5 gap-8">
            {/* Contact info */}
            <motion.div
              initial="hidden"
              animate="visible"
              className="lg:col-span-2 space-y-4"
            >
              {CONTACT_INFO.map((item, i) => (
                <motion.div
                  key={item.label}
                  variants={fadeUp}
                  custom={i + 1}
                  className="glass-card rounded-xl p-5 flex items-start gap-4"
                >
                  <div className="w-10 h-10 rounded-lg bg-cyan/10 border border-cyan/20 flex items-center justify-center flex-shrink-0">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-cyan">
                      <path d={item.icon} />
                    </svg>
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-slate-200">{item.label}</h4>
                    <p className="text-sm text-slate-400 mt-0.5">{item.value}</p>
                  </div>
                </motion.div>
              ))}
            </motion.div>

            {/* Form */}
            <motion.div
              initial="hidden"
              animate="visible"
              className="lg:col-span-3"
            >
              <motion.div variants={fadeUp} custom={1} className="glass-card rounded-xl p-6 sm:p-8">
                {submitted ? (
                  <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="text-center py-12"
                  >
                    <div className="w-16 h-16 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mx-auto mb-4">
                      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-emerald-400">
                        <polyline points="20 6 9 17 4 12" />
                      </svg>
                    </div>
                    <h3 className="text-xl font-semibold mb-2">Message Sent!</h3>
                    <p className="text-slate-400">Thank you for reaching out. We&apos;ll get back to you soon.</p>
                  </motion.div>
                ) : (
                  <form onSubmit={handleSubmit} className="space-y-5">
                    <div className="grid sm:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-xs uppercase tracking-widest text-cyan mb-2 font-medium">
                          Name
                        </label>
                        <input type="text" required className="input-field" placeholder="John Doe" />
                      </div>
                      <div>
                        <label className="block text-xs uppercase tracking-widest text-cyan mb-2 font-medium">
                          Email
                        </label>
                        <input type="email" required className="input-field" placeholder="john@example.com" />
                      </div>
                    </div>

                    <div>
                      <label className="block text-xs uppercase tracking-widest text-cyan mb-2 font-medium">
                        Subject
                      </label>
                      <input type="text" required className="input-field" placeholder="How can we help?" />
                    </div>

                    <div>
                      <label className="block text-xs uppercase tracking-widest text-cyan mb-2 font-medium">
                        Message
                      </label>
                      <textarea
                        rows={5}
                        required
                        className="input-field resize-none"
                        placeholder="Tell us more..."
                      />
                    </div>

                    <button type="submit" className="btn-primary w-full sm:w-auto">
                      Send Message
                    </button>
                  </form>
                )}
              </motion.div>
            </motion.div>
          </div>
        </Container>
      </div>

      <Footer />
    </main>
  );
}

