#!/usr/bin/env python
"""Gate 0: a real SST value for a real lat/lon, fetched in code.

Never passes verify=False. If INCOIS's chain cannot be built, that is reported as a
failure with its cause, not worked around.
"""
import os
import sys

import certifi
import requests

LAT, LON = 11.05, 79.85  # the evidence-card cell off Nagapattinam
TIMEOUT = 30


def open_meteo() -> bool:
    r = requests.get(
        "https://marine-api.open-meteo.com/v1/marine",
        params={
            "latitude": LAT,
            "longitude": LON,
            "current": "sea_surface_temperature,wave_height",
            "timezone": "Asia/Kolkata",
        },
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    d = r.json()
    c, u = d["current"], d["current_units"]
    print(f"  open_meteo_marine  SST {c['sea_surface_temperature']} {u['sea_surface_temperature']}"
          f"  wave {c['wave_height']} {u['wave_height']}")
    print(f"    valid  {c['time']} {d['timezone_abbreviation']}")
    print(f"    cell   {d['latitude']:.4f}N {d['longitude']:.4f}E  (requested {LAT}N {LON}E)")
    if abs(d["latitude"] - LAT) > 0.05 or abs(d["longitude"] - LON) > 0.05:
        print("    note   served cell differs from requested — record the SERVED cell in evidence")
    return True


def incois() -> bool:
    """INCOIS serves only its leaf cert and omits the GlobalSign RSA OV SSL CA 2018
    intermediate, so the chain cannot be built from a stock trust store. Point
    INCOIS_CA_BUNDLE at a bundle containing that intermediate."""
    verify = os.environ.get("INCOIS_CA_BUNDLE") or certifi.where()
    base = os.environ.get("INCOIS_ERDDAP_BASE", "https://erddap.incois.gov.in/erddap")
    try:
        r = requests.get(f"{base}/index.html", timeout=TIMEOUT, verify=verify)
        r.raise_for_status()
    except requests.exceptions.SSLError as e:
        print(f"  incois_erddap      UNVERIFIED — {type(e.__cause__).__name__ if e.__cause__ else 'SSLError'}")
        print(f"    bundle {verify}")
        print("    cause  server omits intermediate 'GlobalSign RSA OV SSL CA 2018'")
        print("    fix    add that intermediate to a bundle, set INCOIS_CA_BUNDLE. Never verify=False.")
        return False
    except requests.RequestException as e:
        print(f"  incois_erddap      UNREACHABLE — {type(e).__name__}")
        return False
    print(f"  incois_erddap      reachable and verified (HTTP {r.status_code})")

    # Daily-OI-V2. Dimensions are [time][zlev][latitude][longitude] — the dataset
    # summary omits zlev. Coverage ends 2011-10-04, so this is an archive, not a feed.
    q = (f"{base}/griddap/NOAA_AVHRR_AMSR_datasets.json"
         "?sst%5B(last)%5D%5B(0.0)%5D%5B(11.0):(11.1)%5D%5B(79.8):(79.9)%5D")
    g = requests.get(q, timeout=TIMEOUT, verify=verify)
    g.raise_for_status()
    t = g.json()["table"]
    for row in t["rows"]:
        time_, _zlev, lat, lon, sst = row
        print(f"  incois_erddap      SST {sst} degrees C")
        print(f"    valid  {time_}")
        print(f"    cell   {lat}N {lon}E  ·  NOAA_AVHRR_AMSR_datasets (archive, ends 2011-10-04)")
    return True


if __name__ == "__main__":
    print("Gate 0 — real numbers for a real lat/lon\n")
    results = {"open_meteo": open_meteo(), "incois": incois()}
    print()
    ok = results["open_meteo"]  # gate needs one real value in code; INCOIS is tracked separately
    print(f"GATE 0 SST fetch: {'PASS' if ok else 'FAIL'}   INCOIS chain: "
          f"{'ok' if results['incois'] else 'BLOCKED (see above)'}")
    sys.exit(0 if ok else 1)
