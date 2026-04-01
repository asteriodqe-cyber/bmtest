# B2 条件场景适配 — few_shot 实验记录

**Skill 版本**：few_shot/skill_v1.md  
**生成方式**：Kimi K2.5 思考模式，参考 baseline + prd-taskmaster  
**实验日期**：2026-04-01  
**配置**：n_runs=3，temperature=1.0，Concurrency=3，Judge=Claude Sonnet 4.6

---

## 整体结果汇总（v1 断言）

| 场景 | Skill pass_rate | Baseline pass_rate | Skill Gain | Efficacy | 状态 |
|---|---|---|---|---|---|
| B2B | 0.731 | 0.631 | +0.270 | MEDIUM 🟡 | ✅ Meets Floor |
| Consumer | 0.721 | 0.636 | +0.233 | MEDIUM 🟡 | ✅ Meets Floor |
| Internal | 0.683 | 0.601 | +0.206 | MEDIUM 🟡 | ✅ Meets Floor |

---

## B2B 场景详细结果

**耗时**：826.2s（13.8min）

| Case | 类型 | with_skill | baseline | Gain | Efficacy | Tier |
|---|---|---|---|---|---|---|
| b2_tc_b2b_01 企业级 CRM | standard | 0.729 | 0.655 | +0.215 | MEDIUM 🟡 | B |
| b2_tc_b2b_02 企业审批流 | standard | 0.749 | 0.530 | +0.465 | MEDIUM 🟡 | B |
| b2_tc_b2b_edge_01 仅提产品名 | edge | 0.715 | 0.709 | +0.020 | LOW 🔴 | B |
| **整体** | | **0.731** | **0.631** | **+0.270** | **MEDIUM 🟡** | **B** |

### B2B 一致性分析

| Case | skill_consistency | skill_kappa | baseline_consistency | baseline_kappa |
|---|---|---|---|---|
| b2_tc_b2b_01 | 0.984 | 1.000 | 0.842 | 0.000 |
| b2_tc_b2b_02 | 0.992 | 1.000 | 0.593 | 0.000 |
| b2_tc_b2b_edge_01 | 0.987 | 1.000 | 0.958 | 1.000 |

---

## Consumer 场景详细结果

**耗时**：775.6s（12.9min）

| Case | 类型 | with_skill | baseline | Gain | Efficacy | Tier |
|---|---|---|---|---|---|---|
| b2_tc_c_01 短视频 APP | standard | 0.729 | 0.704 | +0.085 | LOW 🔴 | B |
| b2_tc_c_02 在线健身 | standard | 0.733 | 0.716 | +0.058 | LOW 🔴 | B |
| b2_tc_c_edge_01 B2C 混合场景 | edge | 0.700 | 0.487 | +0.415 | MEDIUM 🟡 | B |
| **整体** | | **0.721** | **0.636** | **+0.233** | **MEDIUM 🟡** | **B** |

### Consumer 一致性分析

| Case | skill_consistency | skill_kappa | baseline_consistency | baseline_kappa |
|---|---|---|---|---|
| b2_tc_c_01 | 0.977 | 1.000 | 0.966 | 1.000 |
| b2_tc_c_02 | 0.982 | 1.000 | 0.989 | 1.000 |
| b2_tc_c_edge_01 | 0.978 | 1.000 | 0.849 | 1.000 |

---

## Internal 场景详细结果

**耗时**：795.5s（13.3min）

| Case | 类型 | with_skill | baseline | Gain | Efficacy | Tier |
|---|---|---|---|---|---|---|
| b2_tc_int_01 运营数据看板 | standard | 0.625 | 0.556 | +0.157 | LOW 🔴 | B |
| b2_tc_int_02 内容审核工具 | standard | 0.688 | 0.671 | +0.052 | LOW 🔴 | B |
| b2_tc_int_edge_01 高频复杂操作 | edge | 0.736 | 0.576 | +0.377 | MEDIUM 🟡 | B |
| **整体** | | **0.683** | **0.601** | **+0.206** | **MEDIUM 🟡** | **B** |

### Internal 一致性分析

| Case | skill_consistency | skill_kappa | baseline_consistency | baseline_kappa |
|---|---|---|---|---|
| b2_tc_int_01 | 0.824 | 0.000 | 0.978 | 1.000 |
| b2_tc_int_02 | 0.816 | 0.000 | 0.864 | 0.000 |
| b2_tc_int_edge_01 | 0.992 | 1.000 | 0.977 | 1.000 |

---

## zero_shot vs few_shot 跨场景对比（v1 断言）

| 场景 | zero_shot Gain | few_shot Gain | 变化 |
|---|---|---|---|
| B2B | +0.032 | +0.270 | ↑↑ +0.238 |
| Consumer | +0.117 | +0.233 | ↑ +0.116 |
| Internal | +0.224 | +0.206 | ↓ -0.018 |

---

## 关键洞察

**最重要发现：few_shot 在 B2B 场景 Gain 提升最显著（+0.238）**

zero_shot 在 B2B 的 Gain 只有 +0.032（几乎没有增量），而 few_shot 达到 +0.270（MEDIUM）。这直接验证了我们的预测——few_shot Skill 有专门的 B2B 差异化指引（权限体系、RBAC、多租户），在 B2B 场景下效果明显更好。

**Consumer 场景提升中等（+0.116）**

few_shot 在 Consumer 的 Gain 从 +0.117 提升到 +0.233，提升幅度与 B1 相当，说明 few_shot Skill 的 C 端适配指引有一定效果。

**Internal 场景 few_shot 略低于 zero_shot（-0.018）**

few_shot Internal Gain 为 +0.206，zero_shot 为 +0.224，基本持平但略有下降。可能原因是 few_shot Skill 的结构约束更强，在内部工具这种需要灵活表达的场景下反而产生了轻微干扰。

**边界 case 是 Gain 的主要来源**

三个场景中，Gain 最高的都是边界 case：B2B 边界（+0.020 反常低）、Consumer B2C 混合（+0.415）、Internal 高频复杂（+0.377）。说明 Skill 在复杂场景下的引导价值更突出，但 B2B 边界是例外。

**B2B 边界 case 的异常**

B2B 边界（仅提产品名）Gain 只有 +0.020，因为 baseline 已高达 0.709，Kimi 本身在 B2B 场景有很强的内置知识，Skill 的边际价值极小。
