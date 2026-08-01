---
name: cost-model
description: Calculate the cost of AI model calls and agent operations. Use this skill whenever a request involves cost, pricing, budget, model choice, token rates, rate limits or concurrency, text-to-video or image-to-video pricing, batch discounts, regional availability, price-history changes, or the AI-compute portion of a customer quote. It covers the costing method, scope rules, quote-staleness checks, 54 text API and gateway SKUs, regional availability, official price-history annotations for current-price SKUs, and public GPU, instance, and reserved-throughput snapshots.
---

# AI Model Economics

Turn “which model should we use?” into “what will it cost, can it handle the load, where is it officially available, and how long is the pricing basis valid?”

## Why use this skill

Model pricing looks like a lookup table. In practice, three mistakes can make an estimate wrong by an order of magnitude:

1. **Treating token fees as project cost.** Human review can cost many times more than compute.
2. **Checking unit price but not rate limits.** A flagship model can cost more while offering only 1/60 of an older tier’s RPM. A workload may be affordable but unable to run.
3. **Quoting a retired SKU.** The price may be valid when estimated, but the model may be unavailable when the contract is signed.

Use this order: **define the scope → assess all three axes → check whether the price is still valid → give the number.**

## Step 1: answer the three scope questions

Before giving any number, answer these questions and state the answers in the output. Different scopes can produce estimates that differ by two orders of magnitude.

### 1. Is this compute cost or delivery cost?

- **Compute cost** = tokens + tool calls + storage + subscriptions. This is the machine bill.
- **Delivery cost** = compute + human review + fact checking + compliance review + localization + rework. This is the operating cost.

Default to compute cost, **but explicitly list what is excluded**. In production content work, compute is often only a single-digit percentage of delivery cost. Presenting compute cost as delivery cost is the primary error this skill prevents.

### 2. Is this one-off or ongoing?

- **One-off**: calculate the single run; rate limits are usually not the constraint.
- **Ongoing**: calculate the monthly total and **validate rate limits** (see axis two).

### 3. Who will use this number?

- **Internal model selection**: provide a range and state assumptions.
- **External quotation or proposal**: use only a currently offered SKU’s current price and state the snapshot date.

## Step 2: assess all three axes

### Axis 1: unit price

Account for input price, output price, cache-hit price, and **tier conditions**.

Tier conditions are easy to miss. The same model can be priced by context length, target output length, or output resolution. Determine the applicable tier before selecting a price.

Estimated output tokens must include intermediate reasoning and discarded drafts, not only final deliverable text. Reasoning tokens can be billable.

### Axis 2: rate limits

Rate limits determine whether the workload can run, not whether it is cheap. Calculate demand before selecting a tier:

```
Required RPM = peak tasks ÷ available minutes
Required concurrency = task duration (minutes) × required RPM
```

Compare both values with the selected SKU’s `maximum RPM / maximum TPM / maximum concurrency`. **If the tier is insufficient, change tiers; do not substitute “wait longer.”** A concurrency ceiling is hard.

Rate limits are generally non-guaranteed and can vary with platform load. **Never present a rate-limit number as an SLA in an external proposal.**

### Axis 3: lifecycle

Check whether the SKU is marked as retiring or ending service.

- A retiring SKU **must not enter a cost model longer than six months**. It may be temporary capacity, but name the issue in the conclusion and provide a currently offered alternative plus the cost multiplier.
- Vendor replacement cycles differ. The snapshot files record what is publicly documented; older generations may not remain available.

## Step 3: check whether the quote has expired

Price snapshots decay. Check before giving any number.

**Snapshot older than 90 days**: say this before the number, without omission:

> ⚠️ The <vendor> price snapshot is YYYY-MM-DD, N days old. Values are order-of-magnitude only; refresh before a formal quote.

**Item absent from the snapshot**: say it is absent. **Do not use an adjacent SKU as a factual substitute.** An estimate may be offered only when visibly labelled `estimate, unverified`.

**Vendor absent from the snapshot**: say “this skill has no snapshot for that vendor.” **Never price from memory.** Model pricing changes too quickly for remembered figures to be reliable.

## Regional availability: keep two questions separate

“Can an entity in this country open an account or call the API?” and “Which service region processes the request?” are different facts. Never infer one from the other.

- **Account access country**: state that a country is supported or unsupported only when the vendor publishes a country or territory allowlist.
- **Service deployment region**: a cloud region or deployment matrix proves that a service or model can be deployed there; it does not prove that an entity from every country can open an account.
- **No public source**: return `pending_official_source`. This means the snapshot lacks a verifiable source; it does **not** mean available or unavailable.

Read regional data only from `references/regional_availability.json`. Every confirmed record must retain an official URL, source title, and access date. Do not complete gaps with IP tests, third-party lists, or marketing articles.

## Pricing-history annotations do not rewrite the current snapshot

Pricing history is an **official price-history annotation** on a current-price snapshot, not a separate coverage dimension alongside regional availability. Read current prices from `references/model_prices.json`; read `references/pricing_history.json` only for SKUs with qualifying historical evidence. Historical events must never overwrite current prices or be used to infer a previous price from a current one. No history annotation means only that no eligible official historical event is recorded; **it does not mean that current-price data is missing**.

- Each SKU’s `events` array is ordered by immutable `effective_date`. Every event needs exact before/after prices, unit, official source title, URL, and access date.
- When a source page does not provide both an effective date and exact before/after prices, retain `pending_official_source` or an empty array. This is not a gap in current-price coverage. Do not fill it with third-party reports, cached pages, adjacent SKUs, or discount percentages.
- An official announcement that embeds an official price table can be used as same-page evidence. Record the announcement URL and label it as an embedded price table.
- Output only when a price changed, in what unit, and from which amount to which amount. Do not infer competitive strategy or market signals.

Query and validate price-history annotations with:

```bash
python3 scripts/pricing_history.py --list
python3 scripts/pricing_history.py --vendor 'Moonshot AI'
python3 scripts/pricing_history.py --sku qwen-max
python3 scripts/pricing_history.py --validate
```

## Required output format

Use this structure. Lead with the conclusion; never omit the scope or exclusions.

```
[Cost] <one-line conclusion: a number or range>

Scope: compute cost / delivery cost | one-off / ongoing
Snapshot: <vendor> YYYY-MM-DD (N days old)

Price breakdown
| Item | Usage | Unit price | Subtotal |
|---|---|---|---|

Rate-limit check
Required RPM ___ / concurrency ___ | selected-tier maximum ___ → sufficient / insufficient
(If insufficient, provide an alternative tier.)

SKU status
<model> — current / ⚠️ retiring (alternative: ___, cost ×___)

Not included
- <list each exclusion>
```

If usage is estimated, mark it `estimate`; do not let an estimate look like an invoice.

**Display sufficient price precision for the table to multiply correctly.** Calculate internally with exact values, but if `unit price × usage ≠ subtotal` in the displayed table, the reader will doubt the whole estimate. Either show two more decimal places for unit price or state that the unit price is rounded and subtotals use exact values.

## General conversions

```
currency per 1M tokens ÷ 1,000 = currency per 1K tokens
Chinese: 1 token ≈ 0.67 characters | 10,000 Chinese characters ≈ 15,000 tokens
English: 1 token ≈ 0.75 words
```

Express the difference between a lower-priced and higher-priced tier as a multiplier, not only absolute values. “20× more expensive” is more decision-useful than “0.18 CNY versus 3.7 CNY.”

## Vendor snapshot index

| Snapshot | File | Snapshot date | Coverage |
|---|---|---|---|
| Volcengine Ark | `references/volcengine.md` | 2026-07-20 | Text / video / image / 3D / vector / fine-tuning / agent / tool / knowledge base / rate limits / retirement list |
| Multi-vendor text API | `references/multivendor-text-api.md` | 2026-07-21 | 22 vendors and cloud routes; 54 public usage-priced text SKUs; price / cache / batch / request fees / rate limits / lifecycle |
| Cloud infrastructure and throughput | `references/infrastructure_prices.json` | 2026-07-21 | AWS, Azure, and GCP GPUs; Alibaba PTU; Baidu compute units; Huawei public-price null boundaries |
| Coverage audit | `references/coverage-audit.md` | 2026-07-21 | Coverage list, known nulls, and no-mixing rules across routes and purchase models |
| Regional availability | `references/regional_availability.json` | 2026-07-27 | 22 existing suppliers; account access and service deployment recorded separately; missing official sources remain explicit |
| Current-price history annotations | `references/pricing_history.json` | 2026-07-27 | 19 official SKU price-change events; annotations only for current prices with traceable history; no annotation does not reduce current-price coverage |

The machine-readable source of truth is `references/model_prices.json`. It separates currency, route, region, and service tier. An omitted static price is `null`; do not replace it with a direct price, historical price, or discount ratio.

When adding a vendor, follow the structure of `references/volcengine.md`. Its header must include a snapshot date and source links.

## Tools

`scripts/video_cost.py` — Volcengine video-generation cost calculator. Applies the official token formula and reports rate-limit checks and SKU lifecycle status.

`scripts/model_cost.py` — multi-vendor text-token cost calculator. It calculates input, cache-hit, and output only within the same currency, route, and service tier. If no public cache price exists, it refuses to estimate.

`scripts/infrastructure_cost.py` — GPU, instance, reserved-throughput, and compute-unit calculator. It clearly marks whether a price covers the complete instance cost; an incomplete GPU-only item is not a total cost.

`scripts/regional_availability.py` — regional-availability inspector. It shows only records confirmed by official sources; it can filter by vendor or country code, and `--validate` checks vendor coverage and source-field completeness.

`scripts/pricing_history.py` — current-price SKU history-annotation inspector. It shows only events with an effective date, exact before/after price, and official source. Query it separately by vendor or SKU; it does not take part in cost calculation or fill current prices. `--validate` checks event arrays, date order, and source-field completeness.

```bash
python3 scripts/model_cost.py --list
python3 scripts/model_cost.py --model 'OpenAI/Direct API/gpt-5.6-terra' --input-tokens 1000000 --cached-input-tokens 400000 --output-tokens 200000 --mode batch
python3 scripts/model_cost.py --model 'Tencent Cloud/TokenHub/hy3' --input-tokens 1000000 --cached-input-tokens 500000 --output-tokens 250000
python3 scripts/model_cost.py --model 'Perplexity/Sonar/sonar (low search context)' --input-tokens 1000000 --output-tokens 200000 --requests 1000
python3 scripts/infrastructure_cost.py --sku 'p5.4xlarge' --units 24
python3 scripts/regional_availability.py --list
python3 scripts/regional_availability.py --vendor OpenAI
python3 scripts/regional_availability.py --country CN
python3 scripts/regional_availability.py --validate
python3 scripts/pricing_history.py --list
python3 scripts/pricing_history.py --vendor 'Moonshot AI'
python3 scripts/pricing_history.py --sku qwen-max
python3 scripts/pricing_history.py --validate
```

```bash
python3 scripts/video_cost.py --model seedance-2.0 --res 720p --duration 5
python3 scripts/video_cost.py --model seedance-2.0-mini --res 720p --duration 5 --count 200
python3 scripts/video_cost.py --list
```

Manual video pricing is easy to get wrong because pixels must be converted before applying the formula. Use the script whenever possible.

## Common pitfalls

**Treating the default configuration as optimal.** Default parameters often land in the more expensive tier (for example, a default `max_tokens` value above a tier boundary). Check defaults during estimation; this can reduce cost severalfold.

**Ignoring cache.** Cache-hit prices are often roughly one-fifth of input price. Long system prompts and fixed knowledge-base prefixes are repeated input; explicit prefix caching can save most of that cost. For every ongoing workload, ask how much input repeats on each call.

**Treating a low unit price as low total cost.** Higher-resolution video can have a lower unit price but consume tokens faster and cost more overall. Calculate total usage; do not rank only by unit price.

**Multiplying a one-off cost by the number of runs.** Ongoing work can gain cache hits, batch discounts, and free-tier allowances. Free allowances are especially easy to miss: some capabilities cost zero at small monthly volume.
