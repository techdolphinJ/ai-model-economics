#!/usr/bin/env python3
"""按公开 API 快照核算文本模型 token 成本。

不做汇率转换；币种、接入路由和吞吐档必须由调用者明确选择。
数据源：references/model_prices.json（快照超过 90 天自动告警）。
"""

import argparse
import datetime as dt
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CATALOG = ROOT.parent / "references" / "model_prices.json"


def load_catalog():
    with CATALOG.open(encoding="utf-8") as f:
        return json.load(f)


def model_key(row):
    return f"{row['vendor']}/{row['route']}/{row['model']}"


def find_model(catalog, requested):
    candidates = [r for r in catalog["models"] if requested.casefold() in model_key(r).casefold()]
    exact = [r for r in candidates if requested.casefold() == model_key(r).casefold()]
    if len(exact) == 1:
        return exact[0]
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise ValueError(f"Model not found: {requested}. Use --list for full keys.")
    raise ValueError("Ambiguous model name. Provide the full vendor/route/model:\n  " + "\n  ".join(model_key(r) for r in candidates))


def price(row, mode, input_tokens, cached_input_tokens, output_tokens, requests=0):
    if cached_input_tokens > input_tokens:
        raise ValueError("Cached input tokens cannot exceed input tokens.")
    rates = row["prices"].get(mode)
    if not rates:
        available = ", ".join(row["prices"])
        raise ValueError(f"No public price — returned as null, not estimated. Available modes: {available}")
    if rates.get("input") is None or rates.get("output") is None:
        raise ValueError("No public price — returned as null, not estimated.")

    cached_rate = rates.get("cached_input")
    if cached_input_tokens and cached_rate is None:
        raise ValueError("No public price — returned as null, not estimated.")

    uncached = input_tokens - cached_input_tokens
    per_million = 1_000_000
    items = [
        ("Uncached input", uncached, rates["input"]),
        ("Cached input", cached_input_tokens, cached_rate or 0),
        ("Output", output_tokens, rates["output"]),
    ]
    total = sum(tokens / per_million * unit for _, tokens, unit in items)
    request_fee = row.get("request_fee_per_1k")
    if requests and request_fee is not None:
        items.append(("Request surcharge", requests, request_fee, "per 1K requests"))
        total += requests / 1_000 * request_fee
    return items, total


def main():
    ap = argparse.ArgumentParser(description="Public API text-token cost calculator")
    ap.add_argument("--model", help="Full or unique vendor/route/model key")
    ap.add_argument("--input-tokens", type=int, default=0)
    ap.add_argument("--cached-input-tokens", type=int, default=0)
    ap.add_argument("--output-tokens", type=int, default=0)
    ap.add_argument("--requests", type=int, default=0, help="Request count; included only when the SKU publishes a per-request surcharge")
    ap.add_argument("--mode", default="standard", choices=["standard", "batch", "flex", "priority"])
    ap.add_argument("--list", action="store_true", help="List priceable models")
    args = ap.parse_args()
    catalog = load_catalog()

    if args.list:
        for row in catalog["models"]:
            modes = ",".join(row["prices"])
            print(f"{model_key(row)}  [{row['currency']}; {modes}; {row['lifecycle']}]")
        return
    if not args.model:
        ap.error("--model is required (or use --list)")

    try:
        row = find_model(catalog, args.model)
        items, total = price(row, args.mode, args.input_tokens, args.cached_input_tokens, args.output_tokens, args.requests)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(2)

    snapshot = dt.date.fromisoformat(row["snapshot_date"])
    age = (dt.date.today() - snapshot).days
    if age > catalog["stale_after_days"]:
        print(f"⚠️ Snapshot {snapshot} is {age} days old. Verify the official page before formal pricing.\n")

    print(f"Cost: {total:.6f} {row['currency']}")
    print(f"Pricing basis: {model_key(row)} | {args.mode} | snapshot {snapshot} ({age} days old)")
    print("| Item | Usage | Unit price | Subtotal |")
    print("|---|---:|---:|---:|")
    for item in items:
        if len(item) == 4:
            label, units, unit, basis = item
            cost = units / 1_000 * unit
            print(f"| {label} | {units:,} requests | {unit:g} {row['currency']}/{basis} | {cost:.6f} {row['currency']} |")
        else:
            label, tokens, unit = item
            print(f"| {label} | {tokens:,} tokens | {unit:g} {row['currency']}/1M tokens | {tokens / 1_000_000 * unit:.6f} {row['currency']} |")
    print(f"\nSource: {row['source']}")
    print("Rate limit: See the provider's account-specific limits and the catalog record.")
    print(f"Lifecycle: {row['lifecycle']}")
    if row.get("request_fee_per_1k") is not None and not args.requests:
        print("⚠️ This SKU has a per-request surcharge; --requests was not supplied, so it is excluded from the total.")
    if row.get("notes"):
        print("Note: See the catalog record and official source for SKU-specific constraints.")


if __name__ == "__main__":
    main()
