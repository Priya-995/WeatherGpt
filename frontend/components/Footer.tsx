"use client";

import React from "react";
import Link from "next/link";
import { ShieldAlert, Globe, ExternalLink } from "lucide-react";

export default function Footer() {
  return (
    <footer className="bg-surface-container-low border-t border-surface-container-high text-on-surface-variant text-body-sm py-8 px-4 sm:px-6 lg:px-8 mt-12">
      <div className="max-w-[1440px] mx-auto grid grid-cols-1 md:grid-cols-4 gap-8 mb-8">
        {/* Brand & Purpose */}
        <div className="space-y-3 md:col-span-2">
          <div className="flex items-center space-x-2">
            <div className="p-1.5 bg-primary text-on-primary rounded-lg">
              <ShieldAlert className="w-4 h-4" />
            </div>
            <span className="text-headline-sm font-bold text-primary tracking-tight">
              WeatherGPT
            </span>
            <span className="text-[10px] font-mono bg-surface-container px-2 py-0.5 rounded border border-outline-variant/40 text-on-surface-variant">
              SIH Early-Warning Layer
            </span>
          </div>
          <p className="text-body-sm text-on-surface-variant leading-relaxed max-w-lg">
            Data verified by IMD Satellite Imagery, NWP numerical models & Open-Meteo. Transform complex weather data into personalized, multilingual and actionable safety decisions.
          </p>
        </div>

        {/* Quick Links */}
        <div className="space-y-2">
          <div className="text-label-caps text-on-surface font-bold">System Navigation</div>
          <ul className="space-y-1.5 text-body-sm font-medium">
            <li>
              <Link href="/" className="hover:text-primary transition-colors">
                Dashboard & Forecast
              </Link>
            </li>
            <li>
              <Link href="/chat" className="hover:text-primary transition-colors">
                AI Assistant
              </Link>
            </li>
            <li>
              <Link href="/alerts" className="hover:text-primary transition-colors">
                Official Alert Center
              </Link>
            </li>
            <li>
              <Link href="/risk" className="hover:text-primary transition-colors">
                Early-Warning Risk Map
              </Link>
            </li>
            <li>
              <Link href="/advisory" className="hover:text-primary transition-colors">
                Advisory Panel
              </Link>
            </li>
          </ul>
        </div>

        {/* Institutional & Legal Links */}
        <div className="space-y-2">
          <div className="text-label-caps text-on-surface font-bold">Governance & Support</div>
          <ul className="space-y-1.5 text-body-sm font-medium">
            <li className="flex items-center space-x-1.5 hover:text-primary transition-colors cursor-pointer">
              <Globe className="w-3.5 h-3.5 text-outline" />
              <span>India Meteorological Dept (IMD)</span>
            </li>
            <li className="flex items-center space-x-1.5 hover:text-primary transition-colors cursor-pointer">
              <Globe className="w-3.5 h-3.5 text-outline" />
              <span>Ministry of Earth Sciences (MoES)</span>
            </li>
            <li className="hover:text-primary transition-colors cursor-pointer">
              Emergency Contacts & Helplines
            </li>
            <li className="hover:text-primary transition-colors cursor-pointer">
              Terms of Service & Privacy
            </li>
          </ul>
        </div>
      </div>

      <div className="max-w-[1440px] mx-auto pt-6 border-t border-surface-container-high flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-outline font-mono">
        <div>
          © {new Date().getFullYear()} WeatherGPT • Smart India Hackathon (MoES Theme)
        </div>
        <div>
          Data verified by IMD Satellite Imagery & Open-Meteo
        </div>
      </div>
    </footer>
  );
}
