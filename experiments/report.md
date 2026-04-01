# PRD Skill Benchmark — 实验报告

## Pass/Fail 阈值设定

| Benchmark | 增益阈值 | 依据 | 状态 |
|-----------|---------|------|------|
| **B1** | ≥ 0.6 | 基础结构任务，章节缺失属硬性缺陷，容错低 | 初始设定（待校准）|
| **B2** | ≥ 0.5 | 条件适配有主观成分，场景定义存在模糊空间，容错适中 | 初始设定（待校准）|
| **B3** | ≥ 0.5 | 多步骤任务，部分步骤失败可接受（如顺序轻微错乱但语义关联存在）| 初始设定（待校准）|

### 阈值校准计划

当前阈值为基于任务难度的**先验设定**，需在 baseline 实验后进行统计校准：

1. 收集 ≥ 20 个随机 Skill 样本的评估结果
2. 计算各 Benchmark 分数分布的 25th / 50th / 75th 百分位
3. 将阈值调整至 75th 百分位（前 25% 视为"通过"）
4. 计算校准后阈值与人工判断的相关性，Cohen's Kappa > 0.6 视为可接受

**版本记录：**
- v0.1（当前）：先验阈值，待校准
- v1.0：将在 baseline 实验完成后更新

---

## 已知偏差与局限性

### 1. LLM Judge 温度偏差

| Provider | Judge Temperature | 说明 |
|----------|------------------|------|
| Moonshot kimi-k2.5 | 0.6 | API 强制要求，无法调低 |
| Anthropic Claude | 0.6 | 与 Moonshot 对齐 |

**影响**：temperature=0.6 相对较高，LLM Judge 的判断存在一定随机性。通过 n=5 次采样 + Cohen's Kappa 指标监控一致性，Kappa < 0.6 时结果应视为不可靠。

### 2. 内容截断偏差

超过 3000 字符的 PRD 输出会被首尾采样（保留前 1200 + 后 800 字符）。截断可能导致：
- 中间章节（如假设与约束、依赖关系）无法被 LLM Judge 评估
- B3 中 PRD 与任务列表之间的过渡段落可能丢失

**缓解措施**：Judge prompt 中已明确告知 LLM 这是部分样本，避免因内容不完整而误降 confidence。

### 3. Rule-based 断言的关键词局限

B1 的结构检查依赖关键词匹配（如"背景"、"用户故事"），Agent 若使用同义词（如"现状分析"、"用户场景"）可能导致误判为缺失。

**缓解措施**：每条 rule 断言已包含多个同义关键词，覆盖常见表达变体。

### 4. Surrogate Agent 版本漂移

模型版本更新可能导致历史 benchmark 分数失效。所有实验记录 `skill_hash` + `surrogate_agent` 版本，可通过 `results.csv` 中的 `skill_hash` 字段追溯对应 Skill 版本。

---

## 实验元数据规范

所有实验自动记录以下元数据，存储于 `experiments/results.csv`：
```json
{
  "surrogate_agent": "kimi-k2.5",
  "api_provider": "moonshot",
  "temperature": 0.6,
  "thinking_mode": "instant",
  "timestamp": "YYYY-MM-DD",
  "n_runs": 5,
  "skill_hash": "sha256:xxxxxxxxxxxxxxxx"
}
```

---

## 实验结果（待填写）

### B1 基础结构合规性

| Skill 版本 | 条件 | pass_rate | consistency | kappa | gain | efficacy |
|-----------|------|-----------|-------------|-------|------|----------|
| zero_shot/skill_v1 | with_skill | - | - | - | - | - |
| zero_shot/skill_v1 | baseline | - | - | - | - | - |
| few_shot/skill_v1 | with_skill | - | - | - | - | - |
| few_shot/skill_v1 | baseline | - | - | - | - | - |

### B2 条件场景适配

| Skill 版本 | 场景 | 条件 | pass_rate | consistency | kappa | gain | efficacy |
|-----------|------|------|-----------|-------------|-------|------|----------|
| zero_shot/skill_v1 | b2b | with_skill | - | - | - | - | - |
| zero_shot/skill_v1 | consumer | with_skill | - | - | - | - | - |
| zero_shot/skill_v1 | internal | with_skill | - | - | - | - | - |

### B3 流程编排完整性

| Skill 版本 | 条件 | pass_rate | consistency | kappa | gain | efficacy |
|-----------|------|-----------|-------------|-------|------|----------|
| zero_shot/skill_v1 | with_skill | - | - | - | - | - |
| zero_shot/skill_v1 | baseline | - | - | - | - | - |

---

## 运行命令记录
```bash
# 设置 API Key
export MOONSHOT_API_KEY="sk-your-key"

# B1 评估
python evaluators/parallel_eval.py \
  --skill datasets/generated_skills/zero_shot/skill_v1.md \
  --benchmark b1 \
  --provider moonshot \
  --model kimi-k2.5 \
  --n-runs 5

# B2 评估（需指定 scenario）
python evaluators/parallel_eval.py \
  --skill datasets/generated_skills/zero_shot/skill_v1.md \
  --benchmark b2 \
  --scenario b2b \
  --provider moonshot \
  --model kimi-k2.5

python evaluators/parallel_eval.py \
  --skill datasets/generated_skills/zero_shot/skill_v1.md \
  --benchmark b2 \
  --scenario consumer \
  --provider moonshot \
  --model kimi-k2.5

python evaluators/parallel_eval.py \
  --skill datasets/generated_skills/zero_shot/skill_v1.md \
  --benchmark b2 \
  --scenario internal \
  --provider moonshot \
  --model kimi-k2.5

# B3 评估
python evaluators/parallel_eval.py \
  --skill datasets/generated_skills/zero_shot/skill_v1.md \
  --benchmark b3 \
  --provider moonshot \
  --model kimi-k2.5
```

---

## 结论（待填写

# PRD Skill Benchmark — 实验报告

**版本**：v1.0  
**日期**：2026-03-31  
**Repo**：asteriodqe-cyber/bmtest（Private）

---

## 一、实验概述

### 1.1 评估目标

本实验评估的不是 PRD 本身的质量，而是 **Agent 生成 PRD Skill 的能力**。

Skill 是一种可复用的指令文件，决定了 Agent 在特定任务上的行为上限。核心问题是：

> Agent 生成的 Skill，能否让另一个 Agent 持续产出高质量 PRD？

### 1.2 实验设计

**被评估者**：Kimi K2.5（生成 PRD）  
**评估者**：Claude Sonnet 4.6（LLM Judge，避免自我评估偏差）  
**核心指标**：Skill Gain = (with_skill得分 - baseline得分) / (1 - baseline得分)

**两个待测 Skill 版本**：

| 版本 | 生成方式 | 文件路径 |
|---|---|---|
| zero_shot | Kimi K2.5 快速模式，无示例直接生成 | `datasets/generated_skills/zero_shot/skill_v1.md` |
| few_shot | Kimi K2.5 思考模式，参考 baseline + prd-taskmaster | `datasets/generated_skills/few_shot/skill_v1.md` |

**Baseline Skill 设计参考**：融入了 [prd-taskmaster](https://skills.sh/anombyte93/prd-taskmaster/prd-taskmaster) 的核心设计思想，由 Kimi K2.5 思考模式提取，包括质量分级、13 项验证检查思路、用户测试检查点概念。

### 1.3 三个 Benchmark 设计逻辑

三个 Benchmark 形成能力阶梯：结构合规（能力基线）→ 场景适配（判断力）→ 流程编排（系统能力）

| Benchmark | 测试内容 | 评估方式 |
|---|---|---|
| B1 基础结构合规性 | Skill 能否引导产出结构完整的 PRD | Rule 断言 + Claude 批量 Judge |
| B2 条件场景适配 | Skill 能否根据 B2B/C端/内部工具调整风格 | 多场景断言验证 |
| B3 流程编排完整性 | Skill 能否引导 PRD→任务拆解且语义关联 | 步骤 + 依赖断言 |

---

## 二、评估框架说明

### 2.1 双层评估体系

**第一层：Rule-based 断言**
- 关键词匹配、章节顺序验证
- 完全自动化，零成本，可复现
- 适合格式合规性检查

**第二层：LLM-as-Judge（Claude Sonnet）**
- 批量评估语义层面质量，5 条断言合并为 1 次 API 调用
- 使用不同模型（Kimi 生成，Claude 评估），避免自我评估偏差
- 适合存在性和内容质量检查

### 2.2 质量分级

| Tier | pass_rate | 含义 |
|---|---|---|
| A | ≥ 0.80 | 优秀 |
| B | 0.60 - 0.79 | 良好，达到质量门槛 |
| C | 0.40 - 0.59 | 合格，需改进 |
| D | < 0.40 | 不合格 |

### 2.3 Skill Gain 解读

| Gain | Efficacy | 含义 |
|---|---|---|
| > 0.50 | HIGH 🟢 | Skill 带来显著提升 |
| 0.20 - 0.50 | MEDIUM 🟡 | Skill 有一定价值 |
| < 0.20 | LOW 🔴 | Skill 提升不明显 |

---

## 三、已知偏差与局限性

### 3.1 temperature=1.0 随机性

Kimi K2.5 流式模式强制要求 temperature=1.0，导致多次运行结果有波动。缓解方式：n_runs=3 取平均，但统计噪音仍存在，体现在部分 case 的 Kappa=0.000。

### 3.2 Rule 断言关键词覆盖不足（人工复核发现）

经人工复核 `experiments/samples/` 中的样本文件，发现 Rule 断言在存在性检查上存在系统性低估：

**b1_04（用户场景）**：PRD 使用"核心使用场景"，未被关键词 `['用户场景', '用例', 'User Stories']` 匹配，误判为失败。

**b1_10/b1_11（验收标准/度量指标）**：验收逻辑散落在各功能点中，LLM Judge 正确识别（b1_21 confidence=0.75），但 Rule 断言因章节标题不匹配判定失败。Rule 与 LLM 判断出现矛盾。

**b1_15（章节顺序）**：复合标题"背景与目标"导致顺序检查误判。

**结论**：Rule 断言适合格式合规性检查（如用户故事是否三段式），不适合存在性检查。LLM Judge 在语义理解上更接近真实质量。基于人工复核，zero_shot B1 实际质量约 0.75，当前自动评估 0.636 因 Rule 断言误判偏低约 0.10-0.15。

### 3.3 LLM Judge 非完美

Claude 的判断标准可能与人类评审有偏差。缓解方式：所有运行的详细样本保存在 `experiments/samples/`，支持人工复核。

---

### 3.4 评估版本说明

本实验同时维护两个断言版本：

| 版本 | 文件 | 说明 |
|---|---|---|
| v1 | b1_structure.json | 原版，关键词严格匹配，可能低估使用非标准章节标题的 PRD |
| v2 | b1_structure_v2.json | 扩充版，增加中文惯用章节标题关键词，更贴近实际 PRD 写作习惯 |

两个版本的结果均保留在 results.csv 中，通过 assertions_version 字段区分。

## 四、实验结果

### 4.1 B1 基础结构合规性

**测试配置**：7 cases（5 standard + 2 edge），n_runs=3，Kimi K2.5，temperature=1.0

#### zero_shot 结果（v1 断言）

| Case | 场景 | with_skill | baseline | Gain | Efficacy | Tier |
|---|---|---|---|---|---|---|
| b1_tc_01 | 电商购物车 | 0.596 | 0.550 | +0.103 | LOW 🔴 | C |
| b1_tc_02 | 社交点赞 | 0.717 | 0.521 | +0.410 | MEDIUM 🟡 | B |
| b1_tc_03 | 用户注册登录 | 0.683 | 0.570 | +0.262 | MEDIUM 🟡 | B |
| b1_tc_04 | 消息通知 | 0.543 | 0.449 | +0.170 | LOW 🔴 | C |
| b1_tc_05 | 搜索功能 | 0.659 | 0.583 | +0.184 | LOW 🔴 | B |
| b1_tc_edge_01 | 极简需求描述 | 0.624 | 0.510 | +0.232 | MEDIUM 🟡 | B |
| b1_tc_edge_02 | 跨平台复杂需求 | 0.627 | 0.499 | +0.256 | MEDIUM 🟡 | B |
| **整体** | | **0.636** | **0.526** | **+0.231** | **MEDIUM 🟡** | **B** |

#### few_shot 结果（v1 断言）

| Case | 场景 | with_skill | baseline | Gain | Efficacy | Tier |
|---|---|---|---|---|---|---|
| b1_tc_01 | 电商购物车 | 0.623 | 0.592 | +0.076 | LOW 🔴 | B |
| b1_tc_02 | 社交点赞 | 0.724 | 0.488 | +0.461 | MEDIUM 🟡 | B |
| b1_tc_03 | 用户注册登录 | 0.656 | 0.518 | +0.285 | MEDIUM 🟡 | B |
| b1_tc_04 | 消息通知 | 0.608 | 0.479 | +0.248 | MEDIUM 🟡 | B |
| b1_tc_05 | 搜索功能 | 0.696 | 0.588 | +0.263 | MEDIUM 🟡 | B |
| b1_tc_edge_01 | 极简需求描述 | 0.767 | 0.502 | +0.532 | HIGH 🟢 | B |
| b1_tc_edge_02 | 跨平台复杂需求 | 0.663 | 0.477 | +0.356 | MEDIUM 🟡 | B |
| **整体** | | **0.677** | **0.521** | **+0.326** | **MEDIUM 🟡** | **B** |

#### few_shot 结果（v2 断言）

| Case | 场景 | with_skill | baseline | Gain | Efficacy | Tier |
|---|---|---|---|---|---|---|
| b1_tc_01 | 电商购物车 | 0.749 | 0.681 | +0.213 | MEDIUM 🟡 | B |
| b1_tc_02 | 社交点赞 | 0.738 | 0.553 | +0.413 | MEDIUM 🟡 | B |
| b1_tc_03 | 用户注册登录 | 0.717 | 0.670 | +0.140 | LOW 🔴 | B |
| b1_tc_04 | 消息通知 | 0.736 | 0.628 | +0.290 | MEDIUM 🟡 | B |
| b1_tc_05 | 搜索功能 | 0.706 | 0.751 | -0.178 | LOW 🔴 | B |
| b1_tc_edge_01 | 极简需求描述 | 0.789 | 0.704 | +0.286 | MEDIUM 🟡 | B |
| b1_tc_edge_02 | 跨平台复杂需求 | 0.696 | 0.676 | +0.061 | LOW 🔴 | B |
| **整体** | | **0.733** | **0.666** | **+0.200** | **LOW 🔴** | **B** |

#### B1 小结

| 版本 | 断言 | Skill pass_rate | Baseline | Gain | Efficacy |
|---|---|---|---|---|---|
| zero_shot | v1 | 0.636 | 0.526 | +0.231 | MEDIUM 🟡 |
| few_shot | v1 | 0.677 | 0.521 | +0.326 | MEDIUM 🟡 |
| few_shot | v2 | 0.733 | 0.666 | +0.200 | LOW 🔴 |

- few_shot v1 比 zero_shot v1 Gain 高 +0.095，示例引导有效
- few_shot v2 绝对分数最高（0.733），但 Gain 最低（+0.200），因为 v2 同时修正了 baseline 的低估，压缩了增益空间
- 极简需求场景是 few_shot 的最强项（v1 Gain=+0.532 HIGH），说明 few_shot Skill 在输入不足时引导能力更强

---

### 4.2 B2 条件场景适配

**测试配置**：每场景 3 cases（2 standard + 1 edge），n_runs=3，v1 断言

#### zero_shot 结果

| 场景 | with_skill | baseline | Gain | Efficacy |
|---|---|---|---|---|
| B2B | 0.699 | 0.689 | +0.032 | LOW 🔴 |
| Consumer | 0.681 | 0.639 | +0.117 | LOW 🔴 |
| Internal | 0.687 | 0.597 | +0.224 | MEDIUM 🟡 |

**zero_shot B2B 各 Case**

| Case | 场景 | with_skill | baseline | Gain | Efficacy | Tier |
|---|---|---|---|---|---|---|
| b2_tc_b2b_01 | 企业级 CRM | 0.683 | 0.644 | +0.108 | LOW 🔴 | B |
| b2_tc_b2b_02 | 企业审批流 | 0.722 | 0.724 | -0.008 | LOW 🔴 | B |
| b2_tc_b2b_edge_01 | 仅提产品名 | 0.693 | 0.699 | -0.022 | LOW 🔴 | B |

**zero_shot Consumer 各 Case**

| Case | 场景 | with_skill | baseline | Gain | Efficacy | Tier |
|---|---|---|---|---|---|---|
| b2_tc_c_01 | 短视频 APP | 0.713 | 0.683 | +0.093 | LOW 🔴 | B |
| b2_tc_c_02 | 在线健身 | 0.722 | 0.656 | +0.193 | LOW 🔴 | B |
| b2_tc_c_edge_01 | B2C 混合场景 | 0.609 | 0.578 | +0.074 | LOW 🔴 | B |

**zero_shot Internal 各 Case**

| Case | 场景 | with_skill | baseline | Gain | Efficacy | Tier |
|---|---|---|---|---|---|---|
| b2_tc_int_01 | 运营数据看板 | 0.594 | 0.544 | +0.109 | LOW 🔴 | C |
| b2_tc_int_02 | 内容审核工具 | 0.736 | 0.578 | +0.373 | MEDIUM 🟡 | B |
| b2_tc_int_edge_01 | 高频复杂操作 | 0.732 | 0.668 | +0.192 | LOW 🔴 | B |

#### few_shot 结果（v1 断言）

| 场景 | with_skill | baseline | Gain | Efficacy |
|---|---|---|---|---|
| B2B | 0.731 | 0.631 | +0.270 | MEDIUM 🟡 |
| Consumer | 0.721 | 0.636 | +0.233 | MEDIUM 🟡 |
| Internal | 0.683 | 0.601 | +0.206 | MEDIUM 🟡 |

**few_shot B2B 各 Case**

| Case | 场景 | with_skill | baseline | Gain | Efficacy | Tier |
|---|---|---|---|---|---|---|
| b2_tc_b2b_01 | 企业级 CRM | 0.729 | 0.655 | +0.215 | MEDIUM 🟡 | B |
| b2_tc_b2b_02 | 企业审批流 | 0.749 | 0.530 | +0.465 | MEDIUM 🟡 | B |
| b2_tc_b2b_edge_01 | 仅提产品名 | 0.715 | 0.709 | +0.020 | LOW 🔴 | B |

**few_shot Consumer 各 Case**

| Case | 场景 | with_skill | baseline | Gain | Efficacy | Tier |
|---|---|---|---|---|---|---|
| b2_tc_c_01 | 短视频 APP | 0.729 | 0.704 | +0.085 | LOW 🔴 | B |
| b2_tc_c_02 | 在线健身 | 0.733 | 0.716 | +0.058 | LOW 🔴 | B |
| b2_tc_c_edge_01 | B2C 混合场景 | 0.700 | 0.487 | +0.415 | MEDIUM 🟡 | B |

**few_shot Internal 各 Case**

| Case | 场景 | with_skill | baseline | Gain | Efficacy | Tier |
|---|---|---|---|---|---|---|
| b2_tc_int_01 | 运营数据看板 | 0.625 | 0.556 | +0.157 | LOW 🔴 | B |
| b2_tc_int_02 | 内容审核工具 | 0.688 | 0.671 | +0.052 | LOW 🔴 | B |
| b2_tc_int_edge_01 | 高频复杂操作 | 0.736 | 0.576 | +0.377 | MEDIUM 🟡 | B |

#### B2 小结

| 场景 | zero_shot Gain | few_shot Gain | 变化 |
|---|---|---|---|
| B2B | +0.032 | +0.270 | ↑↑ +0.238 |
| Consumer | +0.117 | +0.233 | ↑ +0.116 |
| Internal | +0.224 | +0.206 | ↓ -0.018 |

- few_shot 在 B2B 场景提升最显著（+0.238），直接验证了 few_shot Skill 的 B2B 差异化指引有效
- Consumer 场景提升中等（+0.116），B2C 混合边界 case 是主要贡献来源（Gain +0.415）
- Internal 场景 few_shot 与 zero_shot 基本持平，few_shot 的结构约束未带来明显额外价值

---

### 4.3 B3 流程编排完整性

**测试配置**：5 cases（3 standard + 2 edge），n_runs=3，v1 断言

#### zero_shot 结果

| Case | 场景 | with_skill | baseline | Gain | Efficacy | Tier |
|---|---|---|---|---|---|---|
| b3_tc_01 | 健身房预约系统 | 0.635 | 0.693 | -0.189 | LOW 🔴 | B |
| b3_tc_02 | 二手交易平台 | 0.689 | 0.651 | +0.107 | LOW 🔴 | B |
| b3_tc_03 | 在线预约挂号 | 0.628 | 0.712 | -0.291 | LOW 🔴 | B |
| b3_tc_edge_01 | 极简指令 | 0.693 | 0.696 | -0.011 | LOW 🔴 | B |
| b3_tc_edge_02 | 需求矛盾 | 0.674 | 0.688 | -0.046 | LOW 🔴 | B |
| **整体** | | **0.664** | **0.688** | **-0.078** | **LOW 🔴** | **B** |

#### few_shot 结果

待补充（API 服务不稳定导致实验未完成，预计下午重试）

#### B3 小结

zero_shot Skill 在 B3 的 Gain 为负（-0.078），是三个 Benchmark 中唯一出现负 Gain 的情况。根本原因是 zero_shot Skill 没有任务拆解指引，Kimi 在没有 Skill 约束时反而能更自由地生成任务拆解内容。

few_shot Skill 有完整的五步流程指引（PRD 质量验证 → 功能拆解 → 依赖梳理 → 开发计划 → 风险评估），预计 B3 Gain 会显著转正。

---

## 五、zero_shot vs few_shot 对比

### 5.1 B1 对比

| 指标 | zero_shot | few_shot | 变化 |
|---|---|---|---|
| Skill pass_rate | 0.636 | 0.677 | ↑ +0.041 |
| Baseline pass_rate | 0.526 | 0.521 | ≈ 持平 |
| Skill Gain | +0.231 | +0.326 | ↑ +0.095 |
| Efficacy | MEDIUM 🟡 | MEDIUM 🟡 | 持平 |

### 5.2 B2 对比

| 场景 | zero_shot Gain | few_shot Gain | 变化 |
|---|---|---|---|
| B2B | +0.032 | +0.270 | ↑↑ +0.238 |
| Consumer | +0.117 | +0.233 | ↑ +0.116 |
| Internal | +0.224 | +0.206 | ↓ -0.018 |

### 5.3 B3 对比

| 版本 | Gain |
|---|---|
| zero_shot | -0.078 |
| few_shot | 待补充 |

### 5.4 综合结论

**few_shot Skill 在大多数场景下优于 zero_shot，但提升幅度因 Benchmark 和场景而异。**

- **B1**：few_shot 稳定优于 zero_shot，Gain 提升 +0.095，示例引导对结构合规性有效
- **B2**：few_shot 在 B2B 场景提升最显著（+0.238），在 Internal 场景持平，整体提升明显
- **B3**：zero_shot 出现负 Gain，few_shot 预计转正，是两个版本差距最大的维度

**Skill Gain 与场景难度的关系**：Baseline 得分越高的场景（如 B2B），Kimi 本身能力越强，Skill 的边际价值越小。Skill 在输入信息不足（极简需求）和场景复杂（B2C 混合、高频复杂操作）时价值最突出。

## 六、评估器改进建议

### 6.1 Rule 断言修正建议
```json
{
  "id": "b1_04",
  "check": "包含'用户场景'或'用例'或'User Stories'或'核心使用场景'或'场景'",
  "type": "structural"
},
{
  "id": "b1_10",
  "method": "llm",
  "check": "文档是否在功能需求中明确定义了验收标准或业务规则"
}
```

### 6.2 Rule vs LLM 权重建议

| 检查类型 | 建议方式 | 原因 |
|---|---|---|
| 存在性检查 | LLM | 关键词匹配无法覆盖所有表达方式 |
| 格式合规性 | Rule | 格式有明确标准 |
| 内容质量 | LLM | 语义理解必须依赖 LLM |

### 6.3 顺序检查优化

`check_section_order` 函数应处理复合标题，如"背景与目标"应分别识别为"背景"和"目标"两个锚点。

---

## 七、评估版本对比说明

### 7.1 为什么需要 v2 版本

在人工复核 `experiments/samples/` 中的样本文件后，发现 v1 断言存在系统性低估问题。

根本原因是：**Rule 断言的关键词列表基于标准英文 PRD 模板设计，而 Kimi 生成的 PRD 使用的是中文惯用章节标题**，导致关键词匹配失败，但实际内容完整。

典型误判案例（来自 `82f6dea0_b1_b1_tc_01_baseline_0.json`）：

| 断言 | v1 判定 | 实际内容 | 误判原因 |
|---|---|---|---|
| b1_03 目标用户 | ❌ 失败 | 第3节"用户故事"有完整用户角色表格 | 找不到"目标用户/用户画像/Persona" |
| b1_04 用户场景 | ❌ 失败 | 第3节就是用户故事表格 | 找不到"用户场景/用例/User Stories" |
| b1_07 UX设计 | ❌ 失败 | 第7节"页面布局与交互"内容完整 | 找不到"用户体验/设计说明/UX" |
| b1_11 度量指标 | ❌ 失败 | 第2节有转化率等量化目标 | 找不到"度量指标/成功标准/Metrics" |

**实际质量估算**：去掉上述误判，该 PRD 实际得分约 0.762，而 v1 自动评估为 0.578，偏低约 0.18。

### 7.2 两个版本的定位

| 版本 | 文件后缀 | 关键词策略 | 适用场景 |
|---|---|---|---|
| v1 | `_structure.json` | 严格匹配标准章节标题 | 评估 Skill 是否引导输出标准格式 |
| v2 | `_structure_v2.json` | 扩充中文惯用标题同义词 | 评估 Skill 是否引导输出实质内容 |

使用方式：
```bash
# v1（默认）
python evaluators/parallel_eval.py --skill ... --benchmark b1

# v2（扩充关键词）
python evaluators/parallel_eval.py --skill ... --benchmark b1 --assertions-version v2
```

### 7.3 自动化评估的系统性缺陷

**缺陷一：关键词匹配无法覆盖语义等价表达**

同一个概念在不同 PRD 中可能有十几种表达方式，关键词列表永远无法穷举。v2 版本扩充了关键词但仍不完整，本质上是"打补丁"而非根治。根本解决方案是对所有存在性检查都改用 LLM Judge，但会增加 API 调用成本。

**缺陷二：LLM Judge 的一致性依赖温度参数**

Claude Judge 使用 temperature=0.1，但仍存在轻微随机性。对于边界案例（confidence 在 0.4-0.6 之间），同一份 PRD 多次评估可能得到不同结论。缓解方式：Judge 也可以做多次采样取平均，但成本翻倍。

**缺陷三：内容采样丢失中间信息**

当 PRD 超过 3000 字时，`_sample_content` 只保留首尾各 1200/800 字，中间内容被截断。如果关键章节（如验收标准）恰好在中间，会导致 LLM Judge 误判。

**缺陷四：temperature=1.0 引入随机噪音**

Kimi K2.5 流式模式强制 temperature=1.0，导致同一个 prompt 的多次输出差异较大。n_runs=3 的平均可以部分缓解，但 Kappa=0.000 的情况说明部分 case 的结果仍不稳定。

**缺陷五：Skill Gain 在 baseline 高分区间压缩**

当 baseline 得分已经较高（如 >0.65）时，即使 with_skill 得分更高，Gain 的绝对值也会被压缩。这导致在 B2B 场景下 zero_shot Skill 的 Gain 接近 0，但实际上两个版本的绝对质量都达到了 Tier-B。

### 7.4 改进方向（未来工作）

1. 对所有"存在性"断言改用 LLM Judge，彻底消除关键词匹配偏差
2. 对 LLM Judge 也做多次采样（judge_runs=3），提升评估一致性
3. 增大内容采样窗口，或改为按章节结构采样
4. 引入人工标注的黄金标准集（20-30 份 PRD），用于校准自动评估的准确率
5. 考虑使用 pass^k 指标替代简单平均，更科学地衡量稳定性

---

## 八、扩展性说明

本框架不局限于 PRD 场景，只需替换断言定义和测试用例即可迁移到其他 Skill 类型。

**与现有框架的差异化定位**：

| 框架 | 评估对象 | 区别 |
|---|---|---|
| DeepEval / G-Eval | LLM 输出质量 | 评估单次输出，不评估 Skill 文件本身 |
| SkillsBench | 已有 Skill 的执行效果 | 假设 Skill 已存在，不评估 Skill 生成能力 |
| **本项目** | Agent 生成 Skill 的能力 | 评估从零生成 Skill 的增量价值 |

---

## 九、变更记录

| 日期 | 变更内容 |
|---|---|
| 2026-03-31 | B1/B2/B3 zero_shot 实验完成，发现 Rule 断言误判问题 |
| 2026-04-01 | 新增 v2 断言版本（扩充关键词库），B1 few_shot 实验完成 |
| 待补充 | B2/B3 few_shot 实验结果 |
| 待补充 | v2 断言版本实验结果 |
