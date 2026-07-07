"""
03_clean_and_join.py
--------------------
Cleans both raw datasets and produces the four analysis-ready CSVs that
Excel, Power BI and SQL all work from. Every cleaning decision is stated
in a comment — an analysis is only as credible as its cleaning log.

Inputs:
  data/raw/price_paid_mk_2025.csv
  data/raw/crime_street_mk_2025.csv

Outputs (data/processed/):
  prices_clean.csv            one row per sale, typed and filtered
  crime_by_outcode_month.csv  crime counts by outcode x month x category
  outcode_summary.csv         THE JOIN: price stats + crime stats per outcode
  monthly_trends.csv          city-wide monthly medians and crime totals

Run:  python scripts/03_clean_and_join.py   (from the repo root, after 01+02)
"""

from pathlib import Path

import pandas as pd

RAW = Path("data/raw")
OUT = Path("data/processed")

# Human-readable labels for the PPD single-letter codes.
PROPERTY_TYPES = {"D": "Detached", "S": "Semi-detached", "T": "Terraced", "F": "Flat"}


def clean_prices() -> pd.DataFrame:
    df = pd.read_csv(RAW / "price_paid_mk_2025.csv")
    n0 = len(df)

    # -- Cleaning decisions (each one logged to the console) ------------------
    # 1. Category A sales only: category B covers repossessions, buy-to-lets
    #    bought through companies etc., which distort market price.
    df = df[df["ppd_category"] == "A"]

    # 2. Milton Keynes outcodes only: the postal town includes a handful of
    #    stray rows (e.g. LU7) and blank postcodes we cannot place.
    df = df.dropna(subset=["postcode"])
    df["outcode"] = df["postcode"].str.split().str[0]
    df = df[df["outcode"].str.match(r"^MK\d+$")]

    # 3. Price sanity window £30k-£2m: below is not a market sale (ground
    #    rents, part-transfers), above is a handful of outliers that would
    #    drag averages around. Medians are used downstream anyway.
    df["price"] = pd.to_numeric(df["price"])
    df = df[df["price"].between(30_000, 2_000_000)]

    # 4. Typed date + month column to join against crime months.
    df["date_of_transfer"] = pd.to_datetime(df["date_of_transfer"])
    df["month"] = df["date_of_transfer"].dt.strftime("%Y-%m")
    df["property_type_label"] = df["property_type"].map(PROPERTY_TYPES)
    df["new_build"] = df["new_build"].eq("Y")

    print(f"prices: {n0:,} raw -> {len(df):,} clean "
          f"({n0 - len(df):,} removed by filters above)")

    keep = ["transaction_id", "price", "date_of_transfer", "month", "postcode",
            "outcode", "property_type", "property_type_label", "new_build",
            "tenure", "street", "locality", "district"]
    return df[keep].sort_values("date_of_transfer")


def aggregate_crime() -> pd.DataFrame:
    df = pd.read_csv(RAW / "crime_street_mk_2025.csv")
    print(f"crime:  {len(df):,} unique street-level crimes loaded")

    # Long format: one row per outcode x month x category, ready for pivots.
    agg = (df.groupby(["outcode", "month", "category"])
             .size()
             .reset_index(name="crime_count"))
    return agg


def build_outcode_summary(prices: pd.DataFrame, crime: pd.DataFrame) -> pd.DataFrame:
    """The core join: one row per outcode with price and crime measures."""
    price_stats = (prices.groupby("outcode")
                   .agg(sales=("price", "size"),
                        median_price=("price", "median"),
                        mean_price=("price", "mean"))
                   .round(0))

    crime_totals = (crime.groupby("outcode")["crime_count"].sum()
                    .rename("total_crimes"))

    # Violent crime broken out separately: it is the category buyers say
    # they care about most, and it behaves differently from e.g. shoplifting.
    violent = (crime[crime["category"] == "violent-crime"]
               .groupby("outcode")["crime_count"].sum()
               .rename("violent_crimes"))

    summary = (price_stats
               .join(crime_totals)
               .join(violent)
               .fillna(0)
               .reset_index())

    # Crimes per sale is NOT crime per resident — we have no population
    # denominator at outcode level. See README "Limitations".
    summary["crimes_per_sale"] = (summary["total_crimes"] / summary["sales"]).round(1)
    return summary.sort_values("median_price", ascending=False)


def build_monthly_trends(prices: pd.DataFrame, crime: pd.DataFrame) -> pd.DataFrame:
    """City-wide month-by-month view for trend charts."""
    monthly_price = (prices.groupby("month")
                     .agg(sales=("price", "size"), median_price=("price", "median")))
    monthly_crime = (crime.groupby("month")["crime_count"].sum()
                     .rename("total_crimes"))
    return monthly_price.join(monthly_crime).reset_index()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    prices = clean_prices()
    crime = aggregate_crime()
    summary = build_outcode_summary(prices, crime)
    trends = build_monthly_trends(prices, crime)

    prices.to_csv(OUT / "prices_clean.csv", index=False)
    crime.to_csv(OUT / "crime_by_outcode_month.csv", index=False)
    summary.to_csv(OUT / "outcode_summary.csv", index=False)
    trends.to_csv(OUT / "monthly_trends.csv", index=False)

    # Headline number for the README: how related are crime and price?
    corr = summary["total_crimes"].corr(summary["median_price"])
    print(f"\nOutcode summary ({len(summary)} districts):")
    print(summary.to_string(index=False))
    print(f"\nCorrelation, total crimes vs median price: {corr:.2f}")


if __name__ == "__main__":
    main()
