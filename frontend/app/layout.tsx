import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "HospiForecast | AI-Powered Hospital Admission Forecasting",
  description: "Enterprise-grade ML forecasting for hospital admissions. 7-day predictions with sub-second inference.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

