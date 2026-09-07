import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Can You Negotiate? — Crisis Negotiation Simulator",
  description: "A real-time, voice-first crisis negotiation simulator. De-escalate via verbal interrupt, calm the subject, and prevent escalation.",
  keywords: ["negotiation", "crisis", "simulation", "de-escalation", "voice AI"],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex-col">{children}</body>
    </html>
  );
}
