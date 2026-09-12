import { useEffect, useState } from "react";

/** Drives the "Offline — showing cached data" badge. This is the one bit of
 * runtime truth every surface needs: a boat crew must always be able to see
 * whether they are looking at a live answer or a cached one. */
export function useOnlineStatus(): boolean {
  const [online, setOnline] = useState(() => (typeof navigator === "undefined" ? true : navigator.onLine));

  useEffect(() => {
    const goOnline = () => setOnline(true);
    const goOffline = () => setOnline(false);
    window.addEventListener("online", goOnline);
    window.addEventListener("offline", goOffline);
    return () => {
      window.removeEventListener("online", goOnline);
      window.removeEventListener("offline", goOffline);
    };
  }, []);

  return online;
}
