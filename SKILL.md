---
name: cost-model
description: AI 模型调用与 agent 运行的成本核算。当对话涉及「跑这个要多少钱」「用哪个模型划算」「token 单价」「限流 / RPM / 并发够不够」「文生视频 / 图生视频报价」「批量推理折扣」「区域可用性 / 出海能否接入」「历史调价 / 价格何时变了」「给客户报价里的 AI 算力那部分」，或任何需要把「用哪个模型」换算成「多少钱、能跑多快、官方声明在哪些地区可用、当前价是否附有可溯源的历史调价注脚」的场景时使用。含核算方法、口径规则、报价失效检查、54 个文本 API/网关 SKU、区域可用性，以及当前价格快照的 SKU 历史调价附注和 GPU、实例、预留吞吐公开快照。只要提到成本、报价、预算、划不划算、够不够跑、贵不贵、区域可用性、历史调价，就该用这个 skill——即使没明说要核算。
---

# 成本核算

把「用哪个模型」换算成「多少钱、能不能跑得动、能用多久」。

## 为什么需要这个 skill

模型报价看起来是查表，实际有三个坑，每个都会让结论错一个数量级：

1. **只算 token 费**，把它当成项目成本报给客户——漏掉的人工审核部分往往是算力的十几倍。
2. **只看单价不看限流**——旗舰模型比往期档贵一倍，但 RPM 可能只有 1/60。算出来能负担，实际跑不动。
3. **引用了已下线的 SKU**——报价当时成立，签合同时那个型号已经没了。

所以核算的顺序是：**先定口径 → 三轴都算 → 检查报价是否还有效 → 才给数**。

---

## 第一步：口径三问（不能跳）

给任何数字之前，先在心里答完这三问，并把答案写进输出。口径不同，同一件事的报价能差两个数量级。

**1. 算的是算力成本还是交付成本？**

- **算力成本** = token + 工具调用 + 存储 + 订阅。机器账单。
- **交付成本** = 算力 + 人工审核 + 事实核对 + 合规过审 + 本地化 + 返工。真实成本。

默认按算力成本算，**但必须显式列出没算进去的部分**。经验比例：产出类任务里算力通常只占交付成本的个位数百分比。把算力成本当交付成本报出去，是这个 skill 要防的头号错误。

**2. 一次性还是持续跑？**

- 一次性 → 算单次，限流基本不是约束。
- 持续 → 算月度总额，**并且必须校验限流**（见轴二）。

**3. 这个数给谁看？**

- 内部选型 → 给区间，可以带假设。
- 对外报价 / 写进方案 → 只能用**在架 SKU** 的**当代价格**，且必须标快照日期。

---

## 第二步：三轴都要算

### 轴一 · 单价

要素：输入价、输出价、缓存命中价，以及**分档条件**。

分档条件是最容易漏的——同一个模型的价格可能按上下文长度、目标输出长度、输出分辨率分成好几档。先确定落在哪一档，再取价。

估算时输出 token 要**含中间推理和废稿**，不能只按最终成品字数算。推理模型的思维链是要付费的。

### 轴二 · 限流（决定能不能跑，不是贵不贵）

先算需求，再看档位够不够：

```
需要的 RPM = 峰值任务数 ÷ 可用分钟数
需要的并发 = 单任务耗时(分钟) × 需要的 RPM
```

拿这两个数去比所选 SKU 的 `最大 RPM / 最大 TPM / 最大并发`。**不够就换档，不要换成"多等一会儿"**——并发上限是硬的，等不出来。

限流通常是**非刚性保障**（受平台负载影响）。**永远不要把限流数字当 SLA 写进对外方案。**

### 轴三 · 生命周期

查所用 SKU 有没有「即将下线 / 停止服务」标记。

- 标了下线 → **不能进任何超过 6 个月的成本模型**。可以当临时算力用，但结论里必须点名，并给出在架替代 + 换算后的倍数变化。
- 各厂商汰换节奏不同，快照文件里会记。观察到的规律：一年一代、老代不留。

---

## 第三步：失效检查（硬规则）

价格快照是会烂的。给数之前先检查：

**快照超过 90 天** → 先说这一句，再给数，不许省略：

> ⚠️ 本次引用的 <厂商> 报价快照为 YYYY-MM-DD，距今 N 天。数字仅供量级参考，正式报价须重新抓取。

**快照里没有的项** → 直接说没有。**不要拿相邻 SKU 推算后当事实给出。**可以给推算值，但必须标「推算，未经核实」。

**问到没有快照的厂商** → 直接说「本 skill 尚无该厂商快照」。**不要凭记忆报价**——模型定价是变动最快的一类事实，记忆里的数几乎一定是旧的。

## 区域可用性：先分清两个问题

「某国能否开户/调用」与「请求由哪个服务区域处理」不是同一个事实，禁止相互推导。

- **账户接入地**：只有厂商公开 country/territory allowlist 时，才能说某地受支持或不受支持。
- **服务部署地**：云厂商的 region / deployment matrix 只能证明服务或模型在该区域可部署；它不证明任意国家主体都能开户。
- **无公开来源**：输出 `pending_official_source`。这表示本快照尚未收录可核验来源，**不表示可用或不可用**。

区域数据一律读取 `references/regional_availability.json`，每条已确认记录必须保留官方 URL、来源标题与访问日期。不要用 IP 测试、第三方清单或营销文章补全空项。

## 定价历史附注：不改写当前快照

定价历史不是与区域可用性并列的覆盖维度，而是当前价格快照的**官方调价历史附注**。当前价格读取 `references/model_prices.json`；有符合条件历史证据的 SKU 再读取 `references/pricing_history.json`。历史事件不得回填当前价格，也不得把当前价倒推为“调整前价格”。没有历史附注只表示该 SKU 的当前价没有可收录的官方历史事件，**不表示当前价格数据缺失**。

- 每个 SKU 的 `events` 是按不可变 `effective_date` 排序的数组。每个事件必须同时有精确的调整前/后价格、单位、官方来源标题、URL 与访问日期。
- 来源页面没有同时给出生效日与前后精确价格时，保留 `pending_official_source` 或空数组；这不是当前价格快照的缺口。不以第三方报道、网页缓存、相邻 SKU 或折扣比例补齐。
- 官方公告中嵌入的官方价目图可以作为同页证据，来源仍写公告页 URL，并明确标注为嵌入价表。
- 输出仅陈述何时、按什么单位、从多少变为多少；不把调价解释为竞争策略或市场信号。

用 `scripts/pricing_history.py` 查询和验证：

```
python3 scripts/pricing_history.py --list
python3 scripts/pricing_history.py --vendor 'Moonshot AI'
python3 scripts/pricing_history.py --sku qwen-max
python3 scripts/pricing_history.py --validate
```

---

## 输出格式

固定用这个结构。结论先行，口径和未计入项不能省。

```
【成本】<一句话结论：一个数或一个区间>

口径：算力成本 / 交付成本 ｜ 一次性 / 持续
快照：<厂商> YYYY-MM-DD（距今 N 天）

单价拆解
| 项 | 用量 | 单价 | 小计 |
|---|---|---|---|

限流校验
需要 RPM ___ / 并发 ___ ｜ 所选档位上限 ___ → 够 / 不够
（不够时给出替代档位）

SKU 状态
<型号> — 在架 / ⚠️ 即将下线（替代：___，成本 ×___）

未计入
- <逐条列出>
```

用量是估的就写「估」，别让估算值看起来像账单。

**单价列的精度必须让表格自己乘得通。** 内部按精确值算，但显示时若 `单价 × 用量 ≠ 小计`，对方一验算就会怀疑整张表——哪怕数字其实是对的。两种处理，选一个：单价多给两位小数，或在表下注明「单价已四舍五入，小计按精确值计」。

---

## 通用换算

```
元/百万 token ÷ 1000 = 元/千 token
中文 1 token ≈ 0.67 字 ｜ 1 万汉字 ≈ 1.5 万 token
英文 1 token ≈ 0.75 词
```

**便宜档和贵档差多少，用倍数表达，不要只给绝对值。** 「0.18 元 vs 3.7 元」不如「差 20 倍」有决策价值。

---

## 厂商快照索引

| 厂商 | 文件 | 快照日期 | 覆盖 |
|---|---|---|---|
| 火山引擎方舟 | `references/volcengine.md` | 2026-07-20 | 文本 / 视频 / 图片 / 3D / 向量 / 精调 / Agent / 工具 / 知识库 / 限流 / 下线清单 |
| 多厂商文本 API | `references/multivendor-text-api.md` | 2026-07-21 | 22 个厂商/云路由，54 个公开按量文本 SKU；单价 / 缓存 / 批处理 / 请求附加费 / 限流 / 生命周期 |
| 云基础设施/吞吐 | `references/infrastructure_prices.json` | 2026-07-21 | AWS/Azure/GCP GPU、阿里 PTU、百度算力单元，以及华为公开价空值边界 |
| 覆盖审计 | `references/coverage-audit.md` | 2026-07-21 | 覆盖清单、已知空值、跨路由/购买模式不混算规则 |
| 区域可用性 | `references/regional_availability.json` | 2026-07-27 | 22 个既有供应商；账户接入地与服务部署地分开记录；无官方来源显式待补充 |
| 当前价格调价历史附注 | `references/pricing_history.json` | 2026-07-27 | 19 个官方 SKU 调价事件；仅为有可溯源历史的当前价格附注，无附注不影响当前价覆盖 |

机器可读的真源是 `references/model_prices.json`。它明确分开币种、路由、区域和服务档；没有写出的静态价格就是 `null`，不得以直连价、历史价或折扣比例代替。

新增厂商时，照 `volcengine.md` 的结构写，头部必须有快照日期和来源链接。

---

## 工具

`scripts/video_cost.py` — 火山视频生成成本计算器。按官方 token 公式算，同时输出限流校验和 SKU 下线状态。

`scripts/model_cost.py` — 多厂商文本 token 成本计算器。仅计算同一币种、同一路由、同一服务档的输入 / 缓存命中 / 输出；没有公开缓存价时会拒绝估算而不是猜。

`scripts/infrastructure_cost.py` — GPU、实例、预留吞吐与算力单元计算器。它会明确标记价格是否已覆盖完整实例成本；不完整的 GPU-only 项不能当总成本。

`scripts/regional_availability.py` — 区域可用性查询器。它只展示官方来源已确认的记录；可按厂商或国家代码查看，`--validate` 会检查供应商覆盖与来源字段完整性。

`scripts/pricing_history.py` — 当前价格的 SKU 历史调价附注查询器。它只展示带生效日、精确前后价格和官方来源的事件；需与当前价格目录按 SKU 分别查阅，不参与成本计算或补全当前价。可按厂商或 SKU 查询，`--validate` 会检查事件数组、日期顺序和来源字段完整性。

```
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

```
python3 scripts/video_cost.py --model seedance-2.0 --res 720p --duration 5
python3 scripts/video_cost.py --model seedance-2.0-mini --res 720p --duration 5 --count 200
python3 scripts/video_cost.py --list
```

视频报价手算容易错（要先换算像素再套公式），能用脚本就用脚本。

---

## 常见坑

**把默认配置当最优配置。** 很多参数的默认值恰好落在贵的那一档（例如 max_tokens 默认值高于分档线）。核算时顺手检查一遍默认值，往往能直接省几倍。

**忽略缓存。** 缓存命中价通常是输入价的 1/5 左右。长 system prompt、固定知识库前缀这类重复输入，用显式前缀缓存能省大头。任何"持续跑"的核算都要问一句：这里面有多少是每次都重复的输入？

**把单价低当成便宜。** 高分辨率视频的**单价**可能更低，但 token 用量涨得更快，总价更高。永远算总量，不看单价排序。

**拿一次的成本乘以次数。** 持续跑要考虑缓存命中率上升、批量折扣、免费额度。免费额度尤其容易漏——有些能力有每月免费额度，量小的时候实际成本是零。
