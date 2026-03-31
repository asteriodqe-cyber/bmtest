from __future__ import annotations

import csv
import warnings
from pathlib import Path
from statistics import mean, stdev
from typing import TypedDict

try:
    from filelock import FileLock
    HAS_FILELOCK = True
except ImportError:
    HAS_FILELOCK = False


# ── 质量下限配置 ──────────────────────────────────────────

QUALITY_FLOOR = {
    "b1": 0.60,  # 基础结构，要求较高
    "b2": 0.55,  # 条件适配，允许略低
    "b3": 0.55   # 流程编排，允许略低（任务更复杂）
}


# ── 类型定义 ──────────────────────────────────────────────

class MetricsResult(TypedDict):
    pass_rate: float
    consistency: float
    final_score: float


class GainResult(TypedDict):
    skill_pass_rate: float
    skill_consistency: float
    skill_final_score: float
    baseline_pass_rate: float
    baseline_consistency: float
    baseline_final_score: float
    gain: float
    efficacy: str
    absolute_tier: str
    meets_quality_floor: bool
    quality_floor: float
    diagnosis: str


# ── CSV 字段定义（单一来源）──────────────────────────────

CSV_FIELDNAMES = [
    "timestamp", "benchmark_id", "scenario", "test_case",
    "skill_path", "skill_hash", "condition",
    "provider", "model", "n_runs",
    "pass_rate", "consistency", "final_score", "kappa",
    "gain", "efficacy",
    "absolute_tier", "meets_quality_floor", "quality_floor",
    "diagnosis"
]


# ── 核心指标计算 ──────────────────────────────────────────

def calculate_metrics(results: list[float]) -> MetricsResult:
    """
    计算单组运行结果的核心指标

    Notes:
        - len < 2 时不调用 stdev（会抛 StatisticsError）
        - pass_rate 为 0.0 或 1.0 时 consistency 直接设为 1.0
        - final_score = 0.6 * pass_rate + 0.4 * consistency
    """
    if not results:
        return MetricsResult(pass_rate=0.0, consistency=0.0, final_score=0.0)

    pass_rate = mean(results)

    if len(results) < 2 or pass_rate in (0.0, 1.0):
        consistency = 1.0
    else:
        raw_std = stdev(results)
        normalized_std = raw_std / 0.5
        consistency = max(0.0, 1.0 - normalized_std)

    final_score = round(0.6 * pass_rate + 0.4 * consistency, 4)

    return MetricsResult(
        pass_rate=round(pass_rate, 4),
        consistency=round(consistency, 4),
        final_score=final_score
    )


# ── 绝对质量评估 ──────────────────────────────────────────

def _get_absolute_tier(score: float) -> str:
    """
    绝对质量分级

    A (≥0.8): 可直接用于开发，无需修改
    B (0.6-0.79): 需产品经理微调，框架完整
    C (0.4-0.59): 结构合规但内容空洞，需重写
    D (<0.4): 基本不可用
    """
    if score >= 0.8:
        return "A"
    if score >= 0.6:
        return "B"
    if score >= 0.4:
        return "C"
    return "D"


def _calculate_efficacy(
    gain: float,
    skill_score: float
) -> str:
    """
    二维 efficacy 判定：同时考虑绝对质量和相对增益

    硬底线：skill_score < 0.5 直接判 low，无论 gain 多高
    high：高增益（>0.5）且绝对质量达 B 级（≥0.6）
    medium：中等增益（>0.2）且绝对质量达 C 级（≥0.5）
    low：其他情况
    """
    if skill_score < 0.5:
        return "low"
    if gain > 0.5 and skill_score >= 0.6:
        return "high"
    if gain > 0.2 and skill_score >= 0.5:
        return "medium"
    return "low"


def _generate_diagnosis(
    gain: float,
    tier: str,
    meets_floor: bool,
    skill_score: float
) -> str:
    """
    生成一句话诊断，帮助用户快速定位问题

    四种典型情况：
    1. 绝对质量不足
    2. 增益不足（Skill 无效）
    3. 高增益但低绝对质量（矛盾场景：Skill 框架对但内容浅）
    4. 正常
    """
    if not meets_floor:
        return f"绝对质量不足（{tier}级，需提升至B级以上，当前={skill_score:.2f}）"
    if gain < 0.2:
        return f"增益不足（Gain={gain:.3f}），Skill 未带来显著提升"
    if tier == "C" and gain > 0.5:
        return "高增益但绝对质量低：Skill 框架正确但 instructions 内容深度不足，建议优化"
    return "正常"


# ── Skill Gain 计算 ───────────────────────────────────────

def calculate_skill_gain(
    skill_scores: list[float],
    baseline_scores: list[float],
    benchmark_id: str = "b1"
) -> GainResult:
    """
    计算 Skill Gain：有 Skill 相比无 Skill 的增量价值

    公式：Gain = (skill_score - baseline_score) / (1 - baseline_score)

    新增二维评估：
    - absolute_tier: 绝对质量分级（A/B/C/D）
    - meets_quality_floor: 是否达到质量下限
    - diagnosis: 一句话诊断

    Args:
        skill_scores:    with_skill 条件的得分列表
        baseline_scores: baseline 条件的得分列表
        benchmark_id:    用于查询 QUALITY_FLOOR（默认 b1）
    """
    skill_metrics = calculate_metrics(skill_scores)
    baseline_metrics = calculate_metrics(baseline_scores)

    skill_score = skill_metrics["pass_rate"]
    baseline_score = baseline_metrics["pass_rate"]

    if baseline_score >= 1.0:
        gain = 0.0
    else:
        gain = (skill_score - baseline_score) / (1.0 - baseline_score)

    gain = round(gain, 4)

    floor = QUALITY_FLOOR.get(benchmark_id, 0.5)
    absolute_tier = _get_absolute_tier(skill_score)
    meets_floor = skill_score >= floor
    efficacy = _calculate_efficacy(gain, skill_score)
    diagnosis = _generate_diagnosis(gain, absolute_tier, meets_floor, skill_score)

    return GainResult(
        skill_pass_rate=skill_score,
        skill_consistency=skill_metrics["consistency"],
        skill_final_score=skill_metrics["final_score"],
        baseline_pass_rate=baseline_score,
        baseline_consistency=baseline_metrics["consistency"],
        baseline_final_score=baseline_metrics["final_score"],
        gain=gain,
        efficacy=efficacy,
        absolute_tier=absolute_tier,
        meets_quality_floor=meets_floor,
        quality_floor=floor,
        diagnosis=diagnosis
    )


# ── Cohen's Kappa ─────────────────────────────────────────

def calculate_cohens_kappa(
    scores: list[float],
    threshold: float = 0.6
) -> float:
    """
    标准 Cohen's Kappa（二分类，O(n) 优化版）

    公式：Kappa = (P_o - P_e) / (1 - P_e)
    复杂度：O(n)，适用于任意规模
    """
    if len(scores) < 2:
        return 1.0

    n = len(scores)
    n_pass = sum(1 for s in scores if s >= threshold)
    n_fail = n - n_pass

    if n_pass == 0 or n_fail == 0:
        return 1.0

    total_pairs = n * (n - 1) / 2
    pairs_pass = n_pass * (n_pass - 1) / 2
    pairs_fail = n_fail * (n_fail - 1) / 2

    p_o = (pairs_pass + pairs_fail) / total_pairs
    p_pass = n_pass / n
    p_e = p_pass ** 2 + (1.0 - p_pass) ** 2

    if p_e >= 1.0:
        return 1.0

    kappa = (p_o - p_e) / (1.0 - p_e)
    return round(max(0.0, kappa), 4)


# ── CSV 写入 ──────────────────────────────────────────────

def save_to_csv(
    results: list[dict],
    output_path: str = "experiments/results.csv"
) -> None:
    """
    进程安全的 CSV 写入

    - CSV_FIELDNAMES 单一来源，parallel_eval 共用
    - FileLock(timeout=30) 防并发写入和死锁
    - f.tell()==0 判断是否写 header
    - 大规模测试（>10k行）建议改用 sqlite
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    def _write(f) -> None:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
        if f.tell() == 0:
            writer.writeheader()
        for row in results:
            writer.writerow({k: row.get(k, "") for k in CSV_FIELDNAMES})

    if HAS_FILELOCK:
        lock_path = output_path + ".lock"
        with FileLock(lock_path, timeout=30):
            with open(output_path, "a", newline="", encoding="utf-8") as f:
                _write(f)
    else:
        warnings.warn(
            "filelock not installed — CSV writing is not process-safe. "
            "Install with: pip install filelock",
            stacklevel=2
        )
        with open(output_path, "a", newline="", encoding="utf-8") as f:
            _write(f)
