<div align="center">

[中文](#中文) | [English](#english)

# PRD Skill Benchmark

</div>

---

<a name="中文"></a>
## 中文

围绕 [Anthropic Skill 框架](https://github.com/anthropics/skills) 构建的评估框架，测试 **Agent 生成 PRD Skill 的能力**。

### 核心思路

一个 Skill 的价值体现在它能否让 Claude 的输出变得更好。因此本框架的核心指标是 **Skill 增益（Skill Gain）**：Claude 在有 Skill 指导时，相比无 Skill 时的 PRD 质量提升幅度。
```
Skill 增益 = (有Skill得分 - 基线得分) / (1 - 基线得分)
```

每个 Benchmark 均通过 **有 Skill vs 无 Skill** 的对比来衡量 Agent 生成的 Skill 的增量价值。

### 设计背景

PRD Skill 属于**偏好型 Skill（Preference Skill）**：它固化的是团队偏好的 PRD 格式和流程，而非赋予 Claude 新的能力。这一定性决定了整个评估设计的方向——外部工具调用（如 Jira API）明确不在评估范围内，B3 测试的是文档内的流程编排，而非外部系统集成。

### 三个 Benchmark

| Benchmark | 测试内容 | 评估方式 |
|-----------|---------|---------|
| **B1 — 基础结构合规性** | Skill 能否引导 Claude 产出结构完整的 PRD？ | 断言验证（规则 + LLM）|
| **B2 — 条件场景适配** | Skill 能否根据产品类型（B2B / C端 / 内部工具）引导 Claude 调整 PRD 风格？ | 多场景断言验证 |
| **B3 — 流程编排完整性** | Skill 能否引导 Claude 完成 PRD → 任务拆解，且任务与 PRD 存在语义关联？ | 步骤 + 依赖断言验证 |

### 评估方式

**断言驱动（Assertion-based）** 替代抽象连续打分。每条检查都是具体的、可二进制判定的陈述，例如：
```json
{
  "id": "background_before_stories",
  "check": "'背景'章节出现在'用户故事'章节之前",
  "type": "structural"
}
```

**多进程隔离执行**：每个测试用例在独立进程中运行，避免跨运行的上下文污染，每个条件运行 `n=5` 次取平均值。

### 实验设计

两个条件对比：

| 条件 | 描述 |
|------|------|
| `baseline` | Claude / Kimi 仅接收用户需求，无任何 Skill 指导 |
| `with_skill` | Claude / Kimi 接收用户需求 + 生成的 SKILL.md 作为系统上下文 |

同时对比两组 Skill 来源：

| 来源 | 描述 |
|------|------|
| `zero_shot` | Agent 在无示例条件下生成的 Skill |
| `few_shot` | Agent 在有示例条件下生成的 Skill |

### 目录结构
```
prd-skill-benchmark/
├── README.md
├── benchmark/
│   ├── assertions/
│   │   ├── b1_structure.json       # B1 断言定义
│   │   ├── b2_conditional.json     # B2 场景断言定义
│   │   └── b3_orchestration.json   # B3 流程断言定义
│   └── test_cases/
│       ├── b1_inputs.json          # B1 标准输入用例
│       ├── b2_inputs.json          # B2 多场景输入用例
│       └── b3_inputs.json          # B3 多步骤输入用例
├── evaluators/
│   ├── runner.py                   # Surrogate Agent 执行器（支持多 provider）
│   ├── assertion_checker.py        # 规则型断言评估
│   ├── llm_judge.py                # 语义断言的 LLM Judge
│   ├── gain_calculator.py          # Skill 增益计算
│   └── parallel_eval.py            # 多进程隔离执行
├── datasets/
│   ├── source_skills/              # 开源基线 Skill（ground truth）
│   └── generated_skills/
│       ├── zero_shot/              # 无示例条件下生成的 Skill
│       └── few_shot/               # 有示例条件下生成的 Skill
├── experiments/
│   ├── zero_shot/                  # Zero-shot 实验输出
│   ├── few_shot/                   # Few-shot 实验输出
│   ├── results.csv                 # 量化对比结果
│   └── report.md                   # Pass/Fail 阈值 + 校准计划
└── requirements.txt
```

### Pass/Fail 阈值

| Benchmark | 增益阈值 | 状态 |
|-----------|---------|------|
| B1 | ≥ 0.6 | 初始设定（待校准）|
| B2 | ≥ 0.5 | 初始设定（待校准）|
| B3 | ≥ 0.5 | 初始设定（待校准）|

阈值将在 ≥ 20 个 Skill 样本的基线实验完成后进行统计校准，详见 `experiments/report.md`。

### 快速开始
```bash
pip install -r requirements.txt

# 使用 Kimi K2.5（推荐）
export MOONSHOT_API_KEY=your_key
python evaluators/runner.py \
  --skill datasets/generated_skills/zero_shot/skill_v1.md \
  --benchmark b1 \
  --provider moonshot \
  --model kimi-k2.5

# 使用 Claude
export ANTHROPIC_API_KEY=your_key
python evaluators/runner.py \
  --skill datasets/generated_skills/zero_shot/skill_v1.md \
  --benchmark b1 \
  --provider anthropic \
  --model claude-sonnet-4-6
```

### Surrogate Agent 版本控制

所有实验自动记录以下元数据，确保结果可复现：
```json
{
  "surrogate_agent": "kimi-k2.5",
  "api_provider": "moonshot",
  "temperature": 0.1,
  "thinking_mode": "instant",
  "timestamp": "YYYY-MM-DD",
  "n_runs": 5,
  "skill_hash": "sha256:..."
}
```

> **注意**：使用 Kimi K2.5 时请显式启用 Instant mode（关闭 thinking），避免 `reasoning_content` 干扰断言检查。Moonshot API 对 temperature 有映射（实际温度 = 请求温度 × 0.6），`temperature=0.1` 在 Kimi 端实际为 `0.06`，评估结果更稳定。

### 参考资料

- [Anthropic Skills 框架](https://github.com/anthropics/skills)
- [Kimi K2.5 API 文档](https://platform.moonshot.ai/docs/guide/kimi-k2-5-quickstart)
- [τ-Bench: pass^k 可靠性指标](https://arxiv.org/abs/2406.12045)
- [AgentBench: 将 LLM 作为 Agent 评估](https://openreview.net/forum?id=zAdUB0aCTQ)

---

<a name="english"></a>
## English

A benchmark framework built around [Anthropic's Skill framework](https://github.com/anthropics/skills), evaluating an **Agent's ability to generate PRD Skills** — structured instruction files that guide Claude to produce Product Requirements Documents.

### Core Idea

A Skill's value lies in whether it improves Claude's output. The core metric is **Skill Gain**: the improvement in PRD quality when Claude follows a generated Skill, compared to Claude without any Skill.
```
Skill Gain = (score_with_skill - score_baseline) / (1 - score_baseline)
```

Every benchmark compares **with-Skill vs no-Skill** outputs to measure the incremental value of the generated Skill.

### Design Rationale

A PRD Skill is a **Preference Skill**: it encodes a team's preferred PRD format and process, not a new capability. External tool calls (e.g. Jira API) are explicitly out of scope. B3 tests process orchestration within the document, not external system integration.

### Three Benchmarks

| Benchmark | What It Tests | Evaluation Method |
|-----------|--------------|-------------------|
| **B1 — Structure Compliance** | Does the Skill guide Claude to produce a structurally complete PRD? | Assertion-based (rule + LLM) |
| **B2 — Conditional Adaptation** | Does the Skill adapt PRD style by product type (B2B / Consumer / Internal)? | Multi-scenario assertions |
| **B3 — Process Orchestration** | Does the Skill guide a multi-step flow (PRD → tasks) with semantic traceability between tasks and PRD features? | Step + dependency assertions |

### Evaluation Approach

**Assertion-based evaluation** replaces continuous scoring. Each check is a concrete, binary-verifiable statement:
```json
{
  "id": "background_before_stories",
  "check": "'Background' section appears before 'User Stories' section",
  "type": "structural"
}
```

**Parallel isolated execution**: each test case runs in an independent process to prevent context contamination, with `n=5` runs per condition.

### Experiment Design

Two conditions compared across all benchmarks:

| Condition | Description |
|-----------|-------------|
| `baseline` | Claude / Kimi receives the user prompt with no Skill |
| `with_skill` | Claude / Kimi receives the user prompt + generated SKILL.md as system context |

Two Skill sources compared:

| Source | Description |
|--------|-------------|
| `zero_shot` | Skills generated by the Agent without examples |
| `few_shot` | Skills generated by the Agent with examples provided |

### Repository Structure
```
prd-skill-benchmark/
├── README.md
├── benchmark/
│   ├── assertions/
│   │   ├── b1_structure.json
│   │   ├── b2_conditional.json
│   │   └── b3_orchestration.json
│   └── test_cases/
│       ├── b1_inputs.json
│       ├── b2_inputs.json
│       └── b3_inputs.json
├── evaluators/
│   ├── runner.py
│   ├── assertion_checker.py
│   ├── llm_judge.py
│   ├── gain_calculator.py
│   └── parallel_eval.py
├── datasets/
│   ├── source_skills/
│   └── generated_skills/
│       ├── zero_shot/
│       └── few_shot/
├── experiments/
│   ├── zero_shot/
│   ├── few_shot/
│   ├── results.csv
│   └── report.md
└── requirements.txt
```

### Pass/Fail Thresholds

| Benchmark | Gain Threshold | Status |
|-----------|---------------|--------|
| B1 | ≥ 0.6 | Initial (pre-calibration) |
| B2 | ≥ 0.5 | Initial (pre-calibration) |
| B3 | ≥ 0.5 | Initial (pre-calibration) |

Thresholds will be calibrated after baseline experiments on ≥ 20 Skill samples. See `experiments/report.md`.

### Quick Start
```bash
pip install -r requirements.txt

# Using Kimi K2.5 (recommended)
export MOONSHOT_API_KEY=your_key
python evaluators/runner.py \
  --skill datasets/generated_skills/zero_shot/skill_v1.md \
  --benchmark b1 \
  --provider moonshot \
  --model kimi-k2.5

# Using Claude
export ANTHROPIC_API_KEY=your_key
python evaluators/runner.py \
  --skill datasets/generated_skills/zero_shot/skill_v1.md \
  --benchmark b1 \
  --provider anthropic \
  --model claude-sonnet-4-6
```

### Surrogate Agent Versioning

All experiments automatically record the following metadata for reproducibility:
```json
{
  "surrogate_agent": "kimi-k2.5",
  "api_provider": "moonshot",
  "temperature": 0.1,
  "thinking_mode": "instant",
  "timestamp": "YYYY-MM-DD",
  "n_runs": 5,
  "skill_hash": "sha256:..."
}
```

> **Note**: When using Kimi K2.5, explicitly enable Instant mode (disable thinking) to prevent `reasoning_content` from interfering with assertion checks. Moonshot's API applies a temperature mapping (actual = requested × 0.6), so `temperature=0.1` becomes `0.06` on Kimi's end — producing more stable evaluation results.

### References

- [Anthropic Skills Framework](https://github.com/anthropics/skills)
- [Kimi K2.5 API Docs](https://platform.moonshot.ai/docs/guide/kimi-k2-5-quickstart)
- [τ-Bench: pass^k reliability metric](https://arxiv.org/abs/2406.12045)
- [AgentBench: Evaluating LLMs as Agents](https://openreview.net/forum?id=zAdUB0aCTQ)
