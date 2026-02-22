"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";
import { isAuthenticated, logout, getUser } from "@/lib/auth";

export default function Navbar() {
  const pathname = usePathname();
  const [scrolled, setScrolled] = useState(false);
  const [authed, setAuthed] = useState(false);

  useEffect(() => {
    setAuthed(isAuthenticated());
    const handleScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, [pathname]);

  const handleLogout = () => {
    logout();
    window.location.href = "/";
  };

  return (
    <motion.header
      initial={{ y: -100 }}
      animate={{ y: 0 }}
      transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      className={`fixed top-0 inset-x-0 z-50 transition-all duration-300 ${
        scrolled
          ? "bg-navy/95 backdrop-blur-xl border-b border-white/5"
          : "bg-transparent"
      }`}
    >
      <nav className="max-w-7xl mx-auto px-6 md:px-12 py-4 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2 group">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan to-blue-600 flex items-center justify-center">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5">
              <path d="M12 2v4M12 18v4M2 12h4M18 12h4" />
              <circle cx="12" cy="12" r="3" />
            </svg>
          </div>
          <span className="text-lg font-semibold">
            <span className="gradient-text">Hospi</span>
            <span className="text-off-white">Forecast</span>
          </span>
        </Link>

        <div className="flex items-center gap-4">
          {authed ? (
            <>
              <Link
                href="/dashboard"
                className={`px-4 py-2 text-sm font-medium transition-colors ${
                  pathname === "/dashboard"
                    ? "text-cyan"
                    : "text-slate-300 hover:text-cyan"
                }`}
              >
                Dashboard
              </Link>
              <Link
                href="/agent"
                className={`px-4 py-2 text-sm font-medium transition-colors ${
                  pathname === "/agent"
                    ? "text-cyan"
                    : "text-slate-300 hover:text-cyan"
                }`}
              >
                AI Agent
              </Link>
              <button
                onClick={handleLogout}
                className="px-4 py-2 text-sm font-medium text-slate-400 hover:text-white transition-colors"
              >
                Logout
              </button>
            </>
          ) : (
            <>
              <Link
                href="/login"
                className="px-4 py-2 text-sm font-medium text-slate-300 hover:text-white transition-colors"
              >
                Sign In
              </Link>
              <Link
                href="/register"
                className="px-5 py-2 text-sm font-medium bg-gradient-to-r from-cyan to-blue-600 text-white rounded-lg hover:shadow-lg hover:shadow-cyan/25 transition-all"
              >
                Get Started
              </Link>
            </>
          )}
        </div>
      </nav>
    </motion.header>
  );
}

