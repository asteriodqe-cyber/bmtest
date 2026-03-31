from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path

import aiohttp
from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv(Path(__file__).parent.parent / ".env")

from evaluators.runner import run_surrogate_agent, build_metadata, compute_sha256
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

# ── 日志配置 ──────────────────────────────────────────────

Path("logs").mkdir(exist_ok=True)
LOG_FILE = f"logs/benchmark_{datetime.now():%m%d_%H%M%S}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ]
)
logger = logging.getLogger(__name__)

CHECKPOINT_FILE = "experiments/checkpoint.json"
SAMPLES_DIR = Path("experiments/samples")
TASK_SEMAPHORE_SIZE = 3


# ── 断点续传 ──────────────────────────────────────────────

def load_checkpoint() -> dict:
    path = Path(CHECKPOINT_FILE)
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        logger.info(f"Checkpoint loaded: {len(data.get('completed_runs', []))} runs completed")
        return data
    return {"completed_runs": [], "results": []}


def save_checkpoint(checkpoint: dict) -> None:
    Path(CHECKPOINT_FILE).parent.mkdir(exist_ok=True)
    Path(CHECKPOINT_FILE).write_text(
        json.dumps(checkpoint, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def clear_checkpoint() -> None:
    path = Path(CHECKPOINT_FILE)
    if path.exists():
        path.unlink()
        logger.info("Checkpoint cleared — experiment completed successfully")


def make_run_id(
    skill_path: str,
    benchmark_id: str,
    scenario: str | None,
    tc_id: str,
    condition: str,
    run_idx: int
) -> str:
    skill_hash = compute_sha256(skill_path)[:8]
    scenario_part = f"_{scenario}" if scenario else ""
    return f"{skill_hash}_{benchmark_id}{scenario_part}_{tc_id}_{condition}_{run_idx}"


def save_sample(
    run_id: str,
    prd_content: str,
    rule_results: dict,
    llm_results: dict,
    normalized_score: float,
    use_skill: bool,
    prompt: str
) -> None:
    """
    保存单次运行的详细样本，用于人工审查

    文件存储在 experiments/samples/<run_id>.json
    包含：PRD 完整内容、每条断言的判断结果和理由
    """
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)

    sample = {
        "run_id": run_id,
        "condition": "with_skill" if use_skill else "baseline",
        "prompt": prompt,
        "normalized_score": normalized_score,
        "prd_content": prd_content,
        "rule_assertions": rule_results.get("results", []),
        "llm_assertions": llm_results.get("results", []),
        "rule_score": rule_results.get("rule_score", 0),
        "llm_score": llm_results.get("llm_score", 0),
        "total_max": rule_results.get("rule_max_score", 0) + llm_results.get("llm_max_score", 0)
    }

    sample_path = SAMPLES_DIR / f"{run_id}.json"
    sample_path.write_text(
        json.dumps(sample, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    logger.info(f"[SAMPLE] Saved {sample_path}")


# ── 可视化工具 ────────────────────────────────────────────

def print_header(title: str) -> None:
    width = 60
    print(f"\n{'='*width}")
    print(f"  {title}")
    print(f"{'='*width}")


def print_tier_bar(score: float) -> str:
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
    print_header(f"OVERALL {benchmark_id.upper()} RESULT")
    print(f"  {'Skill pass_rate :':<20} {print_tier_bar(overall_gain['skill_pass_rate'])}")
    print(f"  {'Base  pass_rate :':<20} {print_tier_bar(overall_gain['baseline_pass_rate'])}")
    print(f"  {'─'*55}")
    gain = overall_gain['gain']
    efficacy = overall_gain['efficacy']
    efficacy_icon = {"high": "🟢", "medium": "🟡", "low": "🔴"}.get(efficacy, "⚪")
    print(f"  {'Skill Gain      :':<20} {gain:+.3f} {efficacy_icon} {efficacy.upper()}")
    print(f"  {'Absolute Tier   :':<20} {overall_gain['absolute_tier']}")
    print(f"  {'Meets Floor     :':<20} {'✅ YES' if overall_gain['meets_quality_floor'] else '❌ NO'}")
    print(f"  {'Diagnosis       :':<20} {overall_gain['diagnosis']}")
    print(f"  {'─'*55}")
    print(f"  {'Test cases      :':<20} {total_cases}")
    print(f"  {'Elapsed time    :':<20} {elapsed:.1f}s ({elapsed/60:.1f}min)")
    print(f"  {'Log file        :':<20} {LOG_FILE}")
    print(f"  {'Samples dir     :':<20} experiments/samples/")
    print(f"{'='*60}\n")


# ── 单次评估 ──────────────────────────────────────────────

async def evaluate_single_run(
    session: aiohttp.ClientSession,
    semaphore: asyncio.Semaphore,
    skill_path: str,
    user_input: str,
    use_skill: bool,
    benchmark_id: str,
    scenario: str | None,
    run_id: str,
    checkpoint: dict,
    prompt: str
) -> dict:
    """单次评估（async），支持断点续传，保存详细样本"""
    if run_id in checkpoint["completed_runs"]:
        cached = next(
            (r for r in checkpoint["results"] if r.get("run_id") == run_id),
            None
        )
        if cached:
            logger.info(f"[SKIP] {run_id} — loaded from checkpoint")
            return cached

    async with semaphore:
        logger.info(f"[START] {run_id}")
        start = time.time()

        result = await run_surrogate_agent(
            session=session,
            skill_path=skill_path,
            user_input=user_input,
            use_skill=use_skill
        )

        rule_results = run_rule_assertions_for_benchmark(
            result.content, benchmark_id, scenario
        )
        llm_results = await run_llm_assertions_for_benchmark(
            result.content, benchmark_id, scenario
        )

        total_score = rule_results["rule_score"] + llm_results["llm_score"]
        total_max = rule_results["rule_max_score"] + llm_results["llm_max_score"]
        normalized = total_score / total_max if total_max > 0 else 0.0

        elapsed = time.time() - start
        logger.info(f"[DONE] {run_id} | score={normalized:.3f} | {elapsed:.1f}s")

        # 保存详细样本（透明化黑箱）
        save_sample(
            run_id=run_id,
            prd_content=result.content,
            rule_results=rule_results,
            llm_results=llm_results,
            normalized_score=normalized,
            use_skill=use_skill,
            prompt=prompt
        )

        run_result = {
            "run_id": run_id,
            "normalized_score": round(normalized, 4),
            "rule_score": rule_results["rule_score"],
            "llm_score": llm_results["llm_score"],
            "total_score": round(total_score, 4),
            "total_max": total_max,
            "elapsed": round(elapsed, 2)
        }

        checkpoint["completed_runs"].append(run_id)
        checkpoint["results"].append(run_result)
        save_checkpoint(checkpoint)

        return run_result


# ── 主评估流程 ────────────────────────────────────────────

async def run_benchmark(
    skill_path: str,
    benchmark_id: str,
    n_runs: int = 3,
    scenario: str | None = None
) -> dict:
    """运行完整的 benchmark 评估（async，支持断点续传）"""
    start_time = time.time()

    test_cases_path = Path(f"benchmark/test_cases/{benchmark_id}_inputs.json")
    test_cases_data = json.loads(test_cases_path.read_text(encoding="utf-8"))
    test_cases = test_cases_data["test_cases"]

    if benchmark_id == "b2" and scenario:
        test_cases = [tc for tc in test_cases if tc.get("scenario") == scenario]

    provider = "moonshot"
    model = "kimi-k2.5"
    temperature = 1.0

    print_header(
        f"PRD Skill Benchmark — {benchmark_id.upper()}\n"
        f"  Provider : {provider} | Model: {model}\n"
        f"  Skill    : {skill_path}\n"
        f"  Cases    : {len(test_cases)} | Runs/case: {n_runs}\n"
        f"  Concurrency: {TASK_SEMAPHORE_SIZE} | Judge: Claude Sonnet"
    )

    checkpoint = load_checkpoint()
    resumed = len(checkpoint["completed_runs"])
    if resumed > 0:
        print(f"\n  ♻️  Resuming from checkpoint: {resumed} runs already completed")

    metadata = build_metadata(skill_path, provider, model, temperature, n_runs)
    skill_all_scores: list[float] = []
    baseline_all_scores: list[float] = []
    csv_rows: list[dict] = []

    standard_count = sum(1 for tc in test_cases if tc.get("type") == "standard")
    edge_count = sum(1 for tc in test_cases if tc.get("type") == "edge")
    print(f"\n  📊 Test breakdown: {standard_count} standard + {edge_count} edge cases")

    semaphore = asyncio.Semaphore(TASK_SEMAPHORE_SIZE)

    connector = aiohttp.TCPConnector(limit=TASK_SEMAPHORE_SIZE * 2)
    async with aiohttp.ClientSession(connector=connector) as session:
        try:
            for i, tc in enumerate(test_cases, 1):
                tc_type = tc.get("type", "standard")
                tc_icon = "📌" if tc_type == "edge" else "📝"
                print(f"\n  {tc_icon} Case {i}/{len(test_cases)}: [{tc['id']}] {tc['label']}")

                skill_run_ids = [
                    make_run_id(skill_path, benchmark_id, scenario, tc["id"], "with_skill", j)
                    for j in range(n_runs)
                ]
                baseline_run_ids = [
                    make_run_id(skill_path, benchmark_id, scenario, tc["id"], "baseline", j)
                    for j in range(n_runs)
                ]

                # with_skill 并发执行
                print(f"    with_skill ({n_runs} runs, max {TASK_SEMAPHORE_SIZE} concurrent)...")
                skill_tasks = [
                    evaluate_single_run(
                        session, semaphore, skill_path, tc["prompt"],
                        True, benchmark_id, scenario, run_id, checkpoint,
                        tc["prompt"]
                    )
                    for run_id in skill_run_ids
                ]

                skill_results = []
                with tqdm(total=n_runs, desc="    with_skill", leave=False,
                         bar_format="{l_bar}{bar:20}{r_bar}") as pbar:
                    for coro in asyncio.as_completed(skill_tasks):
                        try:
                            result = await coro
                            skill_results.append(result)
                            pbar.set_postfix({"score": f"{result['normalized_score']:.2f}"})
                        except Exception as e:
                            skill_results.append({"normalized_score": 0.0})
                            tqdm.write(f"    [FAILED] {str(e)[:60]}")
                            logger.error(f"with_skill run failed: {e}")
                        finally:
                            pbar.update(1)

                # baseline 并发执行
                baseline_tasks = [
                    evaluate_single_run(
                        session, semaphore, skill_path, tc["prompt"],
                        False, benchmark_id, scenario, run_id, checkpoint,
                        tc["prompt"]
                    )
                    for run_id in baseline_run_ids
                ]

                baseline_results = []
                with tqdm(total=n_runs, desc="    baseline  ", leave=False,
                         bar_format="{l_bar}{bar:20}{r_bar}") as pbar:
                    for coro in asyncio.as_completed(baseline_tasks):
                        try:
                            result = await coro
                            baseline_results.append(result)
                            pbar.set_postfix({"score": f"{result['normalized_score']:.2f}"})
                        except Exception as e:
                            baseline_results.append({"normalized_score": 0.0})
                            tqdm.write(f"    [FAILED] {str(e)[:60]}")
                            logger.error(f"baseline run failed: {e}")
                        finally:
                            pbar.update(1)

                skill_scores = [r["normalized_score"] for r in skill_results]
                baseline_scores = [r["normalized_score"] for r in baseline_results]

                skill_metrics = calculate_metrics(skill_scores)
                baseline_metrics = calculate_metrics(baseline_scores)
                gain_result = calculate_skill_gain(skill_scores, baseline_scores, benchmark_id)
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
                    f"skill_row keys mismatch\n"
                    f"  extra  : {set(skill_row.keys()) - set(CSV_FIELDNAMES)}\n"
                    f"  missing: {set(CSV_FIELDNAMES) - set(skill_row.keys())}"
                )
                assert set(baseline_row.keys()) == set(CSV_FIELDNAMES), (
                    f"baseline_row keys mismatch\n"
                    f"  extra  : {set(baseline_row.keys()) - set(CSV_FIELDNAMES)}\n"
                    f"  missing: {set(CSV_FIELDNAMES) - set(baseline_row.keys())}"
                )

                csv_rows.extend([skill_row, baseline_row])

        except KeyboardInterrupt:
            print("\n  ⚠️  Interrupted — checkpoint saved, run again to resume")
            logger.info("Interrupted by user")

        finally:
            if csv_rows:
                save_to_csv(csv_rows)
                print(f"\n  💾 Results saved → experiments/results.csv ({len(csv_rows)} rows)")
                logger.info(f"Results saved: {len(csv_rows)} rows")

    if not skill_all_scores:
        print("  No results to summarize.")
        return {}

    overall_gain = calculate_skill_gain(skill_all_scores, baseline_all_scores, benchmark_id)
    elapsed = time.time() - start_time
    print_overall_summary(benchmark_id, overall_gain, len(test_cases), elapsed)

    clear_checkpoint()
    logger.info(f"Benchmark {benchmark_id} completed in {elapsed:.1f}s")

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
    parser.add_argument("--n-runs", type=int, default=3)
    parser.add_argument("--scenario", default=None,
                        help="B2 only: b2b / consumer / internal")

    args = parser.parse_args()

    asyncio.run(run_benchmark(
        skill_path=args.skill,
        benchmark_id=args.benchmark,
        n_runs=args.n_runs,
        scenario=args.scenario
    ))


if __name__ == "__main__":
    main()
