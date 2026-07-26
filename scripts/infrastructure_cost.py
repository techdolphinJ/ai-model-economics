#!/usr/bin/env python3
"""按公开的基础设施/预留吞吐 SKU 快照核算，不估算缺项。"""
import argparse
import datetime as dt
import json
import sys
from pathlib import Path

CATALOG = Path(__file__).resolve().parent.parent / "references" / "infrastructure_prices.json"

def main():
    ap = argparse.ArgumentParser(description="GPU, instance, and reserved-throughput cost calculator")
    ap.add_argument("--sku", help="Full or unique SKU name")
    ap.add_argument("--units", type=float, default=1, help="Quantity in the item's billing_unit")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    d = json.load(CATALOG.open(encoding="utf-8"))
    if a.list:
        for x in d["items"]:
            rate = "null" if x["rate"] is None else f"{x['rate']:g} {x['currency']}"
            print(f"{x['provider']}/{x['service']}/{x['sku']} [{rate}/{x['billing_unit']}; {x['purchase_mode']}]")
        return
    if not a.sku:
        ap.error("--sku is required (or use --list)")
    candidates = [x for x in d["items"] if a.sku.casefold() in f"{x['provider']}/{x['service']}/{x['sku']}".casefold()]
    if len(candidates) != 1:
        print("Error: SKU is ambiguous or not found:\n  " + "\n  ".join(f"{x['provider']}/{x['service']}/{x['sku']}" for x in candidates), file=sys.stderr)
        sys.exit(2)
    x = candidates[0]
    if x["rate"] is None:
        print("No public price — returned as null, not estimated.", file=sys.stderr)
        sys.exit(2)
    total = a.units * x["rate"]
    print(f"Infrastructure cost: {total:.6f} {x['currency']}")
    print(f"Pricing basis: {x['provider']}/{x['service']}/{x['sku']} | {a.units:g} × {x['billing_unit']} × {x['rate']:g}")
    print(f"Region/purchase mode: {x['region']} / {x['purchase_mode']}")
    print(f"Completeness: {'Complete instance/capacity price' if x['total_price_complete'] else 'Incomplete; add other resources as noted in the catalog'}")
    print(f"Source: {x['source']}\nNote: See the catalog entry for scope details.")

if __name__ == "__main__":
    main()
