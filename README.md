<div align="center">

[中文](#中文) | [English](#english)

# PRD Skill Benchmark

**一个基于增量收益的 Agent Skill 评估框架**

</div>

---

<a name="中文"></a>
## 中文

### 核心问题：为什么传统评估方法不够用？

当我们问"这个 Skill 好不好"时，通常的做法是让 LLM 打个分。但这有一个根本性的缺陷：

> **绝对分数无法区分"Skill 本身好"和"模型基础能力强"。**

如果 Kimi K2.5 不用任何 Skill 就能生成 0.65 分的 PRD，而加了 Skill 之后变成 0.68 分——这个 Skill 真的有价值吗？更严重的问题是：**0.68 分的 PRD 能交付给开发团队吗？**

这就是这个框架要解决的问题。

---

### 我的解法：三层评估体系

**第一层：Skill Gain（增量收益）**

不看绝对分数，看 Skill 带来了多少增量：
```
Skill Gain = (有Skill得分 - 无Skill得分) / (1 - 无Skill得分)
```

归一化设计让不同 baseline 水平的场景可以横向比较。

**第二层：Quality Floor（可交付性门槛）**

Gain 高但绝对质量低的 Skill 在实际工作中没有价值。我们设定质量底线：B1 ≥ 0.60，B2 ≥ 0.55，B3 ≥ 0.55。只有同时满足 Gain 和 Quality Floor 的 Skill 才算真正有效。

**第三层：Efficacy Matrix（效用矩阵）**

| 等级 | 条件 | 含义 |
|---|---|---|
| HIGH 🟢 | Gain > 0.5 且 score ≥ Floor | Skill 带来显著且可交付的提升 |
| MEDIUM 🟡 | Gain 0.2-0.5 且 score ≥ Floor | Skill 有一定价值 |
| LOW 🔴 | Gain < 0.2 或 score < Floor | Skill 未带来有效提升 |

---

### 三个 Benchmark 的设计逻辑

对应 PRD Skill 作为"偏好型 Skill"的三个核心能力维度，形成递进的能力阶梯：
```
结构合规（能力基线）→ 场景适配（判断力）→ 流程编排（系统能力）
```

| Benchmark | 测试的能力 | 评估方式 |
|---|---|---|
| **B1 — 基础结构合规性** | Skill 能否引导产出结构完整的 PRD？ | Rule 断言 + Claude 批量 Judge |
| **B2 — 条件场景适配** | Skill 能否根据 B2B/C端/内部工具调整风格？ | 多场景断言验证 |
| **B3 — 流程编排完整性** | Skill 能否引导 PRD→任务拆解且语义关联？ | 步骤 + 依赖断言 |

---

### 三个实验发现

**发现一：B2B 场景下 zero_shot Skill 几乎没有增量价值（Gain=+0.032）**

不是 Skill 写得差，而是 Kimi K2.5 本身对 B2B 产品的理解已经很强（baseline=0.689），Skill 的边际空间被压缩。这揭示了一个规律：**Baseline 越强的场景，Skill 越难体现价值**。

few_shot Skill 通过引入专门的 B2B 差异化指引（RBAC、多租户、审计日志），将 B2B Gain 从 +0.032 提升到 +0.270——证明正确的 Skill 设计可以突破这个天花板。

**发现二：zero_shot Skill 在流程编排（B3）产生负 Gain（-0.078）**

Skill 不仅没有帮助，反而让结果变差。原因是 zero_shot Skill 的强结构约束把 Kimi 的注意力锁定在 PRD 格式上，抑制了它自然生成任务拆解的倾向。没有 Skill 约束时，Kimi 反而更自由地完成了完整流程。

**结论：错误的 Skill 比没有 Skill 更糟糕。**

**发现三：Rule 断言存在系统性低估，偏向英文思维**

通过主动打开样本 JSON 文件做人工复核，发现一份实际质量约 0.76 的 PRD 被自动评估为 0.578。根本原因是 Rule 断言的关键词基于英文标准模板，而 Kimi 使用中文惯用标题（"页面布局与交互"而非"UX Design"）。

这推动了 v2 断言版本的诞生——两个版本并存，通过 `--assertions-version` 参数切换，让评估偏差本身可以被量化。

---

### 实验结果摘要

| Benchmark | 场景 | zero_shot Gain | few_shot Gain | 结论 |
|---|---|---|---|---|
| B1 结构合规 | — | +0.231 MEDIUM 🟡 | +0.326 MEDIUM 🟡 | few_shot 提升 +0.095 |
| B2 场景适配 | B2B | +0.032 LOW 🔴 | +0.270 MEDIUM 🟡 | few_shot 提升 +0.238 |
| B2 场景适配 | Consumer | +0.117 LOW 🔴 | +0.233 MEDIUM 🟡 | few_shot 提升 +0.116 |
| B2 场景适配 | Internal | +0.224 MEDIUM 🟡 | +0.206 MEDIUM 🟡 | 基本持平 |
| B3 流程编排 | — | -0.078 LOW 🔴 | 待补充 | zero_shot 完全失效 |

---

### 评估架构

**被评估者**：Kimi K2.5（Moonshot）生成 PRD  
**评估者**：Claude Sonnet 4.6（Anthropic）批量 Judge

使用不同模型分别承担生成和评估角色，避免自我评估偏差。

**双层评估体系**：

| 层级 | 方式 | 适用场景 |
|---|---|---|
| Rule-based | 关键词匹配、章节顺序验证 | 格式合规性检查 |
| LLM-as-Judge | Claude 批量评估（5条断言合并1次调用） | 存在性、内容质量检查 |

**断言版本**：

| 版本 | 文件 | 关键词策略 |
|---|---|---|
| v1 | `*_structure.json` | 严格匹配英文标准章节标题 |
| v2 | `*_structure_v2.json` | 扩充中文惯用标题同义词 |

---

### 技术实现亮点

**异步并发 + 流式传输**

直接通过 aiohttp 调用 Moonshot API，stream=True 解决长 PRD 生成超时。asyncio + Semaphore=3 控制并发，在速度和限流之间取得平衡。temperature 固定为 1.0（Kimi K2.5 流式模式强制要求），通过 n_runs=3 多次采样缓解随机性。

**断点续传（精确到单次 run）**

中断后重新运行自动跳过已完成的 run，不丢失任何数据。每完成一次 run 立即写入 `experiments/checkpoint.json`。

**样本透明化（黑箱可审查）**

每次 run 的完整 PRD 内容 + 每条断言的判断结果和 confidence 值保存为 JSON，存入 `experiments/samples/`，支持人工复核。正是这个机制让我们发现了 Rule 断言的系统性偏差。

**双版本断言（偏差可量化）**

v1 和 v2 并存，通过 `--assertions-version` 参数切换，让评估偏差本身成为可观测的数据，而不是隐藏的误差。

---

### 快速开始
```bash
pip install -r requirements.txt
cp .env.example .env
# 填入 MOONSHOT_API_KEY 和 ANTHROPIC_API_KEY

# 跑 B1，默认 v1 断言
python evaluators/parallel_eval.py \
  --skill datasets/generated_skills/zero_shot/skill_v1.md \
  --benchmark b1 \
  --n-runs 3

# 跑 B1，v2 断言（扩充中文关键词）
python evaluators/parallel_eval.py \
  --skill datasets/generated_skills/few_shot/skill_v1.md \
  --benchmark b1 \
  --n-runs 3 \
  --assertions-version v2

# 跑 B2 指定场景
python evaluators/parallel_eval.py \
  --skill datasets/generated_skills/few_shot/skill_v1.md \
  --benchmark b2 \
  --scenario b2b \
  --n-runs 3
```

---

### 目录结构
```
prd-skill-benchmark/
├── README.md
├── .env.example
├── requirements.txt
├── docs/
│   └── decisions.md              # 技术决策日志（7个关键决策）
├── benchmark/
│   ├── assertions/
│   │   ├── b1_structure.json     # v1 断言（22条）
│   │   ├── b1_structure_v2.json  # v2 断言（扩充关键词）
│   │   ├── b2_conditional.json
│   │   ├── b2_conditional_v2.json
│   │   ├── b3_orchestration.json
│   │   └── b3_orchestration_v2.json
│   └── test_cases/
│       ├── b1_inputs.json        # 7个用例（5标准+2边界）
│       ├── b2_inputs.json        # 9个用例（6标准+3边界）
│       └── b3_inputs.json        # 5个用例（3标准+2边界）
├── evaluators/
│   ├── runner.py                 # Kimi K2.5 异步执行器（流式传输）
│   ├── assertion_checker.py      # Rule-based 断言（支持v1/v2）
│   ├── llm_judge.py              # Claude LLM Judge（批量评估）
│   ├── gain_calculator.py        # Skill Gain + Efficacy Matrix
│   └── parallel_eval.py          # 主评估流程（断点续传+样本保存）
├── datasets/
│   ├── source_skills/            # Baseline Skill 参考文件
│   └── generated_skills/
│       ├── zero_shot/            # Kimi 快速模式生成
│       └── few_shot/             # Kimi 思考模式生成
├── experiments/
│   ├── results.csv               # 量化结果（自动追加）
│   ├── report.md                 # 完整实验报告
│   ├── records/                  # 各实验详细记录
│   └── samples/                  # 每次run的PRD+断言JSON
└── logs/                         # 运行日志
```

---

### 参考资料

- [Anthropic Skills 框架](https://github.com/anthropics/skills)
- [SkillsBench：首个 Agent Skill 效果基准](https://arxiv.org/abs/2602.12670) — 本项目差异：SkillsBench 评估已有 Skill 的执行效果，本项目评估 Agent **生成** Skill 的能力
- [Kimi K2.5 API 文档](https://platform.moonshot.ai/docs/guide/kimi-k2-5-quickstart)
- [τ-Bench: pass^k 可靠性指标](https://arxiv.org/abs/2406.12045)
- [prd-taskmaster Skill（设计思想参考）](https://skills.sh/anombyte93/prd-taskmaster/prd-taskmaster) — 由 Kimi K2.5 思考模式提取核心设计思想，融入 baseline 设计

---

<a name="english"></a>
## English

### The Core Problem: Why Traditional Evaluation Falls Short

When evaluating a Skill, the common approach is to have an LLM assign a score. But this has a fundamental flaw:

> **Absolute scores cannot distinguish between "a good Skill" and "a capable model."**

If Kimi K2.5 generates a 0.65-score PRD without any Skill, and 0.68 with a Skill — is that Skill actually valuable? More importantly: **is a 0.68-score PRD deliverable to an engineering team?**

This is the problem this framework solves.

---

### My Solution: Three-Layer Evaluation

**Layer 1: Skill Gain (Incremental Value)**

We measure incremental value, not absolute quality:
```
Skill Gain = (score_with_skill - score_baseline) / (1 - score_baseline)
```

Normalization allows fair comparison across scenarios with different baseline levels.

**Layer 2: Quality Floor (Deliverability Threshold)**

High Gain on low-quality PRDs is meaningless in practice. We set minimum quality thresholds: B1 ≥ 0.60, B2 ≥ 0.55, B3 ≥ 0.55. A Skill must satisfy both Gain and Quality Floor to be considered truly effective.

**Layer 3: Efficacy Matrix**

| Level | Condition | Meaning |
|---|---|---|
| HIGH 🟢 | Gain > 0.5 and score ≥ Floor | Significant, deliverable improvement |
| MEDIUM 🟡 | Gain 0.2-0.5 and score ≥ Floor | Moderate value |
| LOW 🔴 | Gain < 0.2 or score < Floor | No effective improvement |

---

### Three Findings

**Finding 1: B2B zero_shot Skill Gain ≈ 0 (+0.032)**

Not because the Skill is bad, but because Kimi K2.5's built-in B2B knowledge is already strong (baseline=0.689), compressing the Gain headroom. This reveals a pattern: **the stronger the baseline, the harder it is for a Skill to add value.**

few_shot Skill — with dedicated B2B guidance (RBAC, multi-tenancy, audit logs) — raised B2B Gain from +0.032 to +0.270, proving that correctly designed Skills can break through this ceiling.

**Finding 2: zero_shot Skill produces negative Gain in B3 (-0.078)**

The Skill not only failed to help — it made things worse. The Skill's structural constraints locked Kimi's attention onto PRD format, suppressing its natural tendency to generate task breakdowns. Without the Skill, Kimi more freely completed the full PRD→tasks flow.

**Conclusion: A wrong Skill is worse than no Skill.**

**Finding 3: Rule assertions systematically underestimate quality**

Human review of sample JSON files revealed a PRD with actual quality ~0.76 was scored 0.578 automatically. The root cause: Rule assertion keywords were designed for English PRD templates, while Kimi uses Chinese-idiomatic section titles ("页面布局与交互" instead of "UX Design").

This led to the creation of v2 assertions — both versions coexist, switchable via `--assertions-version`, making evaluation bias itself observable and quantifiable.

---

### Evaluation Architecture

**Generator**: Kimi K2.5 (Moonshot)
**Judge**: Claude Sonnet 4.6 (Anthropic)

Using different models for generation and evaluation eliminates self-assessment bias.

**Two-Layer Evaluation**:

| Layer | Method | Use Case |
|---|---|---|
| Rule-based | Keyword matching, section ordering | Format compliance |
| LLM-as-Judge | Claude batch evaluation (5 assertions/call) | Existence checks, content quality |

---

### Key Results

| Benchmark | Scenario | zero_shot Gain | few_shot Gain | Delta |
|---|---|---|---|---|
| B1 Structure | — | +0.231 MEDIUM 🟡 | +0.326 MEDIUM 🟡 | ↑ +0.095 |
| B2 Adaptation | B2B | +0.032 LOW 🔴 | +0.270 MEDIUM 🟡 | ↑↑ +0.238 |
| B2 Adaptation | Consumer | +0.117 LOW 🔴 | +0.233 MEDIUM 🟡 | ↑ +0.116 |
| B2 Adaptation | Internal | +0.224 MEDIUM 🟡 | +0.206 MEDIUM 🟡 | ≈ |
| B3 Orchestration | — | -0.078 LOW 🔴 | TBD | zero_shot failed |

---

### Quick Start
```bash
pip install -r requirements.txt
cp .env.example .env
# Fill in MOONSHOT_API_KEY and ANTHROPIC_API_KEY

# Run B1, default v1 assertions
python evaluators/parallel_eval.py \
  --skill datasets/generated_skills/zero_shot/skill_v1.md \
  --benchmark b1 \
  --n-runs 3

# Run B1, v2 assertions (expanded Chinese keywords)
python evaluators/parallel_eval.py \
  --skill datasets/generated_skills/few_shot/skill_v1.md \
  --benchmark b1 \
  --n-runs 3 \
  --assertions-version v2

# Run B2 with specific scenario
python evaluators/parallel_eval.py \
  --skill datasets/generated_skills/few_shot/skill_v1.md \
  --benchmark b2 \
  --scenario b2b \
  --n-runs 3
```

---

### References

- [Anthropic Skills Framework](https://github.com/anthropics/skills)
- [SkillsBench: Benchmarking Agent Skills](https://arxiv.org/abs/2602.12670) — difference: SkillsBench evaluates existing Skills; this project evaluates the ability to **generate** Skills
- [Kimi K2.5 API Docs](https://platform.moonshot.ai/docs/guide/kimi-k2-5-quickstart)
- [τ-Bench: pass^k reliability metric](https://arxiv.org/abs/2406.12045)
- [prd-taskmaster Skill (Design Reference)](https://skills.sh/anombyte93/prd-taskmaster/prd-taskmaster) — key design principles extracted by Kimi K2.5 thinking mode
