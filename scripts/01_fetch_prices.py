"""
01_fetch_prices.py
------------------
Downloads every residential property sale in Milton Keynes for 2025 from
HM Land Registry's Price Paid Data (PPD) service.

Data source: http://landregistry.data.gov.uk (Open Government Licence v3.0)
Output:      data/raw/price_paid_mk_2025.csv

Why this source:
  PPD is the official record of property transactions in England & Wales.
  Each row is one completed sale: price, date, postcode, property type.
  The ppd_data.csv endpoint lets us filter server-side by town and date,
  so we only pull the ~3,700 Milton Keynes rows rather than the national
  multi-gigabyte file.

Run:  python scripts/01_fetch_prices.py   (from the repo root)
"""

from pathlib import Path
from urllib.parse import urlencode

import requests

# --- Configuration ----------------------------------------------------------

RAW_DIR = Path("data/raw")
OUT_FILE = RAW_DIR / "price_paid_mk_2025.csv"

# The PPD export has NO header row, so we define the columns ourselves.
# Column order is fixed by the Land Registry export format.
COLUMNS = [
    "transaction_id", "price", "date_of_transfer", "postcode",
    "property_type",   # D=detached, S=semi, T=terraced, F=flat/maisonette
    "new_build",       # Y = newly built at time of sale
    "tenure",          # F=freehold, L=leasehold
    "saon", "paon", "street", "locality", "town", "district", "county",
    "ppd_category",    # A = standard sale, B = repossession/buy-to-let etc.
    "record_uri",
]

# Server-side filters: full calendar year 2025, all four property types,
# both tenures, new-build and existing stock, town = MILTON KEYNES.
PARAMS = [
    ("et[]", "lrcommon:freehold"),
    ("et[]", "lrcommon:leasehold"),
    ("limit", "6000"),            # comfortably above the ~3,700 expected rows
    ("min_date", "1 January 2025"),
    ("max_date", "31 December 2025"),
    ("nb[]", "true"),
    ("nb[]", "false"),
    ("ptype[]", "lrcommon:detached"),
    ("ptype[]", "lrcommon:semi-detached"),
    ("ptype[]", "lrcommon:terraced"),
    ("ptype[]", "lrcommon:flat-maisonette"),
    ("town", "MILTON KEYNES"),
]

BASE_URL = "http://landregistry.data.gov.uk/app/ppd/ppd_data.csv"


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    url = f"{BASE_URL}?{urlencode(PARAMS)}"
    print(f"Downloading Price Paid Data for Milton Keynes 2025...")

    response = requests.get(url, timeout=120)
    response.raise_for_status()  # fail loudly rather than saving an error page

    # Prepend our header row so downstream tools (pandas, Excel, SQLite)
    # get named columns instead of positional ones.
    header = ",".join(COLUMNS)
    OUT_FILE.write_text(header + "\n" + response.text, encoding="utf-8")

    row_count = response.text.count("\n")
    print(f"Saved {row_count:,} sales to {OUT_FILE}")


if __name__ == "__main__":
    main()
