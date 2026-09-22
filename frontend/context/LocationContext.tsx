"use client";

import React, { createContext, useContext, useState, useEffect } from "react";

export interface StateLocation {
  stateName: string;
  displayName: string;
  lat: number;
  lon: number;
}

export const DEFAULT_STATE: StateLocation = {
  stateName: "Delhi",
  displayName: "Delhi / NCR",
  lat: 28.61,
  lon: 77.21,
};

export const STATE_LOCATIONS: Record<string, StateLocation> = {
  "Delhi": { stateName: "Delhi", displayName: "Delhi / NCR", lat: 28.61, lon: 77.21 },
  "Uttar Pradesh": { stateName: "Uttar Pradesh", displayName: "Uttar Pradesh (Agra)", lat: 27.18, lon: 78.01 },
  "Rajasthan": { stateName: "Rajasthan", displayName: "Rajasthan (Barmer)", lat: 27.20, lon: 70.90 },
  "Maharashtra": { stateName: "Maharashtra", displayName: "Maharashtra (Mumbai)", lat: 19.07, lon: 72.87 },
  "Odisha": { stateName: "Odisha", displayName: "Odisha (Puri)", lat: 19.81, lon: 85.83 },
  "West Bengal": { stateName: "West Bengal", displayName: "West Bengal (Kolkata)", lat: 22.57, lon: 88.36 },
  "Tamil Nadu": { stateName: "Tamil Nadu", displayName: "Tamil Nadu (Chennai)", lat: 13.08, lon: 80.27 },
  "Karnataka": { stateName: "Karnataka", displayName: "Karnataka (Bengaluru)", lat: 12.97, lon: 77.59 },
  "Gujarat": { stateName: "Gujarat", displayName: "Gujarat (Ahmedabad)", lat: 23.02, lon: 72.57 },
  "Telangana": { stateName: "Telangana", displayName: "Telangana (Hyderabad)", lat: 17.38, lon: 78.48 },
  "Kerala": { stateName: "Kerala", displayName: "Kerala (Thiruvananthapuram)", lat: 8.52, lon: 76.93 },
  "Punjab": { stateName: "Punjab", displayName: "Punjab (Amritsar)", lat: 31.63, lon: 74.87 },
  "Haryana": { stateName: "Haryana", displayName: "Haryana (Gurugram)", lat: 28.45, lon: 77.02 },
  "Madhya Pradesh": { stateName: "Madhya Pradesh", displayName: "Madhya Pradesh (Bhopal)", lat: 23.25, lon: 77.41 },
  "Assam": { stateName: "Assam", displayName: "Assam (Guwahati)", lat: 26.14, lon: 91.73 },
  "Bihar": { stateName: "Bihar", displayName: "Bihar (Patna)", lat: 25.59, lon: 85.13 },
  "Jammu and Kashmir": { stateName: "Jammu and Kashmir", displayName: "Jammu & Kashmir (Srinagar)", lat: 34.08, lon: 74.79 },
  "Himachal Pradesh": { stateName: "Himachal Pradesh", displayName: "Himachal Pradesh (Shimla)", lat: 31.10, lon: 77.17 },
  "Uttarakhand": { stateName: "Uttarakhand", displayName: "Uttarakhand (Dehradun)", lat: 30.31, lon: 78.03 },
  "Andhra Pradesh": { stateName: "Andhra Pradesh", displayName: "Andhra Pradesh (Visakhapatnam)", lat: 17.68, lon: 83.21 },
  "Goa": { stateName: "Goa", displayName: "Goa (Panaji)", lat: 15.49, lon: 73.82 },
  "Puducherry": { stateName: "Puducherry", displayName: "Puducherry", lat: 11.94, lon: 79.80 },
};

interface LocationContextType {
  selectedLocation: StateLocation;
  setSelectedState: (stateName: string) => void;
}

const LocationContext = createContext<LocationContextType>({
  selectedLocation: DEFAULT_STATE,
  setSelectedState: () => {},
});

export function LocationProvider({ children }: { children: React.ReactNode }) {
  const [selectedLocation, setSelectedLocation] = useState<StateLocation>(DEFAULT_STATE);

  useEffect(() => {
    const saved = localStorage.getItem("weathergpt_selected_state");
    if (saved && STATE_LOCATIONS[saved]) {
      setSelectedLocation(STATE_LOCATIONS[saved]);
    }
  }, []);

  const setSelectedState = (stateName: string) => {
    const loc = STATE_LOCATIONS[stateName] || DEFAULT_STATE;
    setSelectedLocation(loc);
    localStorage.setItem("weathergpt_selected_state", loc.stateName);
  };

  return (
    <LocationContext.Provider value={{ selectedLocation, setSelectedState }}>
      {children}
    </LocationContext.Provider>
  );
}

export function useLocation() {
  return useContext(LocationContext);
}
