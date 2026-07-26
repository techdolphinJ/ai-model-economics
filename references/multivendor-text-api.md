# 多厂商文本 API · 成本快照

```yaml
snapshot_date: 2026-07-21
stale_after_days: 90
scope: 公开按量文本 API；价格单位为币种/百万token，除非另行说明
machine_catalog: references/model_prices.json
```

## 使用边界

- `model_prices.json` 是 `scripts/model_cost.py` 的唯一机器可读来源；本页是审计索引。新增 SKU 以该 JSON 为准，避免人工表与 calculator 产生双真源。
- 不换汇，不把直连 API、云托管路由、区域、吞吐档或企业协议放进同一价格比较。
- `null` 表示官方静态公开页没有可核验的价格，而非免费或零成本。
- 所有供应商配额会随账号、区域、用量层级变化；除明确写出的数字外，核算前要查看对应控制台。

## 国际直连 API（USD / MTok）

| 供应商 | 型号 | 输入 | 缓存读 | 输出 | 批量/其他 | 官方来源 |
|---|---|---:|---:|---:|---|---|
| OpenAI | gpt-5.6-sol | 5 | 0.5 | 30 | Batch/Flex 5折；Priority 2倍 | [pricing](https://developers.openai.com/api/docs/pricing) |
| OpenAI | gpt-5.6-terra | 2.5 | 0.25 | 15 | 同上 | [pricing](https://developers.openai.com/api/docs/pricing) |
| OpenAI | gpt-5.6-luna | 1 | 0.1 | 6 | 同上 | [pricing](https://developers.openai.com/api/docs/pricing) |
| Anthropic | Claude Opus 4.8 | 5 | 0.5 | 25 | 5m/1h 缓存写 6.25/10；Batch 2.5/12.5 | [pricing](https://platform.claude.com/docs/en/about-claude/pricing) |
| Anthropic | Claude Sonnet 4.6 | 3 | 0.3 | 15 | 缓存写 3.75/6；Batch 1.5/7.5 | [pricing](https://platform.claude.com/docs/en/about-claude/pricing) |
| Anthropic | Claude Haiku 4.5 | 1 | 0.1 | 5 | 缓存写 1.25/2；Batch 0.5/2.5 | [pricing](https://platform.claude.com/docs/en/about-claude/pricing) |
| Google | Gemini 3.6 Flash | 1.5 | 0.15 | 7.5 | Batch/Flex 5折；Priority 1.8倍 | [pricing](https://ai.google.dev/gemini-api/docs/pricing) |
| Google | Gemini 3.5 Flash-Lite | 0.3 | 0.03 | 2.5 | Batch/Flex 5折 | [pricing](https://ai.google.dev/gemini-api/docs/pricing) |
| Google | Gemini 3.1 Pro Preview ≤200K | 2 | 0.2 | 12 | >200K 改 4/0.4/18 | [pricing](https://ai.google.dev/gemini-api/docs/pricing) |
| Cohere | Command A | 2.5 | — | 10 | 生产 key 常规模型 500 RPM | [Command A](https://docs.cohere.com/docs/command-a) |
| Cohere | Command R | 0.15 | — | 0.6 | 生产 key 常规模型 500 RPM | [Command R](https://docs.cohere.com/docs/command-r) |

OpenAI 限流见 [rate limits](https://developers.openai.com/api/docs/guides/rate-limits)，Anthropic 见 [rate limits](https://platform.claude.com/docs/en/api/rate-limits)，Gemini 见 [rate limits](https://ai.google.dev/gemini-api/docs/rate-limits)。Preview 不可作为 6 个月以上架构的唯一基准。

### 本轮补充的国际/网关路由

- [xAI](https://docs.x.ai/developers/pricing)：Grok 4.5、Build 0.1、4.3，200K 以上请求须整次套用 long-context 价格；4.3 Batch 为 8 折。
- [Mistral](https://mistral.ai/pricing/api/)：Large / Medium / Small / Devstral Medium；缓存读为输入 1 折、Batch 5 折。
- [Groq](https://console.groq.com/docs/models)：Llama 3.1 8B、Llama 3.3 70B、GPT-OSS 120B/20B，且记录 Developer plan 的 RPM/TPM。
- [Together](https://docs.together.ai/docs/serverless/models)：Llama 3.3、GPT-OSS 路由；无缓存价时不能假设缓存折扣。
- [Perplexity](https://docs.perplexity.ai/docs/getting-started/pricing)：Sonar 另有每千请求搜索上下文费；用 `model_cost.py --requests` 才会计入。

## 云托管路由（不可与直连价互换）

| 云路由 | 型号 / 条件 | 输入 | 缓存读 | 输出 | 官方来源 |
|---|---|---:|---:|---:|---|
| AWS Bedrock US East/West | DeepSeek-V3.2 | 0.62 | — | 1.85 | [pricing](https://aws.amazon.com/bedrock/pricing/) |
| AWS Bedrock extended access | Claude 3.5 Sonnet | 6 | 0.6 | 30 | [pricing](https://aws.amazon.com/bedrock/pricing/) |
| Azure AI Foundry Global | GPT-4.1 | 2 | 0.5 | 8 | [Retail Prices API](https://prices.azure.com/api/retail/prices?api-version=2023-01-01-preview&%24filter=serviceName%20eq%20%27Foundry%20Models%27%20and%20contains%28meterName%2C%20%27gpt%204.1%27%29) |
| Azure AI Foundry Global | GPT-5 | 1.25 | — | 10 | [pricing](https://azure.microsoft.com/en-us/pricing/details/azure-openai/) |
| Vertex AI Global | Gemini 3.5 Flash | 1.5 | 0.15 | 9 | [pricing](https://cloud.google.com/gemini-enterprise-agent-platform/generative-ai/pricing) |

Bedrock 的 Standard/Flex/Priority/Reserved、Azure 的部署型和区域、Vertex 的 Global/非 Global 都会改变成本或吞吐。GPT-4.1 官方 retirement 表列为 deprecated、退役日 2026-10-14，不能作长期基准。

## 中国模型 API（CNY / MTok）

| 厂商/路由 | 型号 / 条件 | 输入 | 缓存读 | 输出 | 官方来源 |
|---|---|---:|---:|---:|---|
| 阿里云百炼 Global | qwen3-max ≤32K | 2.5 | — | 10 | [pricing](https://help.aliyun.com/zh/model-studio/model-pricing) |
| 阿里云百炼 Global | qwen3.5-flash ≤128K | 0.2 | — | 2 | [pricing](https://help.aliyun.com/zh/model-studio/model-pricing) |
| 百度千帆 | ERNIE-5.1 ≤32K | 4 | — | 18 | [pricing](https://cloud.baidu.com/doc/qianfan-docs/s/Jm8r1826a) |
| 百度千帆 | ERNIE-4.5-Turbo | 0.8 | 0.2 | 3.2 | [pricing](https://cloud.baidu.com/doc/qianfan-docs/s/Jm8r1826a) |
| 腾讯 TokenHub | hy3 | 1 | 0.25 | 4 | [pricing](https://cloud.tencent.com/document/product/1823/130055) |
| 智谱 BigModel | GLM-5.2 | 8 | 2 | 28 | [pricing](https://bigmodel.cn/pricing) |
| 智谱 BigModel | GLM-5.1 <32K | 6 | 1.3 | 24 | [pricing](https://bigmodel.cn/pricing) |
| MiniMax | M2.7 | 2.1 | 0.42 | 8.4 | [pricing](https://platform.minimaxi.com/docs/guides/pricing-paygo) |
| Moonshot Kimi | kimi-k3 | 20 | 2 | 100 | [pricing](https://platform.kimi.com/docs/pricing/chat-k3) |
| Moonshot Kimi | kimi-k2.7-code | 6.5 | 1.3 | 27 | [pricing](https://platform.kimi.com/docs/pricing/chat-k27-code) |
| DeepSeek | deepseek-v4-flash | USD 0.14 | USD 0.0028 | USD 0.28 | [pricing](https://api-docs.deepseek.com/quick_start/pricing) |
| DeepSeek | deepseek-v4-pro | USD 0.435 | USD 0.003625 | USD 0.87 | [pricing](https://api-docs.deepseek.com/quick_start/pricing) |
| 阶跃 | step-3.7-flash | 1.35 | 0.27 | 8.1 | [pricing](https://stepfun.mintlify.app/zh/guides/pricing/details) |
| 阶跃 | step-3.5-flash | 0.7 | 0.14 | 2.1 | [pricing](https://stepfun.mintlify.app/zh/guides/pricing/details) |

关键生命周期：腾讯旧混元 API 正迁移至 TokenHub、停止新购；DeepSeek 的旧 `deepseek-chat` 和 `deepseek-reasoner` 将于 2026-07-24 15:59 UTC 退役。Kimi Batch 仅对指定 K2 系列公开为实时价 60%；阿里支持 Batch 的模型为实时价 50%；未公开静态 Batch 价均没有写进计算器。
