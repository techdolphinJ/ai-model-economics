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
        return None, f"{model} 不支持 {res}（支持：{'/'.join(spec['res'])}）"

    lo, hi = spec["duration"]
    warn = []
    if not (lo <= out_dur <= hi):
        warn.append(f"时长 {out_dur}s 超出 {model} 支持范围 {lo}~{hi}s")

    w, h, approx = RES[res]
    tokens = (in_dur + out_dur) * w * h * FPS / 1024

    if spec.get("price_axis") == "audio":
        unit = spec["prices"][res][0 if audio else 1]
        basis = "有声" if audio else "无声"
    else:
        unit = spec["prices"][res][1 if in_dur > 0 else 0]
        basis = "输入含视频" if in_dur > 0 else "输入不含视频"

    price = tokens / 1_000_000 * unit
    if approx:
        warn.append("480p 为近似值，官方示例约高 4%")

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
    p = argparse.ArgumentParser(description="火山方舟视频生成成本计算器")
    p.add_argument("--model", default="seedance-2.0")
    p.add_argument("--res", default="720p", choices=list(RES))
    p.add_argument("--duration", type=float, default=5, help="输出视频秒数")
    p.add_argument("--input-duration", type=float, default=0, help="输入视频秒数，文生视频填 0")
    p.add_argument("--audio", action="store_true", help="仅 seedance-1.5-pro：输出含声音")
    p.add_argument("--count", type=int, default=1, help="条数")
    p.add_argument("--account", default="个人", choices=["个人", "企业"])
    p.add_argument("--list", action="store_true", help="列出所有型号")
    a = p.parse_args()

    if a.list:
        print(f"火山视频型号（快照 {SNAPSHOT}）\n")
        for m, s in MODELS.items():
            tag = "  ⚠️ 即将下线" if s["retiring"] else ""
            print(f"  {m:<20} {'/'.join(s['res']):<28} {s['duration'][0]}~{s['duration'][1]}s{tag}")
        return

    if a.model not in MODELS:
        print(f"未知型号 {a.model}。可用：{', '.join(MODELS)}", file=sys.stderr)
        sys.exit(1)

    r, err = compute(a.model, a.res, a.duration, a.input_duration,
                     a.audio, a.count, a.account)
    if err:
        print(err, file=sys.stderr)
        sys.exit(1)

    days, stale = staleness()
    if stale:
        print(f"⚠️ 报价快照 {SNAPSHOT}，距今 {days} 天。数字仅供量级参考，正式报价须重新抓取。\n")

    print(f"【成本】{a.count} 条 × {a.res} / {a.duration}s → **{r['total']:.2f} 元**")
    print(f"\n口径：算力成本 ｜ 快照 {SNAPSHOT}（距今 {days} 天）\n")
    print("单价拆解")
    print("| 项 | 值 |")
    print("|---|---|")
    print(f"| 型号 | {a.model} |")
    print(f"| 规格 | {a.res} ({r['dims']}) / {FPS}fps / {a.duration}s |")
    print(f"| 计价口径 | {r['basis']} |")
    print(f"| token 用量 | {r['tokens']:,.0f} |")
    print(f"| token 单价 | {r['unit']:.2f} 元/百万 |")
    print(f"| 单条 | {r['unit_price']:.2f} 元 |")
    print(f"| × {a.count} 条 | **{r['total']:.2f} 元** |")

    print(f"\n限流校验（{a.account}账号）")
    print(f"最大 RPM {r['rpm']} ｜ 最大并发 {r['concurrency']}")
    if r["concurrency"] <= 1:
        print("⚠️ 并发为 1，只能串行，不适合批量生产")
    else:
        print(f"按单条生成 1 分钟估：理论上限约 {r['concurrency'] * 60} 条/小时")

    print("\nSKU 状态")
    if r["retiring"]:
        print(f"⚠️ {a.model} 即将下线，勿用于 6 个月以上的成本模型")
        if r["replacement"]:
            alt, _ = compute(r["replacement"], a.res, a.duration,
                             a.input_duration, a.audio, a.count, a.account)
            if alt:
                mult = alt["total"] / r["total"] if r["total"] else 0
                print(f"   在架替代：{r['replacement']} → {alt['total']:.2f} 元（×{mult:.1f}）")
    else:
        print(f"{a.model} 在架")

    for w in r["warn"]:
        print(f"\n注：{w}")

    off = MODELS[a.model].get("offline")
    if off:
        print(f"\n离线推理档可用：单价 {off:.2f} 元/百万 → 单条 {r['tokens']/1e6*off:.2f} 元"
              f"（× {a.count} = {r['tokens']/1e6*off*a.count:.2f} 元），非实时场景优先用")

    print("\n未计入")
    print("- 创意与脚本、审片与返工、合规过审、字幕与本地化")
    print("- 生成失败不计费，但重试产生的成功件按次计")


if __name__ == "__main__":
    main()
