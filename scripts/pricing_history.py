#!/usr/bin/env python3
"""Inspect and validate the source-bound SKU price-change catalog."""

import argparse
import json
from datetime import date
from pathlib import Path


CATALOG = Path(__file__).resolve().parent.parent / "references" / "pricing_history.json"
EXPECTED_VENDORS = {
    "Volcengine",
    "Moonshot AI",
    "Zhipu AI",
    "MiniMax",
    "Alibaba Cloud",
    "OpenAI",
    "Anthropic",
    "Google",
}
VALID_STATUSES = {"sourced", "pending_official_source"}
SOURCE_FIELDS = {"publisher", "title", "url", "accessed_date", "evidence"}


def load_catalog():
    with CATALOG.open(encoding="utf-8") as handle:
        return json.load(handle)


def counts(provider):
    histories = provider["sku_histories"]
    return len(histories), sum(len(item["events"]) for item in histories)


def format_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(", ", ": "))


def print_list(catalog):
    print("Vendor | Catalog route(s) | Coverage | SKU histories | Events")
    print("-" * 86)
    for provider in catalog["providers"]:
        sku_count, event_count = counts(provider)
        print(
            f"{provider['vendor']} | {', '.join(provider['routes'])} | "
            f"{provider['coverage_status']} | {sku_count} | {event_count}"
        )


def print_provider(provider):
    sku_count, event_count = counts(provider)
    print(f"Vendor: {provider['vendor']}")
    print(f"Catalog route(s): {', '.join(provider['routes'])}")
    print(f"Coverage: {provider['coverage_status']} ({sku_count} SKU histories, {event_count} events)")
    if provider.get("scope"):
        print(f"Scope: {provider['scope']}")
    if provider["coverage_status"] == "pending_official_source":
        print(f"Pending reason: {provider['pending_reason']}")
        return

    for history in provider["sku_histories"]:
        print(f"\nSKU: {history['sku_id']}")
        if history.get("applies_to"):
            print(f"Applies to: {', '.join(history['applies_to'])}")
        print(f"Unit: {history['currency']} {history['unit']}")
        for event in history["events"]:
            source = event["source"]
            print(f"  Effective date: {event['effective_date']}")
            print(f"  Before: {format_json(event['before'])}")
            print(f"  After: {format_json(event['after'])}")
            print(f"  Source: {source['title']} — {source['url']}")
            print(f"  Accessed: {source['accessed_date']}; evidence: {source['evidence']}")


def matching_providers(catalog, sku):
    needle = sku.casefold()
    matches = []
    for provider in catalog["providers"]:
        matched_histories = []
        for history in provider["sku_histories"]:
            candidates = [history["sku_id"], *history.get("applies_to", [])]
            if any(needle in candidate.casefold() for candidate in candidates):
                matched_histories.append(history)
        if matched_histories:
            matches.append((provider, matched_histories))
    return matches


def print_sku(catalog, sku):
    matches = matching_providers(catalog, sku)
    if not matches:
        print(f"No sourced SKU history matched: {sku}")
        return 1
    for provider, histories in matches:
        print(f"Vendor: {provider['vendor']}")
        for history in histories:
            print(f"SKU: {history['sku_id']}")
            if history.get("applies_to"):
                print(f"Applies to: {', '.join(history['applies_to'])}")
            print(f"Unit: {history['currency']} {history['unit']}")
            for event in history["events"]:
                source = event["source"]
                print(f"  Effective date: {event['effective_date']}")
                print(f"  Before: {format_json(event['before'])}")
                print(f"  After: {format_json(event['after'])}")
                print(f"  Source: {source['title']} — {source['url']}")
    return 0


def validate(catalog):
    errors = []
    providers = catalog.get("providers", [])
    vendor_names = [provider.get("vendor") for provider in providers]
    if set(vendor_names) != EXPECTED_VENDORS:
        errors.append("Vendor set does not match the first-version priority scope.")
    if len(vendor_names) != len(set(vendor_names)):
        errors.append("Vendor names must be unique.")

    event_ids = set()
    for provider in providers:
        vendor = provider.get("vendor", "<unknown>")
        status = provider.get("coverage_status")
        if status not in VALID_STATUSES:
            errors.append(f"{vendor}: unsupported coverage status {status!r}.")
        if not provider.get("routes"):
            errors.append(f"{vendor}: catalog route is required.")
        histories = provider.get("sku_histories")
        if not isinstance(histories, list):
            errors.append(f"{vendor}: sku_histories must be an array.")
            continue
        if status == "pending_official_source":
            if histories:
                errors.append(f"{vendor}: pending provider must not contain unsourced events.")
            if not provider.get("pending_reason"):
                errors.append(f"{vendor}: pending provider needs a pending_reason.")
            continue
        if not histories:
            errors.append(f"{vendor}: sourced provider needs at least one SKU history.")
        for history in histories:
            sku_id = history.get("sku_id")
            events = history.get("events")
            if not sku_id or not isinstance(events, list) or not events:
                errors.append(f"{vendor}: each sourced SKU history needs a sku_id and events.")
                continue
            last_date = None
            for event in events:
                event_id = event.get("event_id")
                if not event_id or event_id in event_ids:
                    errors.append(f"{vendor}/{sku_id}: event IDs must be present and globally unique.")
                event_ids.add(event_id)
                try:
                    event_date = date.fromisoformat(event["effective_date"])
                except (KeyError, TypeError, ValueError):
                    errors.append(f"{vendor}/{sku_id}: effective_date must be ISO YYYY-MM-DD.")
                    continue
                if last_date and event_date < last_date:
                    errors.append(f"{vendor}/{sku_id}: events must be ordered by immutable effective_date.")
                last_date = event_date
                if not history.get("currency") or not history.get("unit"):
                    errors.append(f"{vendor}/{sku_id}: SKU history needs a currency and pricing unit.")
                if not isinstance(event.get("before"), dict) or not event["before"]:
                    errors.append(f"{vendor}/{sku_id}: event needs exact before values.")
                if not isinstance(event.get("after"), dict) or not event["after"]:
                    errors.append(f"{vendor}/{sku_id}: event needs exact after values.")
                source = event.get("source")
                if not isinstance(source, dict) or not SOURCE_FIELDS.issubset(source):
                    errors.append(f"{vendor}/{sku_id}: event source lacks required provenance fields.")
                elif not source["url"].startswith("https://"):
                    errors.append(f"{vendor}/{sku_id}: source URL must use HTTPS.")
                else:
                    try:
                        date.fromisoformat(source["accessed_date"])
                    except (TypeError, ValueError):
                        errors.append(f"{vendor}/{sku_id}: source accessed_date must be ISO YYYY-MM-DD.")
    if errors:
        print("Validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    history_count = sum(counts(provider)[0] for provider in providers)
    event_count = sum(counts(provider)[1] for provider in providers)
    print(
        f"Validation passed: {len(providers)} providers, {history_count} SKU histories, "
        f"{event_count} price-change events."
    )
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--list", action="store_true", help="List vendors and history coverage.")
    group.add_argument("--vendor", help="Show one vendor's sourced events or pending reason.")
    group.add_argument("--sku", help="Find a sourced SKU history by ID or covered alias.")
    group.add_argument("--validate", action="store_true", help="Validate catalog structure and provenance fields.")
    args = parser.parse_args()
    catalog = load_catalog()
    if args.validate:
        return validate(catalog)
    if args.vendor:
        provider = next(
            (item for item in catalog["providers"] if item["vendor"].casefold() == args.vendor.casefold()),
            None,
        )
        if provider is None:
            parser.error(f"Unknown vendor: {args.vendor}")
        print_provider(provider)
        return 0
    if args.sku:
        return print_sku(catalog, args.sku)
    print_list(catalog)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
