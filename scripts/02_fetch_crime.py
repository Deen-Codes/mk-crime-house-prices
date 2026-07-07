"""
02_fetch_crime.py
-----------------
Downloads street-level crime for every Milton Keynes postcode district
(outcode) for each month of 2025, using the police.uk open data API.

Data sources:
  https://data.police.uk/docs/          (Open Government Licence v3.0)
  https://api.postcodes.io/             (outcode centroid lookup, free)

Outputs:
  data/raw/crime/{outcode}_{month}.json   one raw API response per call
  data/raw/crime_street_mk_2025.csv       all crimes flattened to one CSV

Method (and its limitation — see README "Limitations"):
  1. Read the price data and take every MK outcode that appears in it,
     so the crime data covers exactly the same areas as the sales data.
  2. Ask postcodes.io for each outcode's geographic centroid.
  3. Ask the police API for street crime within a 1-mile radius of that
     centroid, month by month. Radii of adjacent outcodes can overlap
     and outer edges of large districts can be missed; we de-duplicate
     by crime ID and accept the approximation — it is documented, which
     is what matters for an honest analysis.

Run:  python scripts/02_fetch_crime.py   (from the repo root, after 01)
"""

import csv
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

# --- Configuration ----------------------------------------------------------

RAW_DIR = Path("data/raw")
CRIME_DIR = RAW_DIR / "crime"
PRICES_FILE = RAW_DIR / "price_paid_mk_2025.csv"
OUT_CSV = RAW_DIR / "crime_street_mk_2025.csv"

MONTHS = [f"2025-{m:02d}" for m in range(1, 13)]  # 2025-01 .. 2025-12
MAX_WORKERS = 6          # polite parallelism — stay well under API limits
RETRIES = 2              # police API occasionally 429s/times out; retry


def get_outcodes_from_price_data() -> list[str]:
    """Unique MK outcodes present in the sales data (e.g. 'MK3', 'MK10').

    Deriving the list from the price file (rather than hardcoding MK1-MK19)
    keeps the two datasets covering identical areas by construction.
    """
    outcodes = set()
    with PRICES_FILE.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            postcode = (row["postcode"] or "").strip()
            if postcode.startswith("MK") and " " in postcode:
                outcodes.add(postcode.split()[0])
    return sorted(outcodes, key=lambda oc: int(oc[2:]))  # MK1, MK2, ... MK19


def get_centroid(outcode: str) -> tuple[float, float] | None:
    """Geographic centre of an outcode via postcodes.io. None if unknown."""
    r = requests.get(f"https://api.postcodes.io/outcodes/{outcode}", timeout=30)
    if r.status_code != 200:
        return None
    result = r.json()["result"]
    return result["latitude"], result["longitude"]


def fetch_month(outcode: str, lat: float, lng: float, month: str) -> list[dict]:
    """All street crimes within ~1 mile of (lat, lng) for one month.

    Saves the raw JSON to disk (reproducibility / re-runs without hitting
    the API) and returns the parsed list.
    """
    cache_file = CRIME_DIR / f"{outcode}_{month}.json"
    if cache_file.exists():  # already fetched on a previous run — skip
        return json.loads(cache_file.read_text(encoding="utf-8"))

    url = "https://data.police.uk/api/crimes-street/all-crime"
    params = {"lat": lat, "lng": lng, "date": month}

    for attempt in range(1 + RETRIES):
        try:
            r = requests.get(url, params=params, timeout=60)
            if r.status_code == 200:
                cache_file.write_text(r.text, encoding="utf-8")
                return r.json()
            time.sleep(1 + attempt)  # back off and retry on 429/5xx
        except requests.RequestException:
            time.sleep(1 + attempt)
    print(f"  WARNING: gave up on {outcode} {month}")
    return []


def main() -> None:
    CRIME_DIR.mkdir(parents=True, exist_ok=True)

    outcodes = get_outcodes_from_price_data()
    print(f"Outcodes found in price data: {', '.join(outcodes)}")

    # Resolve centroids first (fast, sequential — only ~17 calls).
    centroids = {}
    for oc in outcodes:
        c = get_centroid(oc)
        if c:
            centroids[oc] = c
        else:
            print(f"  WARNING: no centroid for {oc}, skipping")

    # Fetch every (outcode, month) pair in parallel.
    jobs = [(oc, lat, lng, m) for oc, (lat, lng) in centroids.items() for m in MONTHS]
    print(f"Fetching {len(jobs)} outcode-months of crime data...")

    rows, seen_ids = [], set()
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(fetch_month, oc, lat, lng, m): (oc, m)
                   for oc, lat, lng, m in jobs}
        for future in as_completed(futures):
            outcode, month = futures[future]
            for crime in future.result():
                # De-duplicate: overlapping 1-mile circles mean the same
                # crime can come back for two adjacent outcodes.
                if crime["id"] in seen_ids:
                    continue
                seen_ids.add(crime["id"])
                rows.append({
                    "crime_id": crime["id"],
                    "month": crime["month"],
                    "outcode": outcode,
                    "category": crime["category"],
                    "latitude": crime["location"]["latitude"],
                    "longitude": crime["location"]["longitude"],
                    "street_name": crime["location"]["street"]["name"],
                    "outcome": (crime.get("outcome_status") or {}).get("category", "none recorded"),
                })

    # Flatten to a single CSV — this is what the cleaning step consumes.
    rows.sort(key=lambda r: (r["month"], r["outcode"]))
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"Saved {len(rows):,} unique crimes to {OUT_CSV}")


if __name__ == "__main__":
    main()
