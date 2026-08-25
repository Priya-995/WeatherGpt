import type { Metadata } from "next";
import { Inter, Manrope } from "next/font/google";
import TopNavBar from "@/components/ui/TopNavBar";
import Footer from "@/components/Footer";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const manrope = Manrope({
  subsets: ["latin"],
  variable: "--font-manrope",
  display: "swap",
});

export const metadata: Metadata = {
  title: "WeatherGPT — AI Weather Intelligence & Early Warning",
  description: "Official weather decision support platform integrating real-time telemetry, NWP forecast outputs, and IMD emergency alerts.",
  icons: {
    icon: "/icon.svg",
    shortcut: "/icon.svg",
    apple: "/icon.svg",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      className={`${inter.variable} ${manrope.variable} h-full bg-[#f8f9fa] text-[#191c1d] antialiased`}
    >
      <body className="min-h-full flex flex-col font-sans bg-[#f8f9fa] text-[#191c1d]">
        <TopNavBar />
        <main className="flex-1 max-w-[1440px] w-full mx-auto p-4 sm:p-6 lg:p-8">
          {children}
        </main>
        <Footer />
      </body>
    </html>
  );
}
