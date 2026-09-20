"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  ShieldAlert,
  LayoutDashboard,
  MessageSquare,
  AlertTriangle,
  Map,
  ClipboardList,
  MapPin,
  Languages,
  Menu,
  X,
} from "lucide-react";

export default function TopNavBar() {
  const pathname = usePathname();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navItems = [
    { label: "Dashboard", href: "/", icon: LayoutDashboard },
    { label: "Chat", href: "/chat", icon: MessageSquare },
    { label: "Alerts", href: "/alerts", icon: AlertTriangle },
    { label: "Risk Map", href: "/risk", icon: Map },
    { label: "Advisory", href: "/advisory", icon: ClipboardList },
  ];

  return (
    <header className="bg-surface-container-lowest border-b border-surface-container-high text-on-surface sticky top-0 z-50 shadow-sm">
      <div className="max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand Logo */}
        <Link href="/" className="flex items-center space-x-2.5 group">
          <div className="p-2 bg-primary text-on-primary rounded-lg shadow-sm group-hover:scale-105 transition-transform">
            <ShieldAlert className="w-5 h-5" />
          </div>
          <div>
            <span className="text-headline-sm font-bold text-primary tracking-tight">
              WeatherGPT
            </span>
            <span className="ml-2 text-[10px] text-label-caps text-on-surface-variant bg-surface-container px-2 py-0.5 rounded border border-outline-variant/40">
              IMD / MoES
            </span>
          </div>
        </Link>

        {/* Desktop Navigation with Active Underline in Primary Color */}
        <nav className="hidden md:flex items-center space-x-1 lg:space-x-6">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`relative py-5 text-body-sm font-medium transition-colors flex items-center space-x-1.5 ${
                  isActive
                    ? "text-primary font-semibold"
                    : "text-on-surface-variant hover:text-primary"
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? "text-primary" : "text-outline"}`} />
                <span>{item.label}</span>
                {/* Active-state underline in primary color */}
                {isActive && (
                  <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary rounded-t-md" />
                )}
              </Link>
            );
          })}
        </nav>

        {/* Right utility icons (Location, Language toggle) */}
        <div className="hidden md:flex items-center space-x-3 text-on-surface-variant">
          <div className="flex items-center space-x-1 text-xs bg-surface-container-low px-2.5 py-1.5 rounded border border-outline-variant/40">
            <MapPin className="w-3.5 h-3.5 text-primary" />
            <span className="font-medium text-on-surface">New Delhi, IN</span>
          </div>
          <button
            type="button"
            className="p-1.5 hover:bg-surface-container rounded-lg text-on-surface-variant hover:text-primary transition-colors"
            title="Language selector"
            aria-label="Select Language"
          >
            <Languages className="w-4 h-4" />
          </button>
        </div>

        {/* Mobile Hamburger Toggle */}
        <div className="md:hidden flex items-center space-x-2">
          <button
            type="button"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="p-2 rounded-lg bg-surface-container border border-outline-variant/40 text-on-surface-variant focus:outline-none"
            aria-label="Toggle Navigation Menu"
          >
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile Menu Drawer */}
      {mobileMenuOpen && (
        <div className="md:hidden bg-surface-container-lowest border-b border-surface-container-high px-4 pt-2 pb-4 space-y-1 shadow-lg">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setMobileMenuOpen(false)}
                className={`w-full px-4 py-3 rounded-lg text-body-sm font-semibold transition-all flex items-center space-x-3 ${
                  isActive
                    ? "bg-primary-container text-on-primary-container"
                    : "text-on-surface-variant hover:bg-surface-container"
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? "text-on-primary-container" : "text-outline"}`} />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </div>
      )}
    </header>
  );
}
