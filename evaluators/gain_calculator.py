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


# ── CSV 字段定义（单一来源，parallel_eval 和 save_to_csv 共用）──

CSV_FIELDNAMES = [
    "timestamp", "benchmark_id", "scenario", "test_case",
    "skill_path", "skill_hash", "condition",
    "provider", "model", "n_runs",
    "pass_rate", "consistency", "final_score", "kappa",
    "gain", "efficacy"
]


# ── 核心指标计算 ──────────────────────────────────────────

def calculate_metrics(results: list[float]) -> MetricsResult:
    """
    计算单组运行结果的核心指标

    Args:
        results: 每次运行的归一化得分列表（0-1 之间）

    Returns:
        MetricsResult: pass_rate, consistency, final_score

    Notes:
        - len < 2 时不调用 stdev（会抛 StatisticsError）
        - pass_rate 为 0.0 或 1.0 时 std=0，consistency 直接设为 1.0
        - consistency 归一化基于二元结果最大 std=0.5
        - final_score = 0.6 * pass_rate + 0.4 * consistency（能力主导）
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


def calculate_skill_gain(
    skill_scores: list[float],
    baseline_scores: list[float]
) -> GainResult:
    """
    计算 Skill Gain：有 Skill 相比无 Skill 的增量价值

    公式：Gain = (skill_score - baseline_score) / (1 - baseline_score)

    当 baseline_score >= 1.0 时 gain=0（无提升空间）
    gain > 0.5 → high，> 0.2 → medium，其他 → low
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

    if gain > 0.5:
        efficacy = "high"
    elif gain > 0.2:
        efficacy = "medium"
    else:
        efficacy = "low"

    return GainResult(
        skill_pass_rate=skill_score,
        skill_consistency=skill_metrics["consistency"],
        skill_final_score=skill_metrics["final_score"],
        baseline_pass_rate=baseline_score,
        baseline_consistency=baseline_metrics["consistency"],
        baseline_final_score=baseline_metrics["final_score"],
        gain=gain,
        efficacy=efficacy
    )


def calculate_cohens_kappa(
    scores: list[float],
    threshold: float = 0.6
) -> float:
    """
    标准 Cohen's Kappa（二分类，O(n) 优化版）

    将连续分数转为二元（pass/fail），利用组合数学计算
    多次运行之间的分类一致性，无需两两枚举。

    公式：Kappa = (P_o - P_e) / (1 - P_e)
    - P_o = (C(n_pass,2) + C(n_fail,2)) / C(n,2)  观察一致率
    - P_e = p_pass² + p_fail²                       期望一致率

    复杂度：O(n)，适用于任意规模（包括 n_runs=1000+ 的大规模测试）

    与 consistency 的区别：
    - consistency：基于方差的连续值稳定性指标
    - kappa：基于分类一致率的统计指标，更严格，有标准统计学解释

    Args:
        scores:    每次运行的归一化得分列表
        threshold: 通过/失败的分界线，默认 0.6

    Returns:
        kappa ∈ [0, 1]，1 表示完全一致，0 表示随机水平
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

    设计原则：
    - 字段定义使用 CSV_FIELDNAMES 常量（与 parallel_eval 共用，单一来源）
    - 有 filelock：FileLock(timeout=30) 防止并发写入和死锁
    - 无 filelock：回退串行写入并发出警告
    - 锁内用 f.tell()==0 判断是否写 header（比检查文件存在更可靠）
    - 缺失字段自动填空字符串，不会因字段缺失抛异常

    大规模测试建议：
    - n_runs > 50 时建议预先 pip install filelock 确保锁保护
    - 若单次写入 results 超过 10k 行，可考虑改用 sqlite 替代 CSV
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
