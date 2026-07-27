# cost-model

A cross-vendor reference for AI model economics — pricing, regional availability, and price history, with every number bound to an official source. Built for Claude Code, Codex, and any agent that reads `SKILL.md`.

## What this does

You're about to build something on an LLM, and someone asks: *how much will this actually cost to run?* You open a pricing page. It looks like a table. It isn't.

**cost-model** answers that question properly — across **22 vendors and 54 billing SKUs** — and catches the three things that make every naive estimate wrong: forgetting rate limits, quoting compute cost as project cost, and pricing a model that's about to be retired.

It doesn't just look up prices. It knows which prices you're not allowed to compare.

It also records officially documented regional availability without conflating two different facts: where an account may access an API, and where a cloud route can process inference.

For current-price SKUs with qualifying official evidence, it also keeps a separate historical price note: effective date, exact before/after rate, and official provenance. A SKU without that note still has a complete current-price snapshot; historical evidence is supplementary, not a coverage requirement.

## Demo

Ask your agent *"200 short videos a month, 720p, on Volcengine — what's the yearly cost?"* and it runs:

```
Cost: 200 clips × 720p / 5.0s → **496.80 CNY**

Pricing basis: compute cost | snapshot 2026-07-20 (6 days old)

Unit price breakdown
| Item | Value |
|---|---|
| Model | seedance-2.0-mini |
| Spec | 720p (1280x720) / 24fps / 5.0s |
| Pricing basis | without input video |
| Usage | 108,000 tokens |
| Unit price | 23.00 CNY/1M tokens |
| Per clip | 2.48 CNY |
| × 200 clips | **496.80 CNY** |

Rate limit (personal account)
Max RPM 180 | concurrency 3
Estimated at 1 minute per clip: theoretical ceiling ≈ 180 clips/hour

SKU status
seedance-2.0-mini active

NOT included
- Creative and scripting, review and reshoots, compliance, subtitles, and localization
- Failed generations are not billed; successful retry attempts are billed per clip
```

Notice what it does without being asked: checks whether you can even *run* the volume (rate limit), flags what the token cost leaves out (the real money), and confirms the SKU isn't being sunset. That's the difference between a price and an estimate.

## Key features

- **Refuses to guess** — no public price for a SKU? It returns `null`, not a made-up number. In cost work, *"I don't know"* beats a confident wrong answer.
- **Won't compare the incomparable** — never adds USD to RMB, never mixes direct-API prices with cloud-routed ones, never lets a preview SKU anchor a long-term plan.
- **Rate limit as a first-class axis** — flagship RPM can be 1/60th of the older tier. The cheaper tier is often the only one that can actually handle volume.
- **Compute ≠ delivery** — forces an explicit "not included" line, so token cost never gets quoted as project cost.
- **Prices are dated and expire** — snapshots carry a date; anything past 90 days warns before it answers.
- **Regional availability stays source-bound** — account-country allowlists and service-deployment regions are stored as different claim types. Missing official evidence remains `pending_official_source`, never a guessed restriction.
- **Official price-change notes where evidence exists** — historical events never overwrite current prices. They are a supplementary annotation for matching SKUs, recorded only when an official source supplies an effective date and exact before/after values; no history does not make a current price incomplete.

## Installation

```bash
git clone https://github.com/techdolphinJ/cost-model.git ~/.codex/skills/cost-model
chmod +x ~/.codex/skills/cost-model/scripts/*.py
```

Then just talk to your agent — say "cost", "how much", "which is cheaper", "can it handle the load" — and it loads automatically.

## Usage

Run the calculators directly:

```bash
# List every priceable SKU across all vendors
python3 scripts/model_cost.py --list

# One text call, with cache hits and batch pricing
python3 scripts/model_cost.py --model 'OpenAI/Direct API/gpt-5.6-terra' \
  --input-tokens 1000000 --cached-input-tokens 400000 --output-tokens 200000 --mode batch

# A GPU instance
python3 scripts/infrastructure_cost.py --sku 'p5.4xlarge' --units 24

# Volcengine video generation, with rate-limit and retirement checks
python3 scripts/video_cost.py --model seedance-2.0-mini --res 720p --duration 5 --count 200

# Regional availability: official records only
python3 scripts/regional_availability.py --list
python3 scripts/regional_availability.py --vendor OpenAI
python3 scripts/regional_availability.py --country CN

# Optional official price-change note for a current-price SKU
# Check this separately by SKU; it is not used in cost calculations.
python3 scripts/pricing_history.py --list
python3 scripts/pricing_history.py --vendor 'Moonshot AI'
python3 scripts/pricing_history.py --sku qwen-max
```

Or in conversation:

```
> "We're moving our summarization pipeline off GPT-5.6 onto something cheaper.
   Same quality tier. What are the options and what do they cost per million tokens?"
```

The agent reads the references, runs the numbers, and — this is the point — tells you what it *couldn't* price rather than inventing a figure.

## What's covered

| | |
|---|---|
| **Direct API** | OpenAI · Anthropic · Google Gemini · xAI · Mistral · Cohere |
| **China models** | Alibaba · Baidu · Tencent · Zhipu · MiniMax · Moonshot Kimi · DeepSeek · StepFun |
| **Cloud-routed** | AWS Bedrock · Azure AI Foundry · Vertex AI *(kept separate — never interchangeable with direct)* |
| **Open-source gateways** | Groq · Together *(priced by route, never backfilled to origin vendor)* |
| **Infrastructure** | AWS Capacity Blocks · Azure VM · GCP GPU · Alibaba PTU |
| **Multimodal** | Volcengine full stack — text / video / image / 3D / agent / KB / rate limits |
| **Regional availability** | The same 22 vendors, with official country-access or deployment-region records kept separate; unsupported source coverage stays explicit |
| **Current-price annotations** | Optional official price-change notes for 19 historical SKU events across eight reviewed suppliers; absence of a note does not reduce current-price coverage |

## Under the hood

Progressive disclosure — `SKILL.md` is a concise method (~180 lines); prices load on demand.

| File | What it holds |
|---|---|
| `SKILL.md` | The method: costing framework, three axes, staleness checks, output format |
| `references/multivendor-text-api.md` | 22-vendor text API index + audit notes |
| `references/model_prices.json` | 54 SKUs, machine-readable |
| `references/infrastructure_prices.json` | GPU / instance / reserved throughput |
| `references/regional_availability.json` | Official regional-availability records, claim type, route scope, and source metadata |
| `references/pricing_history.json` | Optional official price-change annotations for a current-price snapshot: SKU events, effective dates, before/after prices, and provenance |
| `references/volcengine.md` | Volcengine multimodal + rate limits + retirement list |
| `references/coverage-audit.md` | What's covered, what's deliberately `null`, and the no-mixing rules |
| `scripts/*.py` | Three calculators, a regional-availability inspector, and an optional price-history-note inspector |

Every price links to an official source. Snapshots are dated. Vendors change prices — the official page always wins.

## Why these rules

These aren't features. They're constraints — things the tool refuses to do.

A cost tool that will guess a missing price, or add USD to RMB to look complete, is worse than useless: it's *confidently wrong*, and a wrong quote does more damage than no quote. This one would rather return less and be right.

## Credits

The method — the costing framework, the discipline about what must never be compared — comes from years of work in cross-border commercialization. The data collection and code were done with a coding agent. What matters isn't who typed it; it's whether every number holds up when you click the source.

## License

MIT — use it, fork it, ship it.
