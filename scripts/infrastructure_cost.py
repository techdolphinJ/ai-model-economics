#!/usr/bin/env python3
"""按公开的基础设施/预留吞吐 SKU 快照核算，不估算缺项。"""
import argparse
import datetime as dt
import json
import sys
from pathlib import Path

CATALOG = Path(__file__).resolve().parent.parent / "references" / "infrastructure_prices.json"

def main():
    ap = argparse.ArgumentParser(description="GPU、实例与预留吞吐成本计算器")
    ap.add_argument("--sku", help="完整或唯一 SKU 名称")
    ap.add_argument("--units", type=float, default=1, help="按条目的 billing_unit 计的数量")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    d = json.load(CATALOG.open(encoding="utf-8"))
    if a.list:
        for x in d["items"]:
            rate = "null" if x["rate"] is None else f"{x['rate']:g} {x['currency']}"
            print(f"{x['provider']}/{x['service']}/{x['sku']} [{rate}/{x['billing_unit']}; {x['purchase_mode']}]")
        return
    if not a.sku:
        ap.error("--sku 必填（或使用 --list）")
    candidates = [x for x in d["items"] if a.sku.casefold() in f"{x['provider']}/{x['service']}/{x['sku']}".casefold()]
    if len(candidates) != 1:
        print("错误：SKU 不唯一或不存在：\n  " + "\n  ".join(f"{x['provider']}/{x['service']}/{x['sku']}" for x in candidates), file=sys.stderr)
        sys.exit(2)
    x = candidates[0]
    if x["rate"] is None:
        print("错误：该 SKU 官方未公开匿名静态价，不能估算。", file=sys.stderr)
        sys.exit(2)
    total = a.units * x["rate"]
    print(f"【基础设施成本】{total:.6f} {x['currency']}")
    print(f"口径：{x['provider']}/{x['service']}/{x['sku']} ｜ {a.units:g} × {x['billing_unit']} × {x['rate']:g}")
    print(f"区域/购买模式：{x['region']} / {x['purchase_mode']}")
    print(f"完整性：{'该 SKU 的实例/容量费完整' if x['total_price_complete'] else '不完整；须按注释追加其他资源'}")
    print(f"来源：{x['source']}\n注意：{x['note']}")

if __name__ == "__main__":
    main()
