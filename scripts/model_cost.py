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
        raise ValueError(f"未找到 {requested}；用 --list 查询完整键名")
    raise ValueError("名称不唯一，请输入完整 vendor/route/model：\n  " + "\n  ".join(model_key(r) for r in candidates))


def price(row, mode, input_tokens, cached_input_tokens, output_tokens, requests=0):
    if cached_input_tokens > input_tokens:
        raise ValueError("缓存命中 token 不能超过输入 token")
    rates = row["prices"].get(mode)
    if not rates:
        available = ", ".join(row["prices"])
        raise ValueError(f"{model_key(row)} 无 {mode} 公开价（可用：{available}）")
    if rates.get("input") is None or rates.get("output") is None:
        raise ValueError(f"{model_key(row)} 的 {mode} 不是普通文本 token 计费，不能用本计算器")

    cached_rate = rates.get("cached_input")
    if cached_input_tokens and cached_rate is None:
        raise ValueError("该快照没有缓存命中价；请传 0 或核查官方文档")

    uncached = input_tokens - cached_input_tokens
    per_million = 1_000_000
    items = [
        ("非缓存输入", uncached, rates["input"]),
        ("缓存命中", cached_input_tokens, cached_rate or 0),
        ("输出", output_tokens, rates["output"]),
    ]
    total = sum(tokens / per_million * unit for _, tokens, unit in items)
    request_fee = row.get("request_fee_per_1k")
    if requests and request_fee is not None:
        items.append(("请求附加费", requests, request_fee, "每千请求"))
        total += requests / 1_000 * request_fee
    return items, total


def main():
    ap = argparse.ArgumentParser(description="公开 API 文本 token 成本计算器")
    ap.add_argument("--model", help="完整或唯一的 vendor/route/model")
    ap.add_argument("--input-tokens", type=int, default=0)
    ap.add_argument("--cached-input-tokens", type=int, default=0)
    ap.add_argument("--output-tokens", type=int, default=0)
    ap.add_argument("--requests", type=int, default=0, help="请求次数；仅在该 SKU 公开每请求附加费时计入")
    ap.add_argument("--mode", default="standard", choices=["standard", "batch", "flex", "priority"])
    ap.add_argument("--list", action="store_true", help="列出可计算模型")
    args = ap.parse_args()
    catalog = load_catalog()

    if args.list:
        for row in catalog["models"]:
            modes = ",".join(row["prices"])
            print(f"{model_key(row)}  [{row['currency']}; {modes}; {row['lifecycle']}]")
        return
    if not args.model:
        ap.error("--model 必填（或使用 --list）")

    try:
        row = find_model(catalog, args.model)
        items, total = price(row, args.mode, args.input_tokens, args.cached_input_tokens, args.output_tokens, args.requests)
    except ValueError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        sys.exit(2)

    snapshot = dt.date.fromisoformat(row["snapshot_date"])
    age = (dt.date.today() - snapshot).days
    if age > catalog["stale_after_days"]:
        print(f"⚠️ 快照 {snapshot} 已 {age} 天，正式报价前必须复核官方页。\n")

    print(f"【成本】{total:.6f} {row['currency']}")
    print(f"口径：{model_key(row)} ｜ {args.mode} ｜ 快照 {snapshot}（{age} 天）")
    print("| 项 | 用量 | 单价 | 成本 |")
    print("|---|---:|---:|---:|")
    for item in items:
        if len(item) == 4:
            label, units, unit, basis = item
            cost = units / 1_000 * unit
            print(f"| {label} | {units:,} 请求 | {unit:g} {row['currency']}/{basis} | {cost:.6f} {row['currency']} |")
        else:
            label, tokens, unit = item
            print(f"| {label} | {tokens:,} token | {unit:g} {row['currency']}/百万 token | {tokens / 1_000_000 * unit:.6f} {row['currency']} |")
    print(f"\n来源：{row['source']}")
    print(f"限流：{row['rate_limit_note']}")
    print(f"生命周期：{row['lifecycle_note']}")
    if row.get("request_fee_per_1k") is not None and not args.requests:
        print("⚠️ 此 SKU 另有每请求附加费；未传 --requests，当前总价不含该部分。")
    if row.get("notes"):
        print(f"注意：{row['notes']}")


if __name__ == "__main__":
    main()
