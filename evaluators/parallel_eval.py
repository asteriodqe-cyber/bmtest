from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

from tqdm import tqdm

from evaluators.runner import run_surrogate_agent, build_metadata
from evaluators.assertion_checker import run_rule_assertions_for_benchmark
from evaluators.llm_judge import run_llm_assertions_for_benchmark
from evaluators.gain_calculator import (
    calculate_metrics,
    calculate_skill_gain,
    calculate_cohens_kappa,
    save_to_csv,
    CSV_FIELDNAMES,
    _get_absolute_tier
)

TASK_TIMEOUT = 120


# ── 进度可视化工具 ────────────────────────────────────────

def print_header(title: str) -> None:
    width = 60
    print(f"\n{'='*width}")
    print(f"  {title}")
    print(f"{'='*width}")


def print_tier_bar(score: float) -> str:
    """可视化质量层级"""
    tier = _get_absolute_tier(score)
    bars = int(score * 20)
    bar = "█" * bars + "░" * (20 - bars)
    tier_icons = {"A": "★★★★", "B": "★★★☆", "C": "★★☆☆", "D": "★☆☆☆"}
    return f"[{bar}] {score:.3f} {tier_icons.get(tier, '')} Tier-{tier}"


def print_test_case_result(
    tc_id: str,
    tc_label: str,
    tc_type: str,
    skill_metrics: dict,
    baseline_metrics: dict,
    gain_result: dict,
    skill_kappa: float,
    baseline_kappa: float
) -> None:
    """打印单个测试用例的详细结果"""
    print(f"\n  {'─'*55}")
    print(f"  with_skill")
    print(f"    pass_rate  : {print_tier_bar(skill_metrics['pass_rate'])}")
    print(f"    consistency: {skill_metrics['consistency']:.3f}")
    print(f"    kappa      : {skill_kappa:.3f}")
    print(f"    final_score: {skill_metrics['final_score']:.3f}")
    print(f"  baseline")
    print(f"    pass_rate  : {print_tier_bar(baseline_metrics['pass_rate'])}")
    print(f"    consistency: {baseline_metrics['consistency']:.3f}")
    print(f"    kappa      : {baseline_kappa:.3f}")

    gain = gain_result['gain']
    efficacy = gain_result['efficacy']
    efficacy_icon = {"high": "🟢", "medium": "🟡", "low": "🔴"}.get(efficacy, "⚪")
    print(f"\n  Skill Gain   : {gain:+.3f} {efficacy_icon} {efficacy.upper()}")
    print(f"  Tier         : {gain_result['absolute_tier']}")
    print(f"  Meets Floor  : {'✅' if gain_result['meets_quality_floor'] else '❌'}")
    print(f"  Diagnosis    : {gain_result['diagnosis']}")


def print_overall_summary(
    benchmark_id: str,
    overall_gain: dict,
    total_cases: int,
    elapsed: float
) -> None:
    """打印整体汇总结果"""
    print_header(f"OVERALL {benchmark_id.upper()} RESULT")

    gain = overall_gain['gain']
    efficacy = overall_gain['efficacy']
    efficacy_icon = {"high": "🟢", "medium": "🟡", "low": "🔴"}.get(efficacy, "⚪")

    print(f"  {'Skill pass_rate :':<20} {print_tier_bar(overall_gain['skill_pass_rate'])}")
    print(f"  {'Base  pass_rate :':<20} {print_tier_bar(overall_gain['baseline_pass_rate'])}")
    print(f"  {'─'*55}")
    print(f"  {'Skill Gain      :':<20} {gain:+.3f} {efficacy_icon} {efficacy.upper()}")
    print(f"  {'Absolute Tier   :':<20} {overall_gain['absolute_tier']}")
    print(f"  {'Meets Floor     :':<20} {'✅ YES' if overall_gain['meets_quality_floor'] else '❌ NO'}")
    print(f"  {'Diagnosis       :':<20} {overall_gain['diagnosis']}")
    print(f"  {'─'*55}")
    print(f"  {'Test cases      :':<20} {total_cases}")
    print(f"  {'Elapsed time    :':<20} {elapsed:.1f}s ({elapsed/60:.1f}min)")
    print(f"{'='*60}\n")


# ── 单次评估（主进程直接调用，无 pickle 问题）────────────

def evaluate_single_run(args: tuple) -> dict:
    """
    单次评估，在主进程中串行执行

    改为串行的原因：
    Windows spawn 模式下 ProcessPoolExecutor 子进程启动开销过大，
    导致进程被强制终止。API 等待是主要瓶颈，串行执行总时间差异不大。
    """
    (
        skill_path, user_input, provider, model,
        temperature, use_skill, benchmark_id, scenario,
        api_keys
    ) = args

    if provider == "moonshot" and api_keys.get("moonshot"):
        os.environ["MOONSHOT_API_KEY"] = api_keys["moonshot"]
    elif provider == "anthropic" and api_keys.get("anthropic"):
        os.environ["ANTHROPIC_API_KEY"] = api_keys["anthropic"]

    result = run_surrogate_agent(
        skill_path=skill_path,
        user_input=user_input,
        provider=provider,
        model=model,
        temperature=temperature,
        use_skill=use_skill
    )

    rule_results = run_rule_assertions_for_benchmark(
        result.content, benchmark_id, scenario
    )
    llm_results = run_llm_assertions_for_benchmark(
        result.content, benchmark_id, scenario, provider
    )

    total_score = rule_results["rule_score"] + llm_results["llm_score"]
    total_max = rule_results["rule_max_score"] + llm_results["llm_max_score"]
    normalized = total_score / total_max if total_max > 0 else 0.0

    return {
        "normalized_score": round(normalized, 4),
        "rule_score": rule_results["rule_score"],
        "llm_score": llm_results["llm_score"],
        "total_score": round(total_score, 4),
        "total_max": total_max
    }


# ── 串行执行（替代原来的并行）────────────────────────────

def run_sequential(
    args_list: list[tuple],
    desc: str = "Evaluating"
) -> list[float]:
    """
    串行执行评估任务，返回 normalized_score 列表

    使用串行替代 ProcessPoolExecutor 的原因：
    - Windows spawn 模式下多进程并发导致子进程被强制终止
    - API 等待是主要瓶颈，串行执行总时间差异不大
    - 串行执行完全避免 pickle 序列化问题
    """
    scores = []
    success_count = 0
    fail_count = 0

    with tqdm(
        total=len(args_list),
        desc=f"    {desc}",
        leave=False,
        bar_format="{l_bar}{bar:25}{r_bar}"
    ) as pbar:
        for arg in args_list:
            try:
                result = evaluate_single_run(arg)
                scores.append(result["normalized_score"])
                success_count += 1
                pbar.set_postfix({
                    "ok": success_count,
                    "fail": fail_count,
                    "last": f"{result['normalized_score']:.2f}"
                })
            except Exception as e:
                fail_count += 1
                scores.append(0.0)
                pbar.set_postfix({
                    "ok": success_count,
                    "fail": fail_count,
                    "last": "ERROR"
                })
                tqdm.write(f"    [ERROR] {str(e)[:80]}")
            finally:
                pbar.update(1)

    if fail_count > 0:
        tqdm.write(f"    ⚠️  {fail_count} run(s) failed")

    return scores


# ── 主评估流程 ────────────────────────────────────────────

def run_benchmark(
    skill_path: str,
    benchmark_id: str,
    provider: str = "moonshot",
    model: str = "kimi-k2.5",
    temperature: float = 0.6,
    n_runs: int = 5,
    scenario: str | None = None
) -> dict:
    """运行完整的 benchmark 评估（with_skill vs baseline 对比）"""
    start_time = time.time()

    test_cases_path = Path(f"benchmark/test_cases/{benchmark_id}_inputs.json")
    test_cases_data = json.loads(test_cases_path.read_text(encoding="utf-8"))
    test_cases = test_cases_data["test_cases"]

    if benchmark_id == "b2" and scenario:
        test_cases = [tc for tc in test_cases if tc.get("scenario") == scenario]

    print_header(
        f"PRD Skill Benchmark — {benchmark_id.upper()}\n"
        f"  Provider : {provider} | Model: {model}\n"
        f"  Skill    : {skill_path}\n"
        f"  Cases    : {len(test_cases)} | Runs/case: {n_runs}\n"
        f"  Mode     : Sequential (stable on Windows)"
    )

    if provider == "moonshot":
        temperature = 0.6

    api_keys = {
        "moonshot": os.getenv("MOONSHOT_API_KEY", ""),
        "anthropic": os.getenv("ANTHROPIC_API_KEY", "")
    }

    if provider == "moonshot" and not api_keys["moonshot"]:
        raise EnvironmentError("MOONSHOT_API_KEY not set")
    if provider == "anthropic" and not api_keys["anthropic"]:
        raise EnvironmentError("ANTHROPIC_API_KEY not set")

    metadata = build_metadata(skill_path, provider, model, temperature, n_runs)
    skill_all_scores: list[float] = []
    baseline_all_scores: list[float] = []
    csv_rows: list[dict] = []

    standard_count = sum(1 for tc in test_cases if tc.get("type") == "standard")
    edge_count = sum(1 for tc in test_cases if tc.get("type") == "edge")
    print(f"\n  📊 Test breakdown: {standard_count} standard + {edge_count} edge cases")

    try:
        for i, tc in enumerate(test_cases, 1):
            tc_type = tc.get("type", "standard")
            tc_icon = "📌" if tc_type == "edge" else "📝"
            print(f"\n  {tc_icon} Case {i}/{len(test_cases)}: [{tc['id']}] {tc['label']}")

            skill_args = [
                (
                    skill_path, tc["prompt"], provider, model,
                    temperature, True, benchmark_id, scenario, api_keys
                )
                for _ in range(n_runs)
            ]
            baseline_args = [
                (
                    skill_path, tc["prompt"], provider, model,
                    temperature, False, benchmark_id, scenario, api_keys
                )
                for _ in range(n_runs)
            ]

            skill_scores = run_sequential(skill_args, desc="with_skill")
            baseline_scores = run_sequential(baseline_args, desc="baseline  ")

            skill_metrics = calculate_metrics(skill_scores)
            baseline_metrics = calculate_metrics(baseline_scores)
            gain_result = calculate_skill_gain(
                skill_scores, baseline_scores, benchmark_id
            )
            skill_kappa = calculate_cohens_kappa(skill_scores)
            baseline_kappa = calculate_cohens_kappa(baseline_scores)

            print_test_case_result(
                tc["id"], tc["label"], tc_type,
                skill_metrics, baseline_metrics,
                gain_result, skill_kappa, baseline_kappa
            )

            skill_all_scores.extend(skill_scores)
            baseline_all_scores.extend(baseline_scores)

            ts = time.strftime("%Y-%m-%d %H:%M:%S")

            skill_row = {
                "timestamp": ts,
                "benchmark_id": benchmark_id,
                "scenario": scenario or "",
                "test_case": tc["id"],
                "skill_path": skill_path,
                "skill_hash": metadata["skill_hash"],
                "condition": "with_skill",
                "provider": provider,
                "model": model,
                "n_runs": n_runs,
                "pass_rate": skill_metrics["pass_rate"],
                "consistency": skill_metrics["consistency"],
                "final_score": skill_metrics["final_score"],
                "kappa": skill_kappa,
                "gain": gain_result["gain"],
                "efficacy": gain_result["efficacy"],
                "absolute_tier": gain_result["absolute_tier"],
                "meets_quality_floor": gain_result["meets_quality_floor"],
                "quality_floor": gain_result["quality_floor"],
                "diagnosis": gain_result["diagnosis"]
            }

            baseline_row = {
                "timestamp": ts,
                "benchmark_id": benchmark_id,
                "scenario": scenario or "",
                "test_case": tc["id"],
                "skill_path": skill_path,
                "skill_hash": metadata["skill_hash"],
                "condition": "baseline",
                "provider": provider,
                "model": model,
                "n_runs": n_runs,
                "pass_rate": baseline_metrics["pass_rate"],
                "consistency": baseline_metrics["consistency"],
                "final_score": baseline_metrics["final_score"],
                "kappa": baseline_kappa,
                "gain": 0.0,
                "efficacy": "N/A",
                "absolute_tier": _get_absolute_tier(baseline_metrics["pass_rate"]),
                "meets_quality_floor": "",
                "quality_floor": gain_result["quality_floor"],
                "diagnosis": "N/A"
            }

            assert set(skill_row.keys()) == set(CSV_FIELDNAMES), (
                f"skill_row keys mismatch CSV_FIELDNAMES\n"
                f"  extra  : {set(skill_row.keys()) - set(CSV_FIELDNAMES)}\n"
                f"  missing: {set(CSV_FIELDNAMES) - set(skill_row.keys())}"
            )
            assert set(baseline_row.keys()) == set(CSV_FIELDNAMES), (
                f"baseline_row keys mismatch CSV_FIELDNAMES\n"
                f"  extra  : {set(baseline_row.keys()) - set(CSV_FIELDNAMES)}\n"
                f"  missing: {set(CSV_FIELDNAMES) - set(baseline_row.keys())}"
            )

            csv_rows.extend([skill_row, baseline_row])

    except KeyboardInterrupt:
        print("\n  ⚠️  Interrupted — saving partial results...")
    finally:
        if csv_rows:
            save_to_csv(csv_rows)
            print(f"\n  💾 Results saved → experiments/results.csv ({len(csv_rows)} rows)")

    if not skill_all_scores:
        print("  No results to summarize.")
        return {}

    overall_gain = calculate_skill_gain(
        skill_all_scores, baseline_all_scores, benchmark_id
    )

    elapsed = time.time() - start_time
    print_overall_summary(benchmark_id, overall_gain, len(test_cases), elapsed)

    return overall_gain


def main():
    parser = argparse.ArgumentParser(
        description="PRD Skill Benchmark Evaluator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python evaluators/parallel_eval.py --skill datasets/generated_skills/zero_shot/skill_v1.md --benchmark b1
  python evaluators/parallel_eval.py --skill datasets/generated_skills/few_shot/skill_v1.md --benchmark b2 --scenario b2b
  python evaluators/parallel_eval.py --skill datasets/generated_skills/zero_shot/skill_v1.md --benchmark b3 --n-runs 3
        """
    )
    parser.add_argument("--skill", required=True, help="Path to SKILL.md file")
    parser.add_argument("--benchmark", required=True, choices=["b1", "b2", "b3"])
    parser.add_argument("--provider", default="moonshot", choices=["moonshot", "anthropic"])
    parser.add_argument("--model", default="kimi-k2.5")
    parser.add_argument("--temperature", type=float, default=0.6)
    parser.add_argument("--n-runs", type=int, default=5)
    parser.add_argument("--scenario", default=None,
                        help="B2 only: b2b / consumer / internal")

    args = parser.parse_args()

    run_benchmark(
        skill_path=args.skill,
        benchmark_id=args.benchmark,
        provider=args.provider,
        model=args.model,
        temperature=args.temperature,
        n_runs=args.n_runs,
        scenario=args.scenario
    )


if __name__ == "__main__":
    main()
