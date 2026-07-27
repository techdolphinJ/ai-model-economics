#!/usr/bin/env python3
"""Inspect manually maintained, officially sourced API regional-availability records."""

import argparse
import datetime as dt
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CATALOG = ROOT.parent / "references" / "regional_availability.json"
EXPECTED_VENDORS = {
    "Alibaba Cloud", "Anthropic", "AWS", "Baidu", "Cohere", "DeepSeek",
    "Google", "Google Cloud", "Groq", "Microsoft", "MiniMax", "Mistral",
    "Moonshot AI", "OpenAI", "Perplexity", "SenseTime", "StepFun",
    "Tencent Cloud", "Together", "Volcengine", "Zhipu AI", "xAI",
}
VALID_STATUSES = {"sourced", "pending_official_source"}


def load_catalog():
    with CATALOG.open(encoding="utf-8") as f:
        return json.load(f)


def age_days(catalog):
    return (dt.date.today() - dt.date.fromisoformat(catalog["snapshot_date"])).days


def find_vendor(catalog, requested):
    candidates = [p for p in catalog["providers"] if requested.casefold() in p["vendor"].casefold()]
    exact = [p for p in candidates if requested.casefold() == p["vendor"].casefold()]
    if len(exact) == 1:
        return exact[0]
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise ValueError(f"Vendor not found: {requested}. Use --list for the catalog.")
    raise ValueError("Ambiguous vendor name. Choose one of:\n  " + "\n  ".join(p["vendor"] for p in candidates))


def render_list(catalog):
    print(f"Regional availability catalog | snapshot {catalog['snapshot_date']} ({age_days(catalog)} days old)")
    print("| Vendor | Catalog route(s) | Coverage | Official records |")
    print("|---|---|---|---:|")
    for provider in catalog["providers"]:
        print(f"| {provider['vendor']} | {', '.join(provider['routes'])} | {provider['coverage_status']} | {len(provider['records'])} |")


def render_vendor(catalog, provider):
    print(f"Regional availability: {provider['vendor']}")
    print(f"Catalog route(s): {', '.join(provider['routes'])}")
    print(f"Coverage: {provider['coverage_status']} | snapshot {catalog['snapshot_date']} ({age_days(catalog)} days old)")
    if provider["coverage_status"] == "pending_official_source":
        print(f"Pending: {provider['pending_reason']}")
        return

    for index, record in enumerate(provider["records"], start=1):
        source = record["source"]
        print(f"\nRecord {index}: {record['claim_type']}")
        print(f"Scope: {record['scope']}")
        if record.get("statement"):
            print(f"Statement: {record['statement']}")
        if record.get("locations"):
            print(f"Locations: {', '.join(record['locations'])}")
        if record.get("location_groups"):
            print(f"Location groups: {', '.join(record['location_groups'])}")
        if record.get("country_checks"):
            print("Country checks:")
            for country, status in record["country_checks"].items():
                print(f"- {country}: {status}")
        print(f"Source: {source['publisher']} — {source['title']}")
        print(f"URL: {source['url']}")
        print(f"Accessed: {source['accessed_date']}")


def render_country(catalog, country):
    country = country.upper()
    print(f"Documented country checks: {country} | snapshot {catalog['snapshot_date']} ({age_days(catalog)} days old)")
    found = False
    for provider in catalog["providers"]:
        for record in provider["records"]:
            status = record.get("country_checks", {}).get(country)
            if status is None:
                continue
            source = record["source"]
            print(f"- {provider['vendor']}: {status} | {source['url']}")
            found = True
    if not found:
        print("No documented country check in this snapshot. This is not a claim of availability or restriction.")


def validate(catalog):
    errors = []
    vendors = [provider.get("vendor") for provider in catalog.get("providers", [])]
    if set(vendors) != EXPECTED_VENDORS:
        errors.append("Provider coverage does not match the pricing catalog plus Volcengine.")
    if len(vendors) != len(set(vendors)):
        errors.append("Duplicate provider records found.")
    for provider in catalog.get("providers", []):
        status = provider.get("coverage_status")
        if status not in VALID_STATUSES:
            errors.append(f"{provider.get('vendor')}: unknown coverage status {status!r}.")
        records = provider.get("records", [])
        if status == "sourced" and not records:
            errors.append(f"{provider.get('vendor')}: sourced coverage requires at least one record.")
        if status == "pending_official_source" and not provider.get("pending_reason"):
            errors.append(f"{provider.get('vendor')}: pending coverage requires a pending_reason.")
        for record in records:
            source = record.get("source", {})
            if not all(source.get(key) for key in ("publisher", "title", "url", "accessed_date")):
                errors.append(f"{provider.get('vendor')}: record is missing source metadata.")
            elif not source["url"].startswith("https://"):
                errors.append(f"{provider.get('vendor')}: source URL must use HTTPS.")
    if errors:
        for error in errors:
            print(f"Validation error: {error}", file=sys.stderr)
        return 1
    print(f"Validation passed: {len(vendors)} providers, {sum(len(p['records']) for p in catalog['providers'])} sourced records.")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Inspect officially sourced API regional-availability records")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--list", action="store_true", help="List provider coverage")
    group.add_argument("--vendor", help="Show one provider's records")
    group.add_argument("--country", help="Show documented checks for an ISO 3166-1 alpha-2 country code")
    group.add_argument("--validate", action="store_true", help="Validate catalog shape and source metadata")
    args = parser.parse_args()
    catalog = load_catalog()

    if args.validate:
        sys.exit(validate(catalog))
    if args.vendor:
        try:
            render_vendor(catalog, find_vendor(catalog, args.vendor))
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            sys.exit(2)
        return
    if args.country:
        if len(args.country) != 2 or not args.country.isalpha():
            parser.error("--country must be an ISO 3166-1 alpha-2 country code")
        render_country(catalog, args.country)
        return
    render_list(catalog)


if __name__ == "__main__":
    main()
