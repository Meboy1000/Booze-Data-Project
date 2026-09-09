
import csv
import io
import time

import pandas as pd
import requests

BASE = "https://breathalcohol.iowa.gov"

COUNTIES = {
    1: "Adair", 2: "Adams", 3: "Allamakee", 4: "Appanoose", 5: "Audubon",
    6: "Benton", 7: "Black Hawk", 8: "Boone", 9: "Bremer", 10: "Buchanan",
    11: "Buena Vista", 12: "Butler", 13: "Calhoun", 14: "Carroll", 15: "Cass",
    16: "Cedar", 17: "Cerro Gordo", 18: "Cherokee", 19: "Chickasaw", 20: "Clarke",
    21: "Clay", 22: "Clayton", 23: "Clinton", 24: "Crawford", 25: "Dallas",
    26: "Davis", 27: "Decatur", 28: "Delaware", 29: "Des Moines", 30: "Dickinson",
    31: "Dubuque", 32: "Emmet", 33: "Fayette", 34: "Floyd", 35: "Franklin",
    36: "Fremont", 37: "Greene", 38: "Grundy", 39: "Guthrie", 40: "Hamilton",
    41: "Hancock", 42: "Hardin", 43: "Harrison", 44: "Henry", 45: "Howard",
    46: "Humboldt", 47: "Ida", 48: "Iowa", 49: "Jackson", 50: "Jasper",
    51: "Jefferson", 52: "Johnson", 53: "Jones", 54: "Keokuk", 55: "Kossuth",
    56: "Lee", 57: "Linn", 58: "Louisa", 59: "Lucas", 60: "Lyon",
    61: "Madison", 62: "Mahaska", 63: "Marion", 64: "Marshall", 65: "Mills",
    66: "Mitchell", 67: "Monona", 68: "Monroe", 69: "Montgomery", 70: "Muscatine",
    71: "O'Brien", 72: "Osceola", 73: "Page", 74: "Palo Alto", 75: "Plymouth",
    76: "Pocahontas", 77: "Polk", 78: "Pottawattamie", 79: "Poweshiek", 80: "Ringgold",
    81: "Sac", 82: "Scott", 83: "Shelby", 84: "Sioux", 85: "Story",
    86: "Tama", 87: "Taylor", 88: "Union", 89: "Van Buren", 90: "Wapello",
    91: "Warren", 92: "Washington", 93: "Wayne", 94: "Webster", 95: "Winnebago",
    96: "Winneshiek", 97: "Woodbury", 98: "Worth", 99: "Wright",
}


def fetch_area_csv(session, view_path):
    """Set the session's current area, then pull its exported CSV text."""
    session.get(f"{BASE}/statistics/view/{view_path}", timeout=15)
    resp = session.get(f"{BASE}/statistics/export/csv", timeout=15)
    resp.raise_for_status()
    return resp.text


def parse_annual_sections(csv_text, area_name):
    """Pull the 'Year To Date' and 'Historical Data' annual tables out of one
    area's exported CSV text and return them as a list of row dicts."""
    rows = []
    section = None
    for line in csv.reader(io.StringIO(csv_text)):
        if not line:
            continue
        if line[0] in ("By Month And Year", "Year To Date", "Historical Data"):
            section = line[0]
            continue
        if section in ("Year To Date", "Historical Data") and line[0] != "Year":
            year, avg_level, num_tests = line
            rows.append({
                "county": area_name,
                "year": int(year),
                "avg_alcohol_level_g210L": float(avg_level) if avg_level else None,
                "num_tests": int(num_tests) if num_tests else 0,
                "source": section,
            })
    return rows


def main():
    session = requests.Session()
    all_rows = []

    areas = [("statewide", "Statewide")] + [(cid, name) for cid, name in COUNTIES.items()]
    for view_path, area_name in areas:
        print(f"Fetching {area_name}...")
        csv_text = fetch_area_csv(session, view_path)
        all_rows.extend(parse_annual_sections(csv_text, area_name))
        time.sleep(0.2)  # be polite to the state's server

    df = pd.DataFrame(all_rows)

    # Where both "Year To Date" and "Historical Data" report the same
    # county/year (they overlap at 2010), keep the Year To Date value.
    df = (
        df.sort_values("source", ascending=False)  # "Year To Date" > "Historical Data"
        .drop_duplicates(subset=["county", "year"], keep="first")
        .drop(columns="source")
        .sort_values(["county", "year"])
        .reset_index(drop=True)
    )

    df.to_csv("iowa_breathalcohol_by_county_year.csv", index=False)
    print(f"Wrote {len(df)} rows to iowa_breathalcohol_by_county_year.csv")


if __name__ == "__main__":
    main()
