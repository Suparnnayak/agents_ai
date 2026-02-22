"use client";

import Link from "next/link";

interface LogoProps {
  size?: "sm" | "md" | "lg";
  showText?: boolean;
}

export default function Logo({ size = "md", showText = true }: LogoProps) {
  const dims = { sm: 28, md: 36, lg: 48 }[size];
  const textSize = { sm: "text-base", md: "text-xl", lg: "text-2xl" }[size];

  return (
    <Link href="/" className="flex items-center gap-2.5 group">
      <svg
        width={dims}
        height={dims}
        viewBox="0 0 64 64"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="flex-shrink-0"
      >
        {/* Gradient defs */}
        <defs>
          <linearGradient id="crossGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#00E5FF" />
            <stop offset="100%" stopColor="#14B8A6" />
          </linearGradient>
          <linearGradient id="waveGrad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#00E5FF" stopOpacity="0.8" />
            <stop offset="100%" stopColor="#06B6D4" stopOpacity="0.3" />
          </linearGradient>
        </defs>

        {/* Medical cross */}
        <rect x="22" y="8" width="20" height="36" rx="3" fill="url(#crossGrad)" opacity="0.9" />
        <rect x="12" y="18" width="40" height="16" rx="3" fill="url(#crossGrad)" opacity="0.9" />

        {/* Wave */}
        <path
          d="M8 46 C18 40, 28 50, 38 44 C48 38, 52 44, 58 42"
          stroke="url(#waveGrad)"
          strokeWidth="2.5"
          strokeLinecap="round"
          fill="none"
        />
        <path
          d="M10 50 C20 44, 30 54, 40 48 C50 42, 54 48, 60 46"
          stroke="url(#waveGrad)"
          strokeWidth="1.5"
          strokeLinecap="round"
          fill="none"
          opacity="0.5"
        />

        {/* Pixel squares */}
        <rect x="48" y="12" width="4" height="4" rx="1" fill="#00E5FF" opacity="0.7" />
        <rect x="54" y="8" width="3" height="3" rx="0.5" fill="#00E5FF" opacity="0.5" />
        <rect x="52" y="18" width="3" height="3" rx="0.5" fill="#14B8A6" opacity="0.6" />
        <rect x="56" y="14" width="2" height="2" rx="0.5" fill="#22D3EE" opacity="0.4" />
      </svg>

      {showText && (
        <span className={`${textSize} font-bold tracking-tight`}>
          <span className="text-slate-200 group-hover:text-white transition-colors">Health</span>
          <span className="gradient-text">Flow</span>
          <span className="text-cyan/60 text-[0.6em] font-semibold ml-1">AI</span>
        </span>
      )}
    </Link>
  );
}

