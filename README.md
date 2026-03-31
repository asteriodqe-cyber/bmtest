<div align="center">

[中文](#中文) | [English](#english)

# PRD Skill Benchmark

</div>

---

<a name="中文"></a>
## 中文

围绕 [Anthropic Skill 框架](https://github.com/anthropics/skills) 构建的评估框架，测试 **Agent 生成 PRD Skill 的能力**。

### 核心思路

一个 Skill 的价值体现在它能否让 Agent 的输出变得更好。因此本框架的核心指标是 **Skill 增益（Skill Gain）**：
```
Skill 增益 = (有Skill得分 - 基线得分) / (1 - 基线得分)
```

每个 Benchmark 均通过 **有 Skill vs 无 Skill** 的对比来衡量 Agent 生成的 Skill 的增量价值。

### 设计背景

PRD Skill 属于**偏好型 Skill（Preference Skill）**：它固化的是团队偏好的 PRD 格式和流程，而非赋予 Agent 新的能力。外部工具调用（如 Jira API）明确不在评估范围内，B3 测试的是文档内的流程编排，而非外部系统集成。

### 评估架构

**被评估者（PRD 生成）**：Kimi K2.5（Moonshot）  
**评估者（LLM Judge）**：Claude Sonnet 4.6（Anthropic）

使用不同模型分别承担生成和评估角色，避免自我评估偏差。

### 三个 Benchmark

| Benchmark | 测试内容 | 评估方式 |
|-----------|---------|---------|
| **B1 — 基础结构合规性** | Skill 能否引导 Kimi 产出结构完整的 PRD？ | 断言验证（规则 + LLM）|
| **B2 — 条件场景适配** | Skill 能否根据产品类型（B2B / C端 / 内部工具）引导 Kimi 调整 PRD 风格？ | 多场景断言验证 |
| **B3 — 流程编排完整性** | Skill 能否引导 Kimi 完成 PRD → 任务拆解，且任务与 PRD 存在语义关联？ | 步骤 + 依赖断言验证 |

### 评估方式

**断言驱动（Assertion-based）** 替代抽象连续打分。每条检查都是具体的、可二进制判定的陈述：
```json
{
  "id": "background_before_stories",
  "check": "'背景'章节出现在'用户故事'章节之前",
  "type": "structural"
}
```

**双层评估体系**：

| 层级 | 方式 | 适用场景 |
|---|---|---|
| Rule-based | 关键词匹配、章节顺序验证 | 格式合规性检查 |
| LLM-as-Judge | Claude 批量评估，5条断言合并1次调用 | 存在性、内容质量检查 |

### 实验设计

两个条件对比：

| 条件 | 描述 |
|------|------|
| `baseline` | Kimi 仅接收用户需求，无任何 Skill 指导 |
| `with_skill` | Kimi 接收用户需求 + 生成的 SKILL.md 作为系统上下文 |

同时对比两组 Skill 来源：

| 来源 | 生成方式 |
|------|------|
| `zero_shot` | Kimi K2.5 快速模式，无示例直接生成 |
| `few_shot` | Kimi K2.5 思考模式，参考 baseline + prd-taskmaster 设计思想 |

### 目录结构
```
prd-skill-benchmark/
├── README.md
├── .env.example                    # API Key 配置模板
├── requirements.txt
├── run_all.ps1 / run_all.sh        # 一键跑完所有实验
├── benchmark/
│   ├── assertions/
│   │   ├── b1_structure.json       # B1 断言定义（22条）
│   │   ├── b2_conditional.json     # B2 场景断言定义
│   │   └── b3_orchestration.json   # B3 流程断言定义
│   └── test_cases/
│       ├── b1_inputs.json          # B1：7个用例（5标准+2边界）
│       ├── b2_inputs.json          # B2：9个用例（6标准+3边界）
│       └── b3_inputs.json          # B3：5个用例（3标准+2边界）
├── evaluators/
│   ├── runner.py                   # Kimi K2.5 异步执行器（流式传输）
│   ├── assertion_checker.py        # Rule-based 断言评估
│   ├── llm_judge.py                # Claude LLM Judge（批量评估）
│   ├── gain_calculator.py          # Skill 增益计算
│   └── parallel_eval.py            # 异步并发执行（断点续传+样本保存）
├── datasets/
│   ├── source_skills/              # Baseline Skill 参考文件
│   └── generated_skills/
│       ├── zero_shot/              # Kimi 快速模式生成的 Skill
│       └── few_shot/               # Kimi 思考模式生成的 Skill
├── experiments/
│   ├── results.csv                 # 量化对比结果（自动追加）
│   ├── report.md                   # 实验报告（含局限性分析）
│   ├── checkpoint.json             # 断点续传记录（运行时自动生成）
│   └── samples/                    # 每次 run 的详细样本（PRD+断言判断）
├── logs/                           # 运行日志（运行时自动生成）
└── tests/
    ├── test_assertion_checker.py
    └── test_gain_calculator.py
```

### Pass/Fail 阈值

| Benchmark | 增益阈值 | 状态 |
|-----------|---------|------|
| B1 | ≥ 0.6 | 初始设定（待校准）|
| B2 | ≥ 0.5 | 初始设定（待校准）|
| B3 | ≥ 0.5 | 初始设定（待校准）|

### 快速开始
```bash
pip install -r requirements.txt

# 配置 API Key
cp .env.example .env
# 编辑 .env 填入 MOONSHOT_API_KEY 和 ANTHROPIC_API_KEY

# 跑 B1（zero_shot Skill，3次采样）
python evaluators/parallel_eval.py \
  --skill datasets/generated_skills/zero_shot/skill_v1.md \
  --benchmark b1 \
  --n-runs 3

# 跑 B2（指定场景）
python evaluators/parallel_eval.py \
  --skill datasets/generated_skills/zero_shot/skill_v1.md \
  --benchmark b2 \
  --scenario b2b \
  --n-runs 3

# 一键跑完所有实验（Windows）
.\run_all.ps1 -Skill datasets/generated_skills/zero_shot/skill_v1.md
```

### 技术说明

**Kimi K2.5 调用方式**：直接通过 aiohttp 调用 `api.moonshot.cn`，使用流式传输（stream=True）解决长 PRD 生成的超时问题。temperature 固定为 1.0（Kimi K2.5 流式模式强制要求）。

**异步并发**：使用 asyncio + aiohttp，Semaphore=3 控制并发数，避免触发 429 限流。

**断点续传**：精确到单次 run，中断后重新运行自动跳过已完成的 run。

**样本透明化**：每次 run 的完整 PRD 内容和断言判断详情保存在 `experiments/samples/`，支持人工复核，避免评估黑箱。

### Surrogate Agent 元数据

所有实验自动记录以下元数据，确保结果可复现：
```json
{
  "surrogate_agent": "kimi-k2.5",
  "api_provider": "moonshot",
  "temperature": 1.0,
  "thinking_mode": "instant",
  "timestamp": "YYYY-MM-DD",
  "n_runs": 3,
  "skill_hash": "sha256:..."
}
```

### 参考资料

- [Anthropic Skills 框架](https://github.com/anthropics/skills)
- [SkillsBench：评估 Agent Skill 效果的基准](https://arxiv.org/abs/2602.12670)
- [Kimi K2.5 API 文档](https://platform.moonshot.ai/docs/guide/kimi-k2-5-quickstart)
- [τ-Bench: pass^k 可靠性指标](https://arxiv.org/abs/2406.12045)
- [AgentBench: 将 LLM 作为 Agent 评估](https://openreview.net/forum?id=zAdUB0aCTQ)
- [prd-taskmaster Skill（设计思想参考）](https://skills.sh/anombyte93/prd-taskmaster/prd-taskmaster) — 由 Kimi K2.5 思考模式提取核心设计思想，融入 baseline Skill 设计

---

<a name="english"></a>
## English

A benchmark framework built around [Anthropic's Skill framework](https://github.com/anthropics/skills), evaluating an **Agent's ability to generate PRD Skills**.

### Core Idea
```
Skill Gain = (score_with_skill - score_baseline) / (1 - score_baseline)
```

Every benchmark compares **with-Skill vs no-Skill** outputs to measure the incremental value of the generated Skill.

### Evaluation Architecture

**PRD Generator**: Kimi K2.5 (Moonshot)  
**LLM Judge**: Claude Sonnet 4.6 (Anthropic)

Using different models for generation and evaluation avoids self-assessment bias.

### Three Benchmarks

| Benchmark | What It Tests | Evaluation Method |
|-----------|--------------|-------------------|
| **B1 — Structure Compliance** | Does the Skill guide Kimi to produce a structurally complete PRD? | Assertion-based (rule + LLM) |
| **B2 — Conditional Adaptation** | Does the Skill adapt PRD style by product type (B2B / Consumer / Internal)? | Multi-scenario assertions |
| **B3 — Process Orchestration** | Does the Skill guide a multi-step flow (PRD → tasks) with semantic traceability? | Step + dependency assertions |

### Two-Layer Evaluation

| Layer | Method | Use Case |
|---|---|---|
| Rule-based | Keyword matching, section order | Format compliance |
| LLM-as-Judge | Claude batch evaluation (5 assertions per call) | Existence checks, content quality |

### Experiment Design

| Condition | Description |
|-----------|-------------|
| `baseline` | Kimi receives user prompt with no Skill |
| `with_skill` | Kimi receives user prompt + generated SKILL.md as system context |

| Skill Source | Generation Method |
|--------|-------------|
| `zero_shot` | Kimi K2.5 fast mode, no examples |
| `few_shot` | Kimi K2.5 thinking mode, with baseline + prd-taskmaster reference |

### Quick Start
```bash
pip install -r requirements.txt

cp .env.example .env
# Fill in MOONSHOT_API_KEY and ANTHROPIC_API_KEY

python evaluators/parallel_eval.py \
  --skill datasets/generated_skills/zero_shot/skill_v1.md \
  --benchmark b1 \
  --n-runs 3
```

### Technical Notes

**Kimi K2.5**: Called directly via aiohttp to `api.moonshot.cn` with streaming (stream=True). Temperature is fixed at 1.0 (required by Kimi K2.5 streaming mode).

**Async concurrency**: asyncio + aiohttp, Semaphore=3 to avoid 429 rate limits.

**Checkpoint resume**: Precise to single run level. Interrupted experiments resume automatically.

**Sample transparency**: Full PRD content and assertion judgments saved to `experiments/samples/` for human review.

### References

- [Anthropic Skills Framework](https://github.com/anthropics/skills)
- [SkillsBench: Benchmarking Agent Skills](https://arxiv.org/abs/2602.12670)
- [Kimi K2.5 API Docs](https://platform.moonshot.ai/docs/guide/kimi-k2-5-quickstart)
- [τ-Bench: pass^k reliability metric](https://arxiv.org/abs/2406.12045)
- [AgentBench: Evaluating LLMs as Agents](https://openreview.net/forum?id=zAdUB0aCTQ)
- [prd-taskmaster Skill (Design Reference)](https://skills.sh/anombyte93/prd-taskmaster/prd-taskmaster) — Key design principles extracted by Kimi K2.5 thinking mode and integrated into baseline Skill design
