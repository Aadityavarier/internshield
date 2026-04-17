import type { Metadata } from "next";
import "./globals.css";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";

export const metadata: Metadata = {
  title: "InternShield — Verify Your Internship Offer Letter",
  description:
    "Don't fall for fake internship offers. InternShield uses AI to analyze offer letters, detect red flags, and protect students from internship scams. Free, anonymous, instant.",
  keywords: [
    "fake offer letter detector",
    "internship verification",
    "offer letter checker",
    "internship scam",
    "fake internship",
    "InternShield",
    "verify offer letter",
    "job scam checker",
  ],
  openGraph: {
    title: "InternShield — Don't Fall for Fake Internship Offers",
    description:
      "Free AI-powered tool to verify internship and job offer letters. Detect scams before they cost you.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <Navbar />
        <main>{children}</main>
        <Footer />
      </body>
    </html>
  );
}
