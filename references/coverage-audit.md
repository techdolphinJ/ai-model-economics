# Cost-model 覆盖审计与更新契约

快照：2026-07-21 ｜ 失效：90 天 ｜ 目标：让 calculator 只对已公开、可复核的计费单位输出数字。

## 已覆盖的计费面

| 面 | 机器源 | 计算器 | 覆盖 |
|---|---|---|---|
| 按量文本 token | `model_prices.json` | `scripts/model_cost.py` | 54 个 SKU：直连模型、云托管路由、开源模型网关、带请求附加费的搜索模型 |
| GPU/实例/预留吞吐 | `infrastructure_prices.json` | `scripts/infrastructure_cost.py` | AWS Capacity Blocks、Azure PAYG VM、GCP GPU/整机、阿里 PTU、百度算力单元、华为价格空值 |
| 火山多模态/Agent/RAG | `volcengine.md` | `scripts/video_cost.py` | 文本、视频、图片、3D、Agent、工具、知识库、限流、下线 |

## 厂商覆盖（文字模型）

- 直连：OpenAI、Anthropic、Google Gemini、xAI、Mistral、Cohere、DeepSeek、智谱、MiniMax、Kimi、阶跃、商汤。
- 云托管：AWS Bedrock、Azure AI Foundry、Vertex AI、阿里百炼、百度千帆、腾讯 TokenHub、火山方舟。
- 开源/多模型网关：Groq、Together；此类价格必须按网关路由使用，绝不能回填为模型原厂价。
- 搜索模型：Perplexity Sonar 的 token 费与每请求搜索上下文费均单独建模。

## 有意保留为 null / 未纳入 runtime 的项目

| 对象 | 结论 | 原因与处理 |
|---|---|---|
| Meta 直连 Llama API | 不建直连 SKU | 未发现 Meta 官方第一方按量 token API 静态价；仅通过 Groq/Together 等路由核算。 |
| AI21 Studio | 价格为 null | 官方文档指向动态价格页、无可匿名核对的每模型静态表；保留来源，不给 calculator 数字。 |
| 华为盘古/ModelArts 推理 | `rate: null` | 官方匿名文档仅公开包周期/按需规则，未给可核验具体单价。 |
| AWS EC2 普通 On-Demand GPU | 不以 Capacity Blocks 代替 | 可公开核验的是 Capacity Blocks；它是预留模式。普通按需价格应在有账户/区域 SKU 时另抓。 |
| 中国云 GPU 裸实例 | 不做猜测快照 | 多数最新价格须区域与登录态；仅记录已公开的百度算力、阿里 PTU。 |
| 订阅计划 | 不混入 API | Chat/助手订阅额度不等价于 API token 费。 |

## 更新规则

1. 单价、缓存价、批处理、区域/部署型、单位、来源 URL、快照日期、限流与生命周期缺一不可；页面没有的数据就是 `null`。
2. 价格跨币种、跨路由、跨区域或跨购买模式时，calculator 不做自动比较或换汇。
3. `total_price_complete: false` 的基础设施 SKU 只能作为组件费；输出必须提示仍需计算 VM/存储/网络/OS 等成本。
4. `preview`、`deprecated`、`temporary-price`、`legacy-route` 不能成为超过 6 个月的默认架构基准。
5. 过 90 天自动告警；正式客户报价必须刷新页面并记录变更。
