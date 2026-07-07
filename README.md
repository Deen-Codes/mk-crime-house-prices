# Crime & House Prices in Milton Keynes, 2025

**Do house prices track street crime across Milton Keynes postcode districts?**
An end-to-end analysis of 3,170 property sales (HM Land Registry) and 26,650
street-level crimes (police.uk) across 17 MK postcode districts, using Python,
SQL, Excel and Power BI.

**[→ Live interactive dashboard](https://deen-codes.github.io/mk-crime-house-prices/)**
(GitHub Pages, built from `docs/index.html`)

> **Headline:** districts with more recorded crime sell for less. The
> correlation between total crimes and median sale price across districts is
> **−0.62** — a strong negative relationship, though not a causal one (see
> Limitations).

---

## Key findings

**1. The price–crime gradient is steep.** MK17 (Woburn Sands & villages) had
the highest median price (£465,000) and just 34 recorded crimes all year.
MK9 (Central Milton Keynes) had the lowest median price (£230,000) and the
second-highest crime count (4,714). Correlation across all 17 districts: −0.62.

**2. City-centre crime is a different kind of crime.** MK9's crime is
dominated by shoplifting (1,413 — more than half the city's total of 2,959),
concentrated around the shopping centre. Retail-driven crime inflates the
centre's numbers without necessarily saying much about residential streets —
one reason correlation isn't causation here.

**3. Violent crime was the city's largest category in 2025** — 10,498
incidents, 39% of all recorded crime, ahead of shoplifting (2,959) and
anti-social behaviour (2,802).

**4. Property type explains the centre's low prices as much as crime does.**
MK9's stock is mostly flats (city-wide flat median: £181,250 vs detached:
£525,000). Low prices in the centre reflect what's being sold, not just
where — a confound the analysis has to acknowledge.

**5. The city-wide median sale price in 2025 was £350,000**, with monthly
medians and crime totals tracked in `data/processed/monthly_trends.csv`.

<!-- TODO: add your Excel and Power BI screenshots here once built:
![Power BI dashboard](powerbi/dashboard.png)
![Excel pivot analysis](excel/pivots.png)
-->

---

## How it's built

```
scripts/01_fetch_prices.py    HM Land Registry Price Paid Data -> data/raw/
scripts/02_fetch_crime.py     police.uk API, 17 outcodes x 12 months -> data/raw/
scripts/03_clean_and_join.py  cleaning log + the outcode-level join -> data/processed/
scripts/04_build_database.py  SQLite database for the SQL analysis -> data/
sql/analysis_queries.sql      10 analysis questions (joins, CTEs, window functions)
excel/                        pivot-table workbook (see excel/INSTRUCTIONS.md)
powerbi/                      dashboard (see powerbi/INSTRUCTIONS.md)
```

Reproduce everything:

```bash
pip install -r requirements.txt
python scripts/01_fetch_prices.py
python scripts/02_fetch_crime.py      # ~200 API calls, cached; re-run resumes
python scripts/03_clean_and_join.py
python scripts/04_build_database.py
sqlite3 data/mk_analysis.db           # then: .read sql/analysis_queries.sql
```

## Data cleaning decisions

All cleaning is logged in `scripts/03_clean_and_join.py` and printed on each
run. Summary: category-A sales only (repossessions/company transactions
excluded), MK outcodes only, price sanity window £30k–£2m, crimes
de-duplicated by ID across overlapping search radii. Raw rows 3,724 → clean
3,170.

## Limitations (read before quoting numbers)

- **Correlation ≠ causation.** Crime and prices share confounds: property
  type mix, retail footfall, transport links, deprivation.
- **Crime geography is approximate.** Crimes are fetched within a 1-mile
  radius of each outcode centroid — adjacent-district overlap is
  de-duplicated by crime ID, but edges of large districts may be
  under-counted, and centroid placement matters: MK1's centroid sits in a
  retail park, giving it 2,905 crimes against only 8 residential sales, so
  its per-sale figure is excluded from interpretation.
- **No population denominator.** Crimes per resident would be the honest
  rate; outcode-level population isn't in either dataset, so `crimes_per_sale`
  is a rough intensity proxy only.
- **Police-recorded crime under-counts true crime**, and anonymised
  street-level locations are deliberately fuzzed by police.uk.
- **One year, one city.** 2025 only; no claim these patterns hold elsewhere.

## Data sources & licences

- [HM Land Registry Price Paid Data](https://www.gov.uk/government/collections/price-paid-data)
  — © Crown copyright, [OGL v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/)
- [police.uk street-level crime API](https://data.police.uk/docs/)
  — © Crown copyright, OGL v3.0
- Outcode centroids: [postcodes.io](https://postcodes.io) (open source)

## Author

**Deen Ali** — [github.com/deen-codes](https://github.com/deen-codes) ·
[linkedin.com/in/deen321](https://linkedin.com/in/deen321)
