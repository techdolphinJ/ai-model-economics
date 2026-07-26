#!/usr/bin/env python3
"""火山方舟视频生成成本计算器

按官方公式核算：
    token 用量 = (输入视频时长 + 输出视频时长) x 宽 x 高 x 帧率 / 1024
    价格 = token 单价 x token 用量

同时输出限流校验与 SKU 生命周期状态。

价格快照：2026-07-20（来源 references/volcengine.md）
超过 90 天后结果仅供量级参考，需重新抓取官方价目。
"""

import argparse
import datetime
import sys

SNAPSHOT = datetime.date(2026, 7, 20)
STALE_DAYS = 90

# 分辨率 -> (宽, 高)。720p/1080p/4k 已用官方价格示例反算验证，误差 <0.1%。
# 480p 按标准 854x480 计算比官方示例低约 4%，官方实际用的像素数偏大，
# 因此 480p 结果标注为近似。
RES = {
    "480p": (854, 480, True),
    "720p": (1280, 720, False),
    "1080p": (1920, 1080, False),
    "4k": (3840, 2160, False),
}

FPS = 24  # 火山视频模型全线锁定 24 fps

# model -> 规格
#   prices: {分辨率组: (不含输入视频单价, 含输入视频单价)}  元/百万token
#   res: 支持的分辨率
#   rpm/concurrency: (企业, 个人)
#   retiring: 是否标记即将下线
MODELS = {
    "seedance-2.0": {
        "prices": {"480p": (46.0, 28.0), "720p": (46.0, 28.0),
                   "1080p": (51.0, 31.0), "4k": (26.0, 16.0)},
        "res": ["480p", "720p", "1080p", "4k"],
        "duration": (4, 15),
        "rpm": {"default": (600, 180), "4k": (15, 15)},
        "concurrency": {"default": (10, 3), "4k": (1, 1)},
        "retiring": False,
    },
    "seedance-2.0-fast": {
        "prices": {"480p": (37.0, 22.0), "720p": (37.0, 22.0)},
        "res": ["480p", "720p"],
        "duration": (4, 15),
        "rpm": {"default": (600, 180)},
        "concurrency": {"default": (10, 3)},
        "retiring": False,
    },
    "seedance-2.0-mini": {
        "prices": {"480p": (23.0, 14.0), "720p": (23.0, 14.0)},
        "res": ["480p", "720p"],
        "duration": (4, 15),
        "rpm": {"default": (600, 180)},
        "concurrency": {"default": (10, 3)},
        "retiring": False,
    },
    "seedance-1.5-pro": {
        # 按输出是否含声音分档，非按输入
        "prices": {"480p": (16.0, 8.0), "720p": (16.0, 8.0), "1080p": (16.0, 8.0)},
        "price_axis": "audio",  # (有声, 无声)
        "res": ["480p", "720p", "1080p"],
        "duration": (4, 12),
        "rpm": {"default": (600, 600)},
        "concurrency": {"default": (10, 10)},
        "retiring": True,
        "replacement": "seedance-2.0-mini",
    },
    "seedance-1.0-pro-fast": {
        "prices": {"480p": (4.20, 4.20), "720p": (4.20, 4.20), "1080p": (4.20, 4.20)},
        "offline": 2.10,
        "res": ["480p", "720p", "1080p"],
        "duration": (2, 12),
        "rpm": {"default": (600, 600)},
        "concurrency": {"default": (10, 10)},
        "retiring": False,
    },
    "seedance-1.0-pro": {
        "offline": 7.50,
        "prices": {"480p": (15.0, 15.0), "720p": (15.0, 15.0), "1080p": (15.0, 15.0)},
        "res": ["480p", "720p", "1080p"],
        "duration": (2, 12),
        "rpm": {"default": (600, 600)},
        "concurrency": {"default": (10, 10)},
        "retiring": False,
    },
}


def staleness():
    days = (datetime.date.today() - SNAPSHOT).days
    return days, days > STALE_DAYS


def compute(model, res, out_dur, in_dur=0.0, audio=False, count=1, account="个人"):
    spec = MODELS[model]
    if res not in spec["res"]:
        return None, f"{model} does not support {res} (supported: {'/'.join(spec['res'])})"

    lo, hi = spec["duration"]
    warn = []
    if not (lo <= out_dur <= hi):
        warn.append(f"Duration {out_dur}s is outside {model}'s supported range of {lo}–{hi}s")

    w, h, approx = RES[res]
    tokens = (in_dur + out_dur) * w * h * FPS / 1024

    if spec.get("price_axis") == "audio":
        unit = spec["prices"][res][0 if audio else 1]
        basis = "with audio" if audio else "without audio"
    else:
        unit = spec["prices"][res][1 if in_dur > 0 else 0]
        basis = "with input video" if in_dur > 0 else "without input video"

    price = tokens / 1_000_000 * unit
    if approx:
        warn.append("480p is an estimate; official examples are approximately 4% higher")

    key = "4k" if res == "4k" and "4k" in spec["rpm"] else "default"
    idx = 1 if account == "个人" else 0
    rpm = spec["rpm"][key][idx]
    conc = spec["concurrency"][key][idx]

    return {
        "tokens": tokens, "unit": unit, "basis": basis,
        "unit_price": price, "total": price * count, "count": count,
        "rpm": rpm, "concurrency": conc, "dims": f"{w}x{h}",
        "retiring": spec["retiring"], "replacement": spec.get("replacement"),
        "warn": warn,
    }, None


def main():
    p = argparse.ArgumentParser(description="Volcengine Ark video-generation cost calculator")
    p.add_argument("--model", default="seedance-2.0")
    p.add_argument("--res", default="720p", choices=list(RES))
    p.add_argument("--duration", type=float, default=5, help="Output-video duration in seconds")
    p.add_argument("--input-duration", type=float, default=0, help="Input-video duration in seconds; use 0 for text-to-video")
    p.add_argument("--audio", action="store_true", help="seedance-1.5-pro only: include audio")
    p.add_argument("--count", type=int, default=1, help="Clip count")
    p.add_argument("--account", default="个人", choices=["个人", "企业"])
    p.add_argument("--list", action="store_true", help="List all models")
    a = p.parse_args()

    if a.list:
        print(f"Volcengine video models (snapshot {SNAPSHOT})\n")
        for m, s in MODELS.items():
            tag = "  ⚠️ sunsetting" if s["retiring"] else ""
            print(f"  {m:<20} {'/'.join(s['res']):<28} {s['duration'][0]}~{s['duration'][1]}s{tag}")
        return

    if a.model not in MODELS:
        print(f"Unknown model {a.model}. Available: {', '.join(MODELS)}", file=sys.stderr)
        sys.exit(1)

    r, err = compute(a.model, a.res, a.duration, a.input_duration,
                     a.audio, a.count, a.account)
    if err:
        print(err, file=sys.stderr)
        sys.exit(1)

    days, stale = staleness()
    if stale:
        print(f"⚠️ Snapshot {SNAPSHOT} is {days} days old. This is directional only; refresh official pricing before formal quoting.\n")

    print(f"Cost: {a.count} clips × {a.res} / {a.duration}s → **{r['total']:.2f} CNY**")
    print(f"\nPricing basis: compute cost | snapshot {SNAPSHOT} ({days} days old)\n")
    print("Unit price breakdown")
    print("| Item | Value |")
    print("|---|---|")
    print(f"| Model | {a.model} |")
    print(f"| Spec | {a.res} ({r['dims']}) / {FPS}fps / {a.duration}s |")
    print(f"| Pricing basis | {r['basis']} |")
    print(f"| Usage | {r['tokens']:,.0f} tokens |")
    print(f"| Unit price | {r['unit']:.2f} CNY/1M tokens |")
    print(f"| Per clip | {r['unit_price']:.2f} CNY |")
    print(f"| × {a.count} clips | **{r['total']:.2f} CNY** |")

    print(f"\nRate limit ({'personal' if a.account == '个人' else 'enterprise'} account)")
    print(f"Max RPM {r['rpm']} | concurrency {r['concurrency']}")
    if r["concurrency"] <= 1:
        print("⚠️ concurrency is 1: serial generation only; unsuitable for batch production")
    else:
        print(f"Estimated at 1 minute per clip: theoretical ceiling ≈ {r['concurrency'] * 60} clips/hour")

    print("\nSKU status")
    if r["retiring"]:
        print(f"⚠️ {a.model} is sunsetting; do not use it for cost models longer than 6 months")
        if r["replacement"]:
            alt, _ = compute(r["replacement"], a.res, a.duration,
                             a.input_duration, a.audio, a.count, a.account)
            if alt:
                mult = alt["total"] / r["total"] if r["total"] else 0
                print(f"   Active replacement: {r['replacement']} → {alt['total']:.2f} CNY (×{mult:.1f})")
    else:
        print(f"{a.model} active")

    for w in r["warn"]:
        print(f"\nNote: {w}")

    off = MODELS[a.model].get("offline")
    if off:
        print(f"\nOffline inference available: Unit price {off:.2f} CNY/1M tokens → per clip {r['tokens']/1e6*off:.2f} CNY"
              f" (× {a.count} = {r['tokens']/1e6*off*a.count:.2f} CNY). Prefer it for non-real-time workloads.")

    print("\nNOT included")
    print("- Creative and scripting, review and reshoots, compliance, subtitles, and localization")
    print("- Failed generations are not billed; successful retry attempts are billed per clip")


if __name__ == "__main__":
    main()
