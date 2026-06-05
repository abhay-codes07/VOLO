import type { Metadata } from "next";
import { Bricolage_Grotesque, Geist, Geist_Mono, Instrument_Serif } from "next/font/google";
import "./globals.css";
import { CursorHalo } from "@/components/motion/CursorHalo";
import { SmoothScroll } from "@/components/motion/SmoothScroll";
import { ScrollProgress } from "@/components/motion/ScrollProgress";
import { QueryProvider } from "@/components/QueryProvider";

const geistSans = Geist({ variable: "--font-geist", subsets: ["latin"], display: "swap" });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"], display: "swap" });
const bricolage = Bricolage_Grotesque({
  variable: "--font-bricolage", subsets: ["latin"], display: "swap", weight: ["400", "500", "600", "700"],
});
const instrument = Instrument_Serif({
  variable: "--font-instrument", subsets: ["latin"], display: "swap", weight: ["400"], style: ["normal", "italic"],
});

export const metadata: Metadata = {
  title: "Volo — Mission control for AI agents",
  description: "Record once. Replay deterministically. Ship.",
  metadataBase: new URL("http://localhost:3001"),
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} ${bricolage.variable} ${instrument.variable}`}
    >
      <body className="antialiased">
        <SmoothScroll />
        <ScrollProgress />
        <CursorHalo />
        <QueryProvider>{children}</QueryProvider>
      </body>
    </html>
  );
}
