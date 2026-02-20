"use client";

import Navbar from "@/components/Navbar";
import HeroSection from "@/components/HeroSection";
import FeatureSection from "@/components/FeatureSection";
import HowItWorksSection from "@/components/HowItWorksSection";
import CTASection from "@/components/CTASection";

export default function HomePage() {
  return (
    <main className="min-h-screen bg-navy">
      <Navbar />
      <HeroSection />
      <FeatureSection />
      <HowItWorksSection />
      <CTASection />
      <footer className="border-t border-white/5 py-8 px-6 md:px-12">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="text-sm text-slate-500">
            &copy; 2026 HospiForecast. All rights reserved.
          </div>
          <div className="flex gap-6">
            {["Privacy", "Terms", "API Docs"].map((link) => (
              <a
                key={link}
                href="#"
                className="text-sm text-slate-500 hover:text-slate-300 transition-colors"
              >
                {link}
              </a>
            ))}
          </div>
        </div>
      </footer>
    </main>
  );
}

