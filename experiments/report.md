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

## 结论（待填写）
