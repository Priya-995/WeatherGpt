"use client";

import React, { useState, useRef, useEffect } from "react";
import { LocationItem, searchLocation } from "@/lib/api";
import { Search, MapPin, X, Loader2 } from "lucide-react";

interface LocationSearchProps {
  onSelectLocation: (loc: LocationItem) => void;
  selectedLocation: LocationItem;
  className?: string;
}

export default function LocationSearch({
  onSelectLocation,
  selectedLocation,
  className = "",
}: LocationSearchProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<LocationItem[]>([]);
  const [searching, setSearching] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleInputChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setQuery(val);

    if (!val.trim()) {
      setResults([]);
      setIsOpen(false);
      return;
    }

    setSearching(true);
    try {
      const res = await searchLocation(val, 6);
      setResults(res);
      setIsOpen(true);
    } catch {
      setResults([]);
    } finally {
      setSearching(false);
    }
  };

  const handleSelect = (loc: LocationItem) => {
    onSelectLocation(loc);
    setQuery("");
    setResults([]);
    setIsOpen(false);
  };

  const handleClear = () => {
    setQuery("");
    setResults([]);
    setIsOpen(false);
  };

  return (
    <div ref={containerRef} className={`relative w-full ${className}`}>
      <div className="relative">
        <input
          type="text"
          placeholder="Search location (e.g. Noida, Paris, Barmer)..."
          value={query}
          onChange={handleInputChange}
          onFocus={() => {
            if (results.length > 0) setIsOpen(true);
          }}
          className="w-full bg-slate-950/90 border border-slate-700 text-white rounded-xl pl-10 pr-10 py-2.5 text-sm placeholder-slate-400 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/50 transition-all shadow-inner"
        />
        <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />

        {searching ? (
          <Loader2 className="w-4 h-4 text-blue-400 animate-spin absolute right-3.5 top-1/2 -translate-y-1/2" />
        ) : query ? (
          <button
            type="button"
            onClick={handleClear}
            className="text-slate-400 hover:text-white absolute right-3 top-1/2 -translate-y-1/2 p-1 rounded-full hover:bg-slate-800 transition-colors"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        ) : null}
      </div>

      {/* Autocomplete Dropdown */}
      {isOpen && results.length > 0 && (
        <ul className="absolute left-0 right-0 top-full mt-1.5 bg-slate-900/95 border border-slate-700 rounded-xl shadow-2xl z-50 max-h-64 overflow-y-auto divide-y divide-slate-800/80 backdrop-blur-xl">
          {results.map((item, idx) => (
            <li
              key={idx}
              onClick={() => handleSelect(item)}
              className="p-3 text-sm hover:bg-blue-600/20 cursor-pointer text-slate-200 hover:text-white transition-colors flex items-center space-x-3 group"
            >
              <div className="p-1.5 bg-slate-950 group-hover:bg-blue-600/30 text-blue-400 rounded-lg border border-slate-800 shrink-0">
                <MapPin className="w-4 h-4" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="font-semibold text-white truncate">{item.name}</div>
                <div className="text-xs text-slate-400 truncate">
                  {item.admin1 ? `${item.admin1}, ` : ""}
                  {item.country || ""}
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
