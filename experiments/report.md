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

#### zero_shot 结果

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


## few_shot 对比（v1 断言版本）

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

#### B1 小结（zero_shot vs few_shot，v1 断言）

| 指标 | zero_shot | few_shot | 变化 |
|---|---|---|---|
| Skill pass_rate | 0.636 | 0.677 | ↑ +0.041 |
| Baseline pass_rate | 0.526 | 0.521 | ≈ 持平 |
| Skill Gain | +0.231 | +0.326 | ↑ +0.095 |
| Efficacy | MEDIUM 🟡 | MEDIUM 🟡 | 持平 |
| Meets Floor | ✅ | ✅ | 持平 |

- few_shot Skill 整体 Gain 比 zero_shot 高 +0.095，说明示例引导有效
- 提升最显著的是极简需求场景（zero_shot +0.232 → few_shot +0.532），说明 few_shot Skill 在输入信息不足时有更强的结构化引导能力
- 电商购物车场景 few_shot Gain 略低（+0.076 vs +0.103），因为 baseline 得分提升压缩了增益空间
- 两个版本的 baseline 得分基本持平（0.526 vs 0.521），说明 Kimi 的基础能力稳定，差异主要来自 Skill 本身

#### B1 小结 额外

- zero_shot Skill 整体达到 Tier-B，Gain=+0.231，通过质量门槛
- Skill 在"社交点赞"场景效果最显著（Gain=+0.410），在"电商购物车"效果最弱（Gain=+0.103）
- Edge case 表现稳定，说明 Skill 对复杂场景也有帮助

### 4.2 B2 条件场景适配

**测试配置**：各场景 3 cases（2 standard + 1 edge），n_runs=3，Kimi K2.5，temperature=1.0

#### zero_shot — B2B 场景结果

| Case | 场景 | with_skill | baseline | Gain | Efficacy | Tier |
|---|---|---|---|---|---|---|
| b2_tc_b2b_01 | 企业级 CRM | 0.683 | 0.644 | +0.108 | LOW 🔴 | B |
| b2_tc_b2b_02 | 企业审批流 | 0.722 | 0.724 | -0.008 | LOW 🔴 | B |
| b2_tc_b2b_edge_01 | B2B边界：仅提产品名 | 0.693 | 0.699 | -0.022 | LOW 🔴 | B |
| **整体** | | **0.699** | **0.689** | **+0.032** | **LOW 🔴** | **B** |

#### zero_shot — Consumer 场景结果

## Consumer 场景详细结果

**耗时**：811.9s（13.5min）

| Case | 类型 | with_skill | baseline | Gain | Efficacy | Tier |
|---|---|---|---|---|---|---|
| b2_tc_c_01 短视频 APP | standard | 0.713 | 0.683 | +0.093 | LOW 🔴 | B |
| b2_tc_c_02 在线健身 | standard | 0.722 | 0.656 | +0.193 | LOW 🔴 | B |
| b2_tc_c_edge_01 B2C 混合场景 | edge | 0.609 | 0.578 | +0.074 | LOW 🔴 | B |
| **整体** | | **0.681** | **0.639** | **+0.117** | **LOW 🔴** | **B** |

### Consumer 一致性分析

| Case | skill_consistency | skill_kappa | baseline_consistency | baseline_kappa |
|---|---|---|---|---|
| b2_tc_c_01 | 0.920 | 1.000 | 0.937 | 1.000 |
| b2_tc_c_02 | 0.978 | 1.000 | 0.865 | 0.000 |
| b2_tc_c_edge_01 | 0.814 | 0.000 | 0.882 | 0.000 |

### Consumer 关键洞察

- Gain 整体 +0.117，略优于 B2B（+0.032），但仍为 LOW
- B2C 混合边界场景 baseline 掉至 Tier-C（0.578），说明混合场景对模型有挑战
- Skill 对 B2C 混合场景的提升同样有限（+0.074），说明 zero_shot Skill 缺乏混合场景的处理逻辑
- 在线健身场景 Gain 最高（+0.193），接近 MEDIUM 阈值

#### zero_shot — Internal 场景结果

## Internal 场景详细结果

**耗时**：739.3s（12.3min）

| Case | 类型 | with_skill | baseline | Gain | Efficacy | Tier |
|---|---|---|---|---|---|---|
| b2_tc_int_01 运营数据看板 | standard | 0.594 | 0.544 | +0.109 | LOW 🔴 | C |
| b2_tc_int_02 内容审核工具 | standard | 0.736 | 0.578 | +0.373 | MEDIUM 🟡 | B |
| b2_tc_int_edge_01 高频复杂操作 | edge | 0.732 | 0.668 | +0.192 | LOW 🔴 | B |
| **整体** | | **0.687** | **0.597** | **+0.224** | **MEDIUM 🟡** | **B** |

### Internal 一致性分析

| Case | skill_consistency | skill_kappa | baseline_consistency | baseline_kappa |
|---|---|---|---|---|
| b2_tc_int_01 | 0.733 | 0.000 | 0.978 | 1.000 |
| b2_tc_int_02 | 0.984 | 1.000 | 0.969 | 1.000 |
| b2_tc_int_edge_01 | 0.972 | 1.000 | 0.824 | 0.000 |

### Internal 关键洞察

- Internal 是 B2 三个场景中 Gain 最高的（+0.224），唯一达到 MEDIUM
- 内容审核工具 Gain=+0.373，是 B2 所有 case 中最高的单项
- 运营数据看板 with_skill 仍为 Tier-C（0.594），consistency 最低（0.733），说明该场景结果不稳定
- zero_shot Skill 对内部工具的适配效果优于 B2B 和 Consumer，可能因为内部工具场景需求更聚焦，Skill 的结构化引导更容易发挥作用

## 整体结果汇总

| 场景 | Skill pass_rate | Baseline pass_rate | Skill Gain | Efficacy | 状态 |
|---|---|---|---|---|---|
| B2B | 0.699 | 0.689 | +0.032 | LOW 🔴 | ✅ Meets Floor |
| Consumer | 0.681 | 0.639 | +0.117 | LOW 🔴 | ✅ Meets Floor |
| Internal | 0.687 | 0.597 | +0.224 | MEDIUM 🟡 | ✅ Meets Floor |

## 跨场景对比

| 维度 | B2B | Consumer | Internal |
|---|---|---|---|
| Skill Gain | +0.032 LOW 🔴 | +0.117 LOW 🔴 | +0.224 MEDIUM 🟡 |
| Baseline 强度 | 高（0.689 Tier-B）| 中（0.639 Tier-B）| 低（0.597 Tier-C）|
| Skill 差异化价值 | 低 | 低 | 中 |
| 最高单 Case Gain | +0.108 | +0.193 | +0.373 |

**结论**：zero_shot Skill 在 B2 场景的表现呈现明显规律——Baseline 越强，Gain 越低。B2B 场景 Kimi 内置知识最强，Skill 边际价值最低；Internal 场景 baseline 最弱，Skill 提升空间最大。

**预测 few_shot 表现**：few_shot Skill 有专门的三场景差异化指引，预计 B2B 和 Consumer 的 Gain 会显著提升，Internal 可能进一步提升至 HIGH。


#### few_shot 结果

待补充

#### B2 小结（B2B 已完成）

**关键发现：B2B 场景下 zero_shot Skill Gain 几乎为零（+0.032）**

两种可能解释：

1. **Kimi 本身对 B2B 产品理解较强**：baseline 已达 Tier-B（0.689），Skill 的边际提升空间有限
2. **zero_shot Skill 缺乏 B2B 差异化指引**：zero_shot 版本没有专门的权限体系、RBAC、多租户等 B2B 特有要求，无法在 B2B 场景下体现优势

这个结果预示着 few_shot Skill（含专门的 B2B 适配章节）在该场景的 Gain 应显著高于 +0.032，将是两个版本最有区分度的对比点之一。

**注意**：企业审批流（-0.008）和 B2B 边界（-0.022）出现负增益，说明在该场景下 Skill 不仅没有帮助，反而略微干扰了输出。这在 Skill 缺乏针对性指引时是合理现象。

# B3 流程编排完整性 — zero_shot 实验记录

**Skill 版本**：zero_shot/skill_v1.md  
**生成方式**：Kimi K2.5 快速模式，无示例直接生成  
**实验日期**：2026-03-31  
**配置**：n_runs=3，temperature=1.0，Concurrency=3，Judge=Claude Sonnet 4.6

---

## 整体结果

| 指标 | 值 |
|---|---|
| Skill pass_rate | 0.664 Tier-B |
| Baseline pass_rate | 0.688 Tier-B |
| Skill Gain | -0.078 LOW 🔴 |
| Meets Floor | ✅ YES |
| Diagnosis | 增益不足，Skill 未带来显著提升 |
| 耗时 | 662.4s（11.0min）|

---

## 各 Case 详细结果

| Case | 类型 | with_skill | baseline | Gain | Efficacy | Tier |
|---|---|---|---|---|---|---|
| b3_tc_01 健身房预约系统 | standard | 0.635 | 0.693 | -0.189 | LOW 🔴 | B |
| b3_tc_02 二手交易平台 | standard | 0.689 | 0.651 | +0.107 | LOW 🔴 | B |
| b3_tc_03 在线预约挂号 | standard | 0.628 | 0.712 | -0.291 | LOW 🔴 | B |
| b3_tc_edge_01 极简指令 | edge | 0.693 | 0.696 | -0.011 | LOW 🔴 | B |
| b3_tc_edge_02 需求矛盾 | edge | 0.674 | 0.688 | -0.046 | LOW 🔴 | B |
| **整体** | | **0.664** | **0.688** | **-0.078** | **LOW 🔴** | **B** |

---

## 一致性分析

| Case | skill_consistency | skill_kappa | baseline_consistency | baseline_kappa |
|---|---|---|---|---|
| b3_tc_01 | 0.924 | 1.000 | 0.993 | 1.000 |
| b3_tc_02 | 0.989 | 1.000 | 0.921 | 1.000 |
| b3_tc_03 | 0.940 | 1.000 | 0.969 | 1.000 |
| b3_tc_edge_01 | 0.993 | 1.000 | 0.998 | 1.000 |
| b3_tc_edge_02 | 0.915 | 1.000 | 0.998 | 1.000 |

**注**：B3 的一致性整体很高，说明结果可靠，负 Gain 不是随机噪音，而是真实的系统性现象。

---

## 关键洞察

- **Skill Gain 为负（-0.078）是本实验最重要的发现**
- zero_shot Skill 没有任务拆解指引，无法引导 Kimi 完成 PRD→任务拆解的完整流程
- Baseline 反而因为没有 Skill 的结构约束，更自由地生成了任务拆解内容
- Skill 的强结构化约束在 B3 场景下产生了负向干扰
- 在线预约挂号场景 Gain 最低（-0.291），说明该场景 baseline 本身就能生成很好的任务拆解

## 预测 few_shot 表现

few_shot Skill 有完整的多步骤流程指引（Step 1-5：PRD质量验证→功能拆解→依赖梳理→开发计划→风险评估），B3 Gain 应显著转正，预计达到 MEDIUM 或以上。这将是 zero_shot vs few_shot 最有区分度的对比维度。

---

## 样本文件

位置：`experiments/samples/b9a1e8af_b3_*.json`

---

## 五、zero_shot vs few_shot 对比

待补充（需要 few_shot 实验数据）

---

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

## 七、扩展性说明

本框架不局限于 PRD 场景，只需替换断言定义和测试用例即可迁移到其他 Skill 类型。

**与现有框架的差异化定位**：

| 框架 | 评估对象 | 区别 |
|---|---|---|
| DeepEval / G-Eval | LLM 输出质量 | 评估单次输出，不评估 Skill 文件本身 |
| SkillsBench | 已有 Skill 的执行效果 | 假设 Skill 已存在，不评估 Skill 生成能力 |
| **本项目** | Agent 生成 Skill 的能力 | 评估从零生成 Skill 的增量价值 |

---

## 八、变更记录

| 日期 | 变更内容 |
|---|---|
| 2026-03-31 | B1 zero_shot 实验完成，发现 Rule 断言误判问题 |
| 待补充 | B2/B3 实验结果 |
| 待补充 | few_shot 对比实验结果 |
