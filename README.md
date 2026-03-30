<div align="center">

[中文](#中文) | [English](#english)

# PRD Skill Benchmark

</div>

---

<a name="中文"></a>
## 中文

本项目是一个评估框架，专门测试 **Agent 生成 PRD Skill 的能力** —— 即生成能够指导 Claude 产出高质量产品需求文档的结构化指令文件。

### 这个 Benchmark 在测什么

**Agent 能否生成一个有效的 Skill，使 Claude 产出的 PRD 质量得到提升。**

核心指标是 **Skill 增益（Skill Gain）**：
```
Skill 增益 = (有Skill得分 - 基线得分) / (1 - 基线得分)
```

### 背景

本 Benchmark 基于 [Anthropic 的 Skill 框架](https://github.com/anthropics/skills) 构建。PRD Skill 属于**偏好型 Skill（Preference Skill）**：固化团队偏好的 PRD 格式和流程，而非赋予 Claude 新能力。

### 三个 Benchmark

| Benchmark | 测试内容 | 评估方式 |
|-----------|---------|---------|
| **B1 — 基础结构合规性** | Skill 能否引导 Claude 产出结构完整的 PRD？ | 断言验证（规则 + LLM）|
| **B2 — 条件场景适配** | Skill 能否根据产品类型自动调整 PRD 风格？ | 多场景断言验证 |
| **B3 — 流程编排完整性** | Skill 能否引导 Claude 完成 PRD → 任务拆解，且存在语义关联？ | 步骤 + 依赖断言验证 |

### 目录结构
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
│   ├── results.csv
│   └── report.md
└── requirements.txt
```

### 快速开始
```bash
pip install -r requirements.txt
python evaluators/runner.py --skill datasets/generated_skills/zero_shot/skill_v1.md --benchmark b1
```

### Pass/Fail 阈值

| Benchmark | 增益阈值 | 状态 |
|-----------|---------|------|
| B1 | ≥ 0.6 | 初始设定（待校准）|
| B2 | ≥ 0.5 | 初始设定（待校准）|
| B3 | ≥ 0.5 | 初始设定（待校准）|

### 参考资料

- [Anthropic Skills 框架](https://github.com/anthropics/skills)
- [τ-Bench: pass^k 可靠性指标](https://arxiv.org/abs/2406.12045)
- [AgentBench](https://openreview.net/forum?id=zAdUB0aCTQ)

---

<a name="english"></a>
## English

A benchmark framework for evaluating an Agent's ability to generate PRD Skills — structured instruction files that guide Claude to produce high-quality Product Requirements Documents.

### What This Benchmarks

It evaluates whether an **Agent can generate a Skill that makes PRDs better**.

The core metric is **Skill Gain**:
```
Skill Gain = (score_with_skill - score_baseline) / (1 - score_baseline)
```

### Background

Built on [Anthropic's Skill framework](https://github.com/anthropics/skills). A PRD Skill is a **Preference Skill**: it encodes a team's preferred PRD format and process, not a new capability.

### Three Benchmarks

| Benchmark | What It Tests | Evaluation Method |
|-----------|--------------|-------------------|
| **B1 — Structure Compliance** | Does the Skill guide Claude to produce a structurally complete PRD? | Assertion-based (rule + LLM) |
| **B2 — Conditional Adaptation** | Does the Skill adapt PRD style by product type (B2B / Consumer / Internal)? | Multi-scenario assertions |
| **B3 — Process Orchestration** | Does the Skill guide a multi-step flow (PRD → tasks) with semantic traceability? | Step + dependency assertions |

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
│   ├── results.csv
│   └── report.md
└── requirements.txt
```

### Quick Start
```bash
pip install -r requirements.txt
python evaluators/runner.py --skill datasets/generated_skills/zero_shot/skill_v1.md --benchmark b1
```

### Pass/Fail Thresholds

| Benchmark | Gain Threshold | Status |
|-----------|---------------|--------|
| B1 | ≥ 0.6 | Initial (pre-calibration) |
| B2 | ≥ 0.5 | Initial (pre-calibration) |
| B3 | ≥ 0.5 | Initial (pre-calibration) |

### References

- [Anthropic Skills Framework](https://github.com/anthropics/skills)
- [τ-Bench: pass^k reliability metric](https://arxiv.org/abs/2406.12045)
- [AgentBench](https://openreview.net/forum?id=zAdUB0aCTQ)
