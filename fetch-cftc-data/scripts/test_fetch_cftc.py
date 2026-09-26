"""Synthetic invariants: financial definitions, missing history, pagination, and dates."""
import datetime as dt
import json
from pathlib import Path
import tempfile
import unittest
import urllib.parse

from fetch_cftc import FIELDS, compare, download, normalize


def raw(date, long=100, short=30, oi=1000, variant="FutOnly"):
    return dict(zip(FIELDS, [date + "T00:00:00.000", "005602", "SOYBEANS - TEST FIXTURE",
                             str(oi), str(long), str(short), variant]))


def clean(records, variant="FutOnly"):
    return normalize(records, ["005602"], dt.date(2000, 1, 1), dt.date(2030, 12, 31), variant)[0]


class DataTests(unittest.TestCase):
    def test_negative_net_zero_oi_and_holiday_date(self):
        rows, warnings = normalize([raw("2006-07-03", 20, 80), raw("2006-07-11", 0, 0, 0)],
                                  ["005602"], dt.date(2006, 1, 1), dt.date(2006, 12, 31), "FutOnly")
        self.assertEqual(rows[0]["date"], "2006-07-03")
        self.assertEqual(rows[0]["net"], -60)
        self.assertEqual(rows[0]["net_share_oi_pct"], -6)
        self.assertIsNone(rows[1]["net_share_oi_pct"])
        self.assertTrue(warnings)

    def test_reject_duplicates_and_wrong_variant(self):
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            clean([raw("2020-09-22"), raw("2020-09-22")])
        with self.assertRaisesRegex(ValueError, "variant"):
            clean([raw("2020-09-22", variant="Combined")])
        with self.assertRaisesRegex(ValueError, "negative"):
            clean([raw("2020-09-22", long=-1)])

    def test_combined_preserves_fraction(self):
        self.assertEqual(clean([raw("2020-09-22", long=100.5, variant="Combined")], "Combined")[0]["net"], 70.5)

    def test_tie_is_not_new_record_and_no_future_leak(self):
        rows = clean([raw("2019-09-24"), raw("2020-09-22"), raw("2021-09-28", long=500)])
        result = compare(rows, "2020-09-22")
        self.assertEqual(result["rank_descending"], 1)
        self.assertEqual(result["ties_at_current_value"], 2)
        self.assertFalse(result["strict_seasonal_record"])
        self.assertEqual(result["full_downloaded_sample_max"], 70)

    def test_missing_year_and_short_history(self):
        rows = clean([raw("2018-09-25"), raw("2020-09-22", long=200)])
        result = compare(rows)
        self.assertEqual(result["missing_years"], [2019])
        self.assertTrue(result["strict_seasonal_record"])
        self.assertEqual(result["sample_years"], 2)
        self.assertLess(result["elapsed_history_years"], 3)
        self.assertFalse(compare(rows[-1:])["strict_seasonal_record"])

    def test_iso_year_boundary(self):
        rows = clean([raw("2019-01-01"), raw("2019-12-31", long=200)])
        self.assertEqual(rows[-1]["calendar_year"], 2019)
        self.assertEqual(rows[-1]["iso_year"], 2020)
        self.assertEqual(compare(rows)["sample_years"], 2)

    def test_nearest_date_and_missing_target(self):
        rows = clean([raw("2019-09-24"), raw("2020-09-22", long=200)])
        self.assertTrue(compare(rows, method="nearest-date")["strict_seasonal_record"])
        with self.assertRaisesRegex(ValueError, "must exist"):
            compare(rows, "2020-09-23")

    def test_paginated_count_reconciliation(self):
        records = [raw("2020-09-08"), raw("2020-09-15"), raw("2020-09-22")]

        def fake(url):
            query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
            if query["$select"] == ["count(*) as n"]:
                value = [{"n": "3"}]
            else:
                offset, limit = int(query["$offset"][0]), int(query["$limit"][0])
                value = records[offset:offset+limit]
            return json.dumps(value).encode()

        with tempfile.TemporaryDirectory() as directory:
            data, metadata = download("https://example.invalid", ["005602"], dt.date(2020, 9, 1),
                                      dt.date(2020, 9, 30), Path(directory), 2, fake)
            self.assertEqual(len(data), 3)
            self.assertTrue(metadata["count_matches"])
            self.assertEqual(len(metadata["requests"]), 4)

    def test_truncated_api_page_fails(self):
        def fake(url):
            return b'[{"n":"3"}]' if "count" in urllib.parse.unquote(url) else b'[]'
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "Incomplete"):
                download("https://example.invalid", ["005602"], dt.date(2020, 9, 1),
                         dt.date(2020, 9, 30), Path(directory), 2, fake)


if __name__ == "__main__":
    unittest.main()
