"use client";

import { useEffect, useState } from "react";
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

import {
  useLocation,
  STATE_LOCATIONS,
} from "@/context/LocationContext";

export default function TopNavBar() {
  const pathname = usePathname();

  const [mobileMenuOpen, setMobileMenuOpen] =
    useState(false);

  const [isScrolled, setIsScrolled] =
    useState(false);

  const { selectedLocation, setSelectedState } =
    useLocation();

  const navItems = [
    {
      label: "Dashboard",
      href: "/",
      icon: LayoutDashboard,
    },
    {
      label: "Chat",
      href: "/chat",
      icon: MessageSquare,
    },
    {
      label: "Alerts",
      href: "/alerts",
      icon: AlertTriangle,
    },
    {
      label: "Risk Map",
      href: "/risk",
      icon: Map,
    },
    {
      label: "Advisory",
      href: "/advisory",
      icon: ClipboardList,
    },
  ];

  // Change navbar background after scrolling
  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 20);
    };

    // Check initial scroll position
    handleScroll();

    window.addEventListener(
      "scroll",
      handleScroll,
      { passive: true }
    );

    return () => {
      window.removeEventListener(
        "scroll",
        handleScroll
      );
    };
  }, []);

  // Close mobile menu when route changes
  useEffect(() => {
    setMobileMenuOpen(false);
  }, [pathname]);

  return (
    <header
      className={`
        fixed left-0 right-0 top-0 z-[100]
        w-full border-b
        text-on-surface
        transition-all duration-500 ease-in-out
        ${
          isScrolled
            ? "border-white/30 bg-white/60 shadow-lg backdrop-blur-xl"
            : "border-surface-container-high bg-white shadow-sm"
        }
      `}
    >
      <div className="mx-auto flex h-16 max-w-[1440px] items-center justify-between px-4 sm:px-6 lg:px-8">
        {/* Brand Logo */}
        <Link
          href="/"
          className="group flex items-center space-x-2.5"
        >
          <div className="rounded-lg bg-primary p-2 text-on-primary shadow-sm transition-transform group-hover:scale-105">
            <ShieldAlert className="h-5 w-5" />
          </div>

          <div className="flex items-center">
            <span className="text-headline-sm font-bold tracking-tight text-primary">
              WeatherGPT
            </span>

            <span
              className={`
                ml-2 rounded border px-2 py-0.5
                text-[10px] text-label-caps
                transition-all duration-500
                ${
                  isScrolled
                    ? "border-white/40 bg-white/45 text-slate-700"
                    : "border-outline-variant/40 bg-surface-container text-on-surface-variant"
                }
              `}
            >
              IMD / MoES
            </span>
          </div>
        </Link>

        {/* Desktop Navigation */}
        <nav className="hidden items-center space-x-1 md:flex lg:space-x-6">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive =
              pathname === item.href;

            return (
              <Link
                key={item.href}
                href={item.href}
                className={`
                  relative flex items-center
                  space-x-1.5 py-5
                  text-body-sm font-medium
                  transition-colors duration-300
                  ${
                    isActive
                      ? "font-semibold text-primary"
                      : "text-slate-700 hover:text-primary"
                  }
                `}
              >
                <Icon
                  className={`
                    h-4 w-4
                    ${
                      isActive
                        ? "text-primary"
                        : "text-slate-500"
                    }
                  `}
                />

                <span>{item.label}</span>

                {isActive && (
                  <span className="absolute bottom-0 left-0 right-0 h-0.5 rounded-t-md bg-primary" />
                )}
              </Link>
            );
          })}
        </nav>

        {/* Desktop Right Utilities */}
        <div className="hidden items-center space-x-3 text-on-surface-variant md:flex">
          {/* State selector */}
          <div
            className={`
              flex items-center space-x-1
              rounded-lg border px-2 py-1
              text-xs shadow-sm
              transition-all duration-300
              hover:border-primary
              ${
                isScrolled
                  ? "border-white/50 bg-white/55"
                  : "border-outline-variant/40 bg-surface-container-low"
              }
            `}
          >
            <MapPin className="ml-1 h-3.5 w-3.5 shrink-0 text-primary" />

            <select
              value={selectedLocation.stateName}
              onChange={(event) =>
                setSelectedState(
                  event.target.value
                )
              }
              className="cursor-pointer bg-transparent py-0.5 pr-1 text-xs font-semibold text-slate-800 focus:outline-none"
              aria-label="Select State / Location"
            >
              {Object.keys(STATE_LOCATIONS).map(
                (state) => (
                  <option
                    key={state}
                    value={state}
                    className="bg-white text-slate-900"
                  >
                    {
                      STATE_LOCATIONS[state]
                        .displayName
                    }
                  </option>
                )
              )}
            </select>
          </div>

          {/* Language selector */}
          <button
            type="button"
            className={`
              rounded-lg p-1.5
              text-slate-600
              transition-colors duration-300
              hover:bg-white/50
              hover:text-primary
            `}
            title="Language selector"
            aria-label="Select Language"
          >
            <Languages className="h-4 w-4" />
          </button>
        </div>

        {/* Mobile Menu Button */}
        <div className="flex items-center space-x-2 md:hidden">
          <button
            type="button"
            onClick={() =>
              setMobileMenuOpen(
                (previous) => !previous
              )
            }
            className={`
              rounded-lg border p-2
              text-slate-700
              transition-all duration-300
              focus:outline-none
              ${
                isScrolled
                  ? "border-white/50 bg-white/55"
                  : "border-outline-variant/40 bg-surface-container"
              }
            `}
            aria-label={
              mobileMenuOpen
                ? "Close Navigation Menu"
                : "Open Navigation Menu"
            }
            aria-expanded={mobileMenuOpen}
          >
            {mobileMenuOpen ? (
              <X className="h-5 w-5" />
            ) : (
              <Menu className="h-5 w-5" />
            )}
          </button>
        </div>
      </div>

      {/* Mobile Menu */}
      {mobileMenuOpen && (
        <div
          className={`
            space-y-1 border-b px-4 pb-4 pt-2
            shadow-lg backdrop-blur-xl
            md:hidden
            ${
              isScrolled
                ? "border-white/30 bg-white/80"
                : "border-surface-container-high bg-white"
            }
          `}
        >
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive =
              pathname === item.href;

            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() =>
                  setMobileMenuOpen(false)
                }
                className={`
                  flex w-full items-center
                  space-x-3 rounded-lg
                  px-4 py-3 text-body-sm
                  font-semibold transition-all
                  ${
                    isActive
                      ? "bg-primary text-white"
                      : "text-slate-700 hover:bg-white/60 hover:text-primary"
                  }
                `}
              >
                <Icon
                  className={`
                    h-4 w-4
                    ${
                      isActive
                        ? "text-white"
                        : "text-slate-500"
                    }
                  `}
                />

                <span>{item.label}</span>
              </Link>
            );
          })}
        </div>
      )}
    </header>
  );
}