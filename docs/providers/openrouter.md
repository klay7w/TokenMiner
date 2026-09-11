# OpenRouter

> Category: **router** · Status: **active**

## Overview

Multi-provider LLM API router. Aggregates hundreds of models behind an OpenAI-compatible API; models with ids ending in ":free" cost $0 per token.

## Current Free Offers

- **OpenRouter Free Models (19 models)** — type `free_tier`, value —, status `active`, confidence `official`
  - 19 models are free (ID ending in ':free', $0 per token). Free variants are subject to platform free-usage rate limits; current numbers are rendered dynamically on the limits page, so they are not recorded as fixed values. See https://openrouter.ai/docs/api-reference/limits.
  - Claim: https://openrouter.ai/models?max_price=0
  - Source: https://openrouter.ai/api/v1/models

## Free Models

| Model | Type | Context | Tools | Vision | Reasoning | Link |
|---|---|---|---|---|---|---|
| `thinkingmachines/inkling-small:free` | text+image+audio | 1M | ✅ | ✅ | ✅ | [↗](https://openrouter.ai/thinkingmachines/inkling-small-20260730) |
| `thinkingmachines/inkling:free` | text+image+audio | 1M | ✅ | ✅ | ✅ | [↗](https://openrouter.ai/thinkingmachines/inkling-20260715) |
| `nvidia/nemotron-3-ultra-550b-a55b:free` | text | 1M | ✅ | ❌ | ✅ | [↗](https://openrouter.ai/nvidia/nemotron-3-ultra-550b-a55b-20260604) |
| `nvidia/nemotron-3.5-lightning:free` | text | 1M | ✅ | ❌ | ✅ | [↗](https://openrouter.ai/nvidia/nemotron-3.5-lightning-20260807) |
| `dots-studio/dots-3-note-preview:free` | text+image | 512K | ✅ | ✅ | ✅ | [↗](https://openrouter.ai/dots-studio/dots-3-note-preview-20260813) |
| `google/gemma-4-26b-a4b-it:free` | text+image+video | 262K | ✅ | ✅ | ✅ | [↗](https://openrouter.ai/google/gemma-4-26b-a4b-it-20260403) |
| `google/gemma-4-31b-it:free` | text+image+video | 262K | ✅ | ✅ | ✅ | [↗](https://openrouter.ai/google/gemma-4-31b-it-20260402) |
| `inclusionai/ling-3.0-flash-fin:free` | text | 262K | ✅ | ❌ | ✅ | [↗](https://openrouter.ai/inclusionai/ling-3.0-flash-fin-20260827) |
| `inclusionai/ling-3.0-flash-sante:free` | text | 262K | ✅ | ❌ | ✅ | [↗](https://openrouter.ai/inclusionai/ling-3.0-flash-sante-20260904) |
| `inclusionai/ling-3.0-flash-vl:free` | text+image+video | 262K | ✅ | ✅ | ✅ | [↗](https://openrouter.ai/inclusionai/ling-3.0-flash-vl-20260910) |
| `nex-agi/nex-n2.5-mini:free` | text+image | 262K | ✅ | ✅ | ✅ | [↗](https://openrouter.ai/nex-agi/nex-n2.5-mini-20260908) |
| `nex-agi/nex-n2.5-pro:free` | text+image | 262K | ✅ | ✅ | ✅ | [↗](https://openrouter.ai/nex-agi/nex-n2.5-pro-20260907) |
| `nvidia/nemotron-3-super-120b-a12b:free` | text | 262K | ✅ | ❌ | ✅ | [↗](https://openrouter.ai/nvidia/nemotron-3-super-120b-a12b-20230311) |
| `poolside/laguna-s-2.1:free` | text | 262K | ✅ | ❌ | ✅ | [↗](https://openrouter.ai/poolside/laguna-s-2.1-20260720) |
| `poolside/laguna-xs-2.1:free` | text | 262K | ✅ | ❌ | ✅ | [↗](https://openrouter.ai/poolside/laguna-xs-2.1-20260625) |
| `cohere/north-mini-code:free` | text | 256K | ✅ | ❌ | ✅ | [↗](https://openrouter.ai/cohere/north-mini-code-20260617) |
| `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free` | text+audio+image+video | 256K | ✅ | ✅ | ✅ | [↗](https://openrouter.ai/nvidia/nemotron-3-nano-omni-30b-a3b-reasoning-20260428) |
| `nvidia/nemotron-3.5-content-safety:free` | text+image | 128K | ❌ | ✅ | ✅ | [↗](https://openrouter.ai/nvidia/nemotron-3.5-content-safety-20260604) |
| `liquid/lfm-2.5-2.6b:free` | text | 66K | ✅ | ❌ | ✅ | [↗](https://openrouter.ai/liquid/lfm-2.5-2.6b-20260811) |

## API

- API base: `https://openrouter.ai/api/v1`
- Compatibility: `openai`

## Context Windows

- Largest free-model context: **1M**
- Free models with published context: 19 of 19

## Rate Limits

_No officially published rate-limit numbers recorded for free usage._

## Requirements

- Account required: yes

## Pros

- 19 free model(s) available
- long-context free models (≥200K)
- free models with tool calling
- free models with reasoning support
- multimodal free models
- high TokenMiner score (89/100, grade A)

## Cons

_No notable drawbacks derived from current data._

## TokenMiner Score

**89/100 — grade A**

| Component | Points | Max |
|---|---|---|
| Free Value | 30 | 30 |
| Model Quality | 20 | 20 |
| Quota & Rate Limit | 8 | 15 |
| Context Window | 10 | 10 |
| API Compatibility | 6 | 10 |
| Ease of Claim | 5 | 5 |
| Platform Reliability | 5 | 5 |
| Transparency | 5 | 5 |

Risk tags: ♾️ Permanent Free Tier

## Recommended For

- Coding
- Reasoning
- Long Context
- Multimodal
- Beginners
- Overall Free API

## Links

- [Official](https://openrouter.ai)
- [Pricing](https://openrouter.ai/models?max_price=0)
- [Docs](https://openrouter.ai/docs)
- [Models](https://openrouter.ai/models)
- [Signup](https://openrouter.ai)

## Sources

- https://openrouter.ai/api/v1/models
- https://openrouter.ai/docs/api-reference/limits

## Last Verified

- Provider: 2026-09-11
- Offer `openrouter-free-models`: 2026-09-11
