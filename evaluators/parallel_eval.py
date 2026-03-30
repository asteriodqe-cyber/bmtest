from __future__ import annotations

import argparse
import json
import multiprocessing
import os
import time
from concurrent.futures import ProcessPoolExecutor, as_completed, TimeoutError
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
    CSV_FIELDNAMES
)

# 单个任务的最长允许时间（秒）
TASK_TIMEOUT = 120


def evaluate_single_run(args: tuple) -> dict:
    """
    单次评估（在独立进程中运行）
    显式从 args 接收 api_keys，不依赖 spawn 模式的环境变量继承
    所有参数通过 tuple 传入确保可 pickle 序列化
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


def run_parallel(
    args_list: list[tuple],
    n_workers: int,
    mp_context,
    desc: str = "Evaluating"
) -> list[float]:
    """
    并行执行一批任务，返回 normalized_score 列表
    - future.result(timeout=TASK_TIMEOUT) 防止僵尸任务卡死
    - tqdm 进度条提供长运行反馈
    - 结果统一返回主进程，不在子进程写 CSV
    """
    scores = []
    actual_workers = min(n_workers, 4)

    with ProcessPoolExecutor(
        max_workers=actual_workers,
        mp_context=mp_context
    ) as executor:
        futures = [executor.submit(evaluate_single_run, arg) for arg in args_list]

        with tqdm(total=len(futures), desc=desc, leave=False) as pbar:
            for future in as_completed(futures):
                try:
                    result = future.result(timeout=TASK_TIMEOUT)
                    scores.append(result["normalized_score"])
                except TimeoutError:
                    print(f"\n  [TIMEOUT] Run exceeded {TASK_TIMEOUT}s, treating as 0.0")
                    scores.append(0.0)
                except Exception as e:
                    print(f"\n  [ERROR] Run failed: {e}")
                    scores.append(0.0)
                finally:
                    pbar.update(1)

    return scores


def run_benchmark(
    skill_path: str,
    benchmark_id: str,
    provider: str = "moonshot",
    model: str = "kimi-k2.5",
    temperature: float = 0.6,
    n_runs: int = 5,
    scenario: str | None = None
) -> dict:
    """
    运行完整的 benchmark 评估（with_skill vs baseline 对比）

    设计：
    - 主进程预加载 api_keys，显式传入子进程
    - baseline 和 with_skill 结果都写入 CSV
    - try/finally 确保崩溃或中断时已完成的结果不丢失
    - csv_rows 的键通过运行时断言严格对齐 CSV_FIELDNAMES（单一来源）
    """
    test_cases_path = Path(f"benchmark/test_cases/{benchmark_id}_inputs.json")
    test_cases_data = json.loads(test_cases_path.read_text(encoding="utf-8"))
    test_cases = test_cases_data["test_cases"]

    if benchmark_id == "b2" and scenario:
        test_cases = [tc for tc in test_cases if tc.get("scenario") == scenario]

    print(f"\n{'='*50}")
    print(f"Benchmark : {benchmark_id.upper()}")
    print(f"Provider  : {provider} | Model: {model}")
    print(f"Test cases: {len(test_cases)} | Runs per case: {n_runs}")
    print(f"{'='*50}")

    mp_context = multiprocessing.get_context("spawn")

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

    try:
        for tc in test_cases:
            tc_type = tc.get("type", "standard")
            print(f"\n[{tc['id']}] {tc['label']} ({tc_type})")

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

            skill_scores = run_parallel(
                skill_args, n_runs, mp_context, desc="  with_skill"
            )
            baseline_scores = run_parallel(
                baseline_args, n_runs, mp_context, desc="  baseline  "
            )

            skill_metrics = calculate_metrics(skill_scores)
            baseline_metrics = calculate_metrics(baseline_scores)
            gain_result = calculate_skill_gain(skill_scores, baseline_scores)
            skill_kappa = calculate_cohens_kappa(skill_scores)
            baseline_kappa = calculate_cohens_kappa(baseline_scores)

            print(f"  with_skill → pass_rate: {skill_metrics['pass_rate']:.3f} | "
                  f"consistency: {skill_metrics['consistency']:.3f} | "
                  f"kappa: {skill_kappa:.3f}")
            print(f"  baseline   → pass_rate: {baseline_metrics['pass_rate']:.3f} | "
                  f"consistency: {baseline_metrics['consistency']:.3f} | "
                  f"kappa: {baseline_kappa:.3f}")
            print(f"  Skill Gain → {gain_result['gain']:.3f} ({gain_result['efficacy']})")

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
                "efficacy": gain_result["efficacy"]
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
                "efficacy": "N/A"
            }

            # 运行时验证字段对齐，防止 CSV_FIELDNAMES 与 row 键集合漂移
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
        print("\n⚠️  Interrupted — saving partial results...")
    finally:
        if csv_rows:
            save_to_csv(csv_rows)
            print(f"Results saved → experiments/results.csv ({len(csv_rows)} rows)")

    if not skill_all_scores:
        print("No results to summarize.")
        return {}

    overall_gain = calculate_skill_gain(skill_all_scores, baseline_all_scores)

    print(f"\n{'='*50}")
    print(f"OVERALL {benchmark_id.upper()} RESULT")
    print(f"  Skill Gain     : {overall_gain['gain']:.3f} ({overall_gain['efficacy']})")
    print(f"  Skill pass_rate: {overall_gain['skill_pass_rate']:.3f}")
    print(f"  Base  pass_rate: {overall_gain['baseline_pass_rate']:.3f}")
    print(f"{'='*50}\n")

    return overall_gain


def main():
    parser = argparse.ArgumentParser(description="PRD Skill Benchmark Evaluator")
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
