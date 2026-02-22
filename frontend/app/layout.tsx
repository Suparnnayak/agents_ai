import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "HealthFlow AI | AI-Driven Hospital Operations Intelligence",
  description:
    "Enterprise-grade AI forecasting platform for hospital admissions. 7-day predictions powered by LightGBM, external signals, and Groq LLM agent reasoning.",
  icons: { icon: "/favicon.ico" },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="scroll-smooth">
      <body className="bg-navy text-off-white antialiased">{children}</body>
    </html>
  );
}
