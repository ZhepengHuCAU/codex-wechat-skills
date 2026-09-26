#!/usr/bin/env python3
"""Download auditable CFTC Disaggregated Managed Money data; stdlib only."""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

DATASETS = {"futures-only": ("72hh-3qpy", "FutOnly"), "combined": ("kh3c-gbw2", "Combined")}
ALIASES = {"soybeans": "005602", "corn": "002602"}
FIELDS = ("report_date_as_yyyy_mm_dd", "cftc_contract_market_code",
          "market_and_exchange_names", "open_interest_all",
          "m_money_positions_long_all", "m_money_positions_short_all", "futonly_or_combined")


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def read_url(url):
    request = urllib.request.Request(url, headers={"User-Agent": "fetch-cftc-data/1.0", "Accept": "application/json"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            if attempt == 2 or (exc.code != 429 and not 500 <= exc.code < 600):
                raise
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if attempt == 2:
                raise
        time.sleep(2 ** attempt)
    raise RuntimeError("Unreachable retry state")


def download(endpoint, codes, start, end, out, page_size=5000, fetch=read_url):
    where = ("cftc_contract_market_code in (" + ",".join("'" + code + "'" for code in codes) + ")"
             + f" AND report_date_as_yyyy_mm_dd >= '{start}T00:00:00'"
             + f" AND report_date_as_yyyy_mm_dd <= '{end}T23:59:59'")
    requests = []

    def query(params, filename):
        url = endpoint + "?" + urllib.parse.urlencode(params)
        raw = fetch(url)
        value = json.loads(raw)
        if not isinstance(value, list):
            raise ValueError(f"API did not return a row array: {filename}")
        (out / "raw_pages" / filename).write_bytes(raw)
        requests.append({"file": "raw_pages/" + filename, "url": url,
                         "sha256": hashlib.sha256(raw).hexdigest(), "rows": len(value)})
        return value

    (out / "raw_pages").mkdir()
    before = int(query({"$select": "count(*) as n", "$where": where}, "count_before.json")[0]["n"])
    if before == 0:
        raise ValueError("No rows for requested codes, dates, and report")
    rows = []
    for offset in range(0, before, page_size):
        page = query({"$select": ",".join(FIELDS), "$where": where,
                      "$order": "report_date_as_yyyy_mm_dd,cftc_contract_market_code",
                      "$limit": str(page_size), "$offset": str(offset)}, f"page_{offset:08d}.json")
        expected = min(page_size, before - offset)
        if len(page) != expected:
            raise ValueError(f"Incomplete or changing API page: offset={offset}, expected={expected}, got={len(page)}")
        rows.extend(page)
    after = int(query({"$select": "count(*) as n", "$where": where}, "count_after.json")[0]["n"])
    if before != after or len(rows) != before:
        raise ValueError("API row count changed during download; rerun into a new output directory")
    return rows, {"source_mode": "live_api", "requests": requests, "count_before": before,
                  "count_after": after, "count_matches": True}


def number(value, field):
    if isinstance(value, bool) or value is None or str(value).strip() == "":
        raise ValueError(f"Missing/invalid numeric field: {field}")
    n = float(value)
    if not math.isfinite(n) or n < 0:
        raise ValueError(f"Invalid negative/nonfinite value: {field}={value}")
    return int(n) if n.is_integer() else n


def normalize(raw, codes, start, end, variant):
    clean, seen, warnings = [], set(), []
    for r in raw:
        missing = [f for f in FIELDS if f not in r or r[f] is None]
        if missing:
            raise ValueError(f"Missing required fields: {missing}")
        date = dt.date.fromisoformat(r[FIELDS[0]][:10])
        code = str(r[FIELDS[1]])
        if code not in codes or not start <= date <= end:
            raise ValueError(f"Record outside requested filters: {date}, {code}")
        if r["futonly_or_combined"] != variant:
            raise ValueError(f"Mixed/wrong report variant: {date}, {code}, {r['futonly_or_combined']}")
        key = (date, code)
        if key in seen:
            raise ValueError(f"Duplicate market/date: {key}")
        seen.add(key)
        long = number(r["m_money_positions_long_all"], "long")
        short = number(r["m_money_positions_short_all"], "short")
        oi = number(r["open_interest_all"], "open_interest")
        if max(long, short) > oi:
            warnings.append(f"{code} {date}: Managed Money side exceeds total open interest")
        if oi == 0:
            warnings.append(f"{code} {date}: zero open interest; net/OI left blank")
        iso_year, iso_week, _ = date.isocalendar()
        clean.append({"date": str(date), "contract_code": code, "market": r["market_and_exchange_names"],
                      "report_variant": variant, "long": long, "short": short, "net": long - short,
                      "open_interest": oi, "net_share_oi_pct": round((long-short)/oi*100, 6) if oi else None,
                      "calendar_year": date.year, "iso_year": iso_year, "iso_week": iso_week})
    missing_codes = sorted(set(codes) - {r["contract_code"] for r in clean})
    if missing_codes:
        raise ValueError(f"No data for requested markets: {missing_codes}")
    return sorted(clean, key=lambda r: (r["date"], r["contract_code"])), warnings


def compare(rows, target_date=None, method="iso-week"):
    """One market, normalized rows. Never includes observations after target_date."""
    target = target_date or max(r["date"] for r in rows)
    found = [r for r in rows if r["date"] == target]
    if len(found) != 1:
        raise ValueError(f"Comparison date must exist exactly once: {target}")
    current = found[0]
    eligible = sorted((r for r in rows if r["date"] <= target), key=lambda r: r["date"])
    sample, missing = [], []
    if method == "iso-week":
        year_key = "iso_year"
        first, last = eligible[0][year_key], current[year_key]
        for year in range(first, last + 1):
            match = [r for r in eligible if r[year_key] == year and r["iso_week"] == current["iso_week"]]
            if len(match) > 1:
                raise ValueError(f"Multiple reports in ISO year/week: {year}/{current['iso_week']}")
            if match:
                sample.append(match[0])
            else:
                missing.append(year)
        definition = f"Same ISO week {current['iso_week']}, grouped by ISO year"
    else:
        year_key = "calendar_year"
        first, last = eligible[0][year_key], current[year_key]
        target_day = dt.date.fromisoformat(target)
        for year in range(first, last + 1):
            try:
                anchor = target_day.replace(year=year)
            except ValueError:
                anchor = dt.date(year, 2, 28)
            candidates = [r for r in eligible if r[year_key] == year
                          and abs((dt.date.fromisoformat(r["date"]) - anchor).days) <= 3]
            if candidates:
                sample.append(min(candidates, key=lambda r: (abs((dt.date.fromisoformat(r['date']) - anchor).days), r['date'])))
            else:
                missing.append(year)
        definition = "Same month/day +/-3 calendar days; closest report, earlier on ties; Feb 29 maps to Feb 28"
    prior = [r for r in sample if r[year_key] < current[year_key]]
    prior_max = max((r["net"] for r in prior), default=None)
    maximum = max(r["net"] for r in eligible)
    rank = 1 + sum(r["net"] > current["net"] for r in sample)
    ties = sum(r["net"] == current["net"] for r in sample)
    return {"comparison_date": target, "current": current, "method": method, "definition": definition,
            "history_start": eligible[0]["date"], "history_end": target,
            "elapsed_history_years": round((dt.date.fromisoformat(target)-dt.date.fromisoformat(eligible[0]['date'])).days/365.2425, 3),
            "first_comparison_year": first, "last_comparison_year": last,
            "sample_years": len(sample), "missing_years": missing,
            "rank_descending": rank, "ties_at_current_value": ties,
            "strict_seasonal_record": prior_max is not None and current["net"] > prior_max,
            "prior_seasonal_max": prior_max,
            "prior_seasonal_max_rows": [r for r in prior if r["net"] == prior_max],
            "seasonal_rows": sample, "full_downloaded_sample_max": maximum,
            "full_downloaded_sample_max_rows": [r for r in eligible if r["net"] == maximum],
            "claim_scope": "Downloaded observations only; confirm official inception and missing years before asserting a historical record"}


def quality(rows, codes, end):
    coverage, warnings = {}, []
    for code in codes:
        market = [r for r in rows if r["contract_code"] == code]
        dates = sorted(dt.date.fromisoformat(r["date"]) for r in market)
        gaps = [{"from": str(a), "to": str(b), "days": (b-a).days}
                for a, b in zip(dates, dates[1:]) if (b-a).days > 10]
        coverage[code] = {"rows": len(market), "start": str(dates[0]), "end": str(dates[-1]),
                          "names": sorted({r["market"] for r in market}), "gaps_over_10_days": gaps}
        if gaps:
            warnings.append(f"{code}: {len(gaps)} gaps exceed 10 days; verify official release history")
        if (end-dates[-1]).days > 14:
            warnings.append(f"{code}: latest observation is more than 14 days before requested end")
    if len({v["end"] for v in coverage.values()}) > 1:
        warnings.append("Requested markets have different latest observation dates")
    return coverage, warnings


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    markets = parser.add_mutually_exclusive_group()
    markets.add_argument("--commodities", help="Comma-separated soybeans,corn (default)")
    markets.add_argument("--codes", help="Comma-separated official six-character market codes")
    parser.add_argument("--report", choices=DATASETS, default="futures-only")
    parser.add_argument("--start", type=dt.date.fromisoformat, default=dt.date(2006, 1, 1))
    parser.add_argument("--end", type=dt.date.fromisoformat, default=dt.datetime.now(dt.timezone.utc).date())
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--raw-input", type=Path, help="Replay a raw row array or this script's raw.json offline")
    parser.add_argument("--compare-date", type=dt.date.fromisoformat)
    parser.add_argument("--comparison", choices=("iso-week", "nearest-date"), default="iso-week")
    parser.add_argument("--page-size", type=int, default=5000)
    args = parser.parse_args(argv)
    if args.codes:
        codes = [c.strip() for c in args.codes.split(",")]
    else:
        names = [c.strip().lower() for c in (args.commodities or "soybeans,corn").split(",")]
        if any(name not in ALIASES for name in names):
            parser.error("Unknown commodity alias; verify the CFTC market code and use --codes")
        codes = [ALIASES[name] for name in names]
    if any(not re.fullmatch(r"[0-9A-Z]{6}", code) for code in codes) or len(set(codes)) != len(codes):
        parser.error("Use distinct six-character CFTC market codes, preserving leading zeroes")
    if args.start > args.end or not 1 <= args.page_size <= 10000:
        parser.error("start must not exceed end; page-size must be 1..10000")
    if args.compare_date and not args.start <= args.compare_date <= args.end:
        parser.error("compare-date must fall inside the requested date range")
    if args.out_dir.exists() and any(args.out_dir.iterdir()):
        parser.error("Output directory is nonempty; choose a new directory")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    dataset, variant = DATASETS[args.report]
    endpoint = f"https://publicreporting.cftc.gov/resource/{dataset}.json"
    if args.raw_input:
        raw_bytes = args.raw_input.read_bytes()
        payload = json.loads(raw_bytes)
        if isinstance(payload, dict) and payload.get("dataset_id", dataset) != dataset:
            raise ValueError("Raw-input dataset does not match requested report")
        raw = payload["rows"] if isinstance(payload, dict) else payload
        if not isinstance(raw, list):
            raise ValueError("Raw input must contain an array of official CFTC rows")
        raw = [r for r in raw if str(r.get(FIELDS[1])) in codes
               and str(args.start) <= r.get(FIELDS[0], "")[:10] <= str(args.end)]
        source = {"source_mode": "offline_replay", "input_file": str(args.raw_input.resolve()),
                  "input_sha256": hashlib.sha256(raw_bytes).hexdigest(), "count_matches": None,
                  "note": "No live freshness or API completeness check; original file provenance must be verified"}
    else:
        raw, source = download(endpoint, codes, args.start, args.end, args.out_dir, args.page_size)
    rows, warnings = normalize(raw, codes, args.start, args.end, variant)
    coverage, quality_warnings = quality(rows, codes, args.end)
    summary = {code: compare([r for r in rows if r["contract_code"] == code],
                             str(args.compare_date) if args.compare_date else None, args.comparison) for code in codes}
    generated = dt.datetime.now(dt.timezone.utc).isoformat()
    write_json(args.out_dir / "raw.json", {"dataset_id": dataset, "endpoint": endpoint,
               "processed_at_utc": generated, "source": source, "rows": raw})
    with (args.out_dir / "positions.csv").open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    write_json(args.out_dir / "summary.json", summary)
    hashes = {name: hashlib.sha256((args.out_dir / name).read_bytes()).hexdigest()
              for name in ("raw.json", "positions.csv", "summary.json")}
    manifest = {"status": "complete", "processed_at_utc": generated, "dataset_id": dataset,
                "endpoint": endpoint, "report": args.report, "category": "Managed Money",
                "requested_start": str(args.start), "requested_end": str(args.end), "codes": codes,
                "rows": len(rows), "coverage": coverage, "warnings": warnings + quality_warnings,
                "source": source, "output_sha256": hashes}
    write_json(args.out_dir / "manifest.json", manifest)
    print(json.dumps({"output": str(args.out_dir.resolve()), "rows": len(rows), "coverage": coverage,
                      "warnings": manifest["warnings"], "source_mode": source["source_mode"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, KeyError, OSError, urllib.error.URLError) as exc:
        print(f"CFTC download failed: {exc}", file=sys.stderr)
        sys.exit(1)
