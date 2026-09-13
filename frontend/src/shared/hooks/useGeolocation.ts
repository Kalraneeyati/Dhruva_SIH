import { useState } from "react";
import type { LatLon } from "../types/domain";

interface GeolocationState {
  location: LatLon | null;
  status: "idle" | "locating" | "granted" | "denied" | "unsupported";
  request: () => void;
}

/**
 * Without this, every query used the gazetteer/default location regardless
 * of where the person actually is — fine for a demo query typed with a place
 * name in it, useless for a real fisherman at sea who just wants "is it safe
 * here, right now" without typing coordinates. One tap, browser-native,
 * no key needed.
 */
export function useGeolocation(): GeolocationState {
  const [location, setLocation] = useState<LatLon | null>(null);
  const [status, setStatus] = useState<GeolocationState["status"]>("idle");

  const request = () => {
    if (!("geolocation" in navigator)) {
      setStatus("unsupported");
      return;
    }
    setStatus("locating");
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLocation({ lat: pos.coords.latitude, lon: pos.coords.longitude });
        setStatus("granted");
      },
      () => setStatus("denied"),
      { enableHighAccuracy: false, timeout: 10_000, maximumAge: 5 * 60_000 },
    );
  };

  return { location, status, request };
}
