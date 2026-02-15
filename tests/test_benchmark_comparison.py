#!/usr/bin/env python3
"""
Pytest-based benchmark comparison between Python and Rust deny list implementations.
This test always displays detailed output regardless of pytest flags.
"""

import asyncio
import json
import pytest
import statistics
import logging 
from mcpgateway.plugins.framework import PluginConfig, Plugin, PluginContext
from mcpgateway.plugins.framework.hooks.prompts import (
    PromptHookType,
    PromptPrehookPayload,
    PromptPrehookResult,
)
from mcpgateway.plugins.framework.models import GlobalContext
from pathlib import Path
from typing import List, Dict, Any, Type, Protocol, runtime_checkable

from plugins.deny_filter.deny import DenyListPlugin
from plugins.deny_filter.deny_rust import DenyListPluginRust
from plugins.deny_filter.deny_rust_rs import DenyListPluginRustRs

from mcpgateway.services.logging_service import LoggingService

# Initialize logging service first
loggingSvc = LoggingService()
loggingSvc.get_logger("plugins.deny_filter.deny").setLevel(logging.ERROR)
loggingSvc.get_logger("plugins.deny_filter.deny_rust").setLevel(logging.ERROR)
loggingSvc.get_logger("plugins.deny_filter.deny_rust_rs").setLevel(logging.ERROR)


WARMUP_RUNS = 3000
BENCHMARK_RUNS = 10000
CONFIG_FILES = [
    "data/deny_check_config_10.json",
    "data/deny_check_config_20.json",
    "data/deny_check_config_100.json",
    "data/deny_check_config_200.json"
]
RUNS_PER_CONFIG = 1
FIRST_IMPL = DenyListPlugin
SECOND_IMPL = DenyListPluginRustRs


@runtime_checkable
class PromptPreFetchPlugin(Protocol):
    """Protocol for plugins that implement prompt_pre_fetch hook."""

    async def prompt_pre_fetch(
            self, payload: PromptPrehookPayload, context: PluginContext
    ) -> PromptPrehookResult:
        """The plugin hook run before a prompt is retrieved and rendered."""
        ...


def load_config(config_path: str) -> Dict[str, Any]:
    """Load the deny check configuration from JSON file."""
    config_file = Path(config_path)
    if not config_file.exists():
        config_file = Path(__file__).parent / config_path

    with open(config_file, "r") as f:
        return json.load(f)


def create_plugin_instances(
        config: Dict[str, Any], plugin_type: Type[Plugin]
) -> List[tuple[str, PromptPreFetchPlugin]]:
    """Create plugin instances for each deny word list."""
    plugins = []

    for deny_list in config["deny_word_lists"]:
        plugin_config = PluginConfig(
            name=f"deny_filter_{deny_list['name']}",
            kind=f"{plugin_type.__module__}.{plugin_type.__name__}",
            hooks=[PromptHookType.PROMPT_PRE_FETCH],
            priority=100,
            config={"words": deny_list["words"]},
        )

        plugin = plugin_type(config=plugin_config)
        plugins.append((deny_list["name"], plugin))

    return plugins


async def benchmark_plugin(
        plugins: List[tuple[str, PromptPreFetchPlugin]],
        sample_texts: List[Dict[str, Any]],
        config: Dict[str, Any],
        warmup_runs: int = WARMUP_RUNS,
        benchmark_runs: int = BENCHMARK_RUNS,
) -> Dict[str, Any]:
    """Benchmark prompt_pre_fetch execution for all combinations."""
    import time

    gctx = GlobalContext(request_id="deny-benchmark")
    ctx = PluginContext(global_context=gctx)

    results = {
        "total_combinations": len(plugins) * len(sample_texts),
        "warmup_runs": warmup_runs,
        "benchmark_runs": benchmark_runs,
        "total_time_us": 0.0,
        "combinations": [],
    }

    for plugin_name, plugin in plugins:
        plugin_deny_words = []
        for deny_list in config["deny_word_lists"]:
            if deny_list["name"] == plugin_name:
                plugin_deny_words = deny_list["words"]
                break

        for sample in sample_texts:
            # Use should_block from data file, not recalculated
            should_block = sample.get("should_block", False)

            payload = PromptPrehookPayload(
                prompt_id="benchmark_test",
                args={
                    "text": sample["text"],
                    "system": sample["text"],
                    "other": sample["text"],
                }
            )

            # Warmup
            for _ in range(warmup_runs):
                await plugin.prompt_pre_fetch(payload, ctx)

            # Benchmark
            timings_us = []
            actual_blocked = None

            for i in range(benchmark_runs):
                start = time.perf_counter()
                result = await plugin.prompt_pre_fetch(payload, ctx)
                elapsed = time.perf_counter() - start
                timings_us.append(elapsed * 1_000_000)

                if i == 0:
                    actual_blocked = result.violation is not None

            # Statistics
            timings_us.sort()
            median = statistics.median(timings_us)
            p99_index = int(len(timings_us) * 0.99)
            p99 = timings_us[p99_index]
            mean = statistics.mean(timings_us)
            min_time = min(timings_us)
            total_time_combination = sum(timings_us)

            combination_result = {
                "plugin_name": plugin_name,
                "sample_name": sample["name"],
                "sample_text_length": len(sample["text"]),
                "expected_block": should_block,
                "actual_blocked": actual_blocked,
                "matches_expected": actual_blocked == should_block,
                "timings": {
                    "median_us": round(median, 2),
                    "p99_us": round(p99, 2),
                    "mean_us": round(mean, 2),
                    "min_us": round(min_time, 2),
                    "total_us": round(total_time_combination, 2),
                },
            }

            results["combinations"].append(combination_result)
            results["total_time_us"] += total_time_combination

    return results


def print_summary(results: Dict[str, Any], plugin_name: str, config: Dict[str, Any] = None):
    """Print benchmark summary - always visible."""
    all_medians = [c["timings"]["median_us"] for c in results["combinations"]]
    all_p99s = [c["timings"]["p99_us"] for c in results["combinations"]]

    total_time_s = results["total_time_us"] / 1_000_000

    mismatches = [
        c for c in results["combinations"] if not c.get("matches_expected", True)
    ]
    total_tests = len(results["combinations"])
    passed_tests = total_tests - len(mismatches)

    # Calculate total deny words and sample text sizes
    total_deny_words = 0
    sample_text_sizes = []
    if config:
        for deny_list in config["deny_word_lists"]:
            total_deny_words += len(deny_list["words"])
        for sample in config["sample_texts"]:
            sample_text_sizes.append(len(sample["text"]))

    print("\n" + "=" * 80)
    print(f"BENCHMARK RESULTS - {plugin_name}")
    print("=" * 80)
    if config:
        print(f"Total Deny Words: {total_deny_words}")
        if sample_text_sizes:
            print(
                f"Sample Text Sizes: min={min(sample_text_sizes)}, max={max(sample_text_sizes)}, avg={sum(sample_text_sizes) // len(sample_text_sizes)}")
        print("-" * 80)
    print(f"Median:     {statistics.median(all_medians):.2f}μs")
    print(f"P99:        {statistics.median(all_p99s):.2f}μs")
    print(f"Total Time: {total_time_s:.6f}s ({results['total_time_us']:.2f}μs)")
    print("=" * 80)
    print(f"\nTest Results: {passed_tests}/{total_tests} passed")

    if mismatches:
        print("\n" + "=" * 80)
        print("MISMATCHES DETECTED")
        print("=" * 80)
        for mismatch in mismatches:
            print(f"\nPlugin: {mismatch['plugin_name']}")
            print(f"Sample: {mismatch['sample_name']}")
            print(f"Expected Block: {mismatch['expected_block']}")
            print(f"Actual Blocked: {mismatch['actual_blocked']}")
            print("-" * 40)
    else:
        print("\n✓ All tests passed - actual behavior matches expected!")
    print("=" * 80)


def print_comparison(first_results: Dict[str, Any], second_results: Dict[str, Any], first_name: str, second_name: str,
                     config: Dict[str, Any] = None):
    """Print comparison between two implementations - always visible."""
    first_medians = [c["timings"]["median_us"] for c in first_results["combinations"]]
    second_medians = [c["timings"]["median_us"] for c in second_results["combinations"]]

    first_p99s = [c["timings"]["p99_us"] for c in first_results["combinations"]]
    second_p99s = [c["timings"]["p99_us"] for c in second_results["combinations"]]

    first_median = statistics.median(first_medians)
    second_median = statistics.median(second_medians)

    first_p99 = statistics.median(first_p99s)
    second_p99 = statistics.median(second_p99s)

    first_total = first_results["total_time_us"]
    second_total = second_results["total_time_us"]

    median_speedup = first_median / second_median if second_median > 0 else 0
    p99_speedup = first_p99 / second_p99 if second_p99 > 0 else 0
    total_speedup = first_total / second_total if second_total > 0 else 0

    # Calculate total deny words and sample text sizes
    total_deny_words = 0
    sample_text_sizes = []
    if config:
        for deny_list in config["deny_word_lists"]:
            total_deny_words += len(deny_list["words"])
        for sample in config["sample_texts"]:
            sample_text_sizes.append(len(sample["text"]))

    print("\n" + "=" * 80)
    print(f"{first_name} vs {second_name} COMPARISON")
    print("=" * 80)
    if config:
        print(f"Total Deny Words: {total_deny_words}")
        if sample_text_sizes:
            print(
                f"Sample Text Sizes: min={min(sample_text_sizes)}, max={max(sample_text_sizes)}, avg={sum(sample_text_sizes) // len(sample_text_sizes)}")
        print("-" * 80)
    print(f"{'Metric':<20} {first_name:<15} {second_name:<15} {'Speedup':<15}")
    print("-" * 80)
    print(
        f"{'Median':<20} {first_median:>10.2f}μs {second_median:>10.2f}μs {median_speedup:>10.2f}x"
    )
    print(f"{'P99':<20} {first_p99:>10.2f}μs {second_p99:>10.2f}μs {p99_speedup:>10.2f}x")
    print(
        f"{'Total Time':<20} {first_total / 1_000_000:>10.6f}s {second_total / 1_000_000:>10.6f}s {total_speedup:>10.2f}x"
    )
    print("=" * 80)
    print(f"\n🚀 {second_name} is {median_speedup:.2f}x faster than {first_name} (median)")
    print(f"🚀 {second_name} is {p99_speedup:.2f}x faster than {first_name} (p99)")
    print(f"🚀 {second_name} is {total_speedup:.2f}x faster than {first_name} (total time)")
    print("=" * 80 + "\n")


@pytest.mark.asyncio
async def test_benchmark_comparison():
    """Benchmark comparison with config - runs all configs multiple times"""

    first_name = FIRST_IMPL.__name__
    second_name = SECOND_IMPL.__name__

    print("\n" + "=" * 80)
    print(f"DENY CHECK BENCHMARK - {first_name} vs {second_name} Comparison")
    print("=" * 80)
    print(f"Configs: {len(CONFIG_FILES)} files x {RUNS_PER_CONFIG} runs each")
    print(f"Warmup Runs: {WARMUP_RUNS}")
    print(f"Benchmark Runs: {BENCHMARK_RUNS}")
    print("=" * 80)

    # Store all results for final summary
    all_config_results = []

    for config_path in CONFIG_FILES:
        config = load_config(config_path)
        
        # Calculate actual word count from config
        word_count = sum(len(deny_list["words"]) for deny_list in config["deny_word_lists"])

        print(f"\n{'=' * 80}")
        print(f"CONFIG: {config_path} ({word_count} words)")
        print(f"{'=' * 80}")

        # Run each config RUNS_PER_CONFIG times
        config_run_results = []

        for run_num in range(1, RUNS_PER_CONFIG + 1):
            print(f"\n--- Run {run_num}/{RUNS_PER_CONFIG} for {word_count} words config ---")

            # First implementation benchmark
            print(f"\nBenchmarking {first_name} implementation...")
            first_plugins = create_plugin_instances(config, FIRST_IMPL)
            first_results = await benchmark_plugin(
                first_plugins,
                config["sample_texts"],
                config,
            )

            # Second implementation benchmark
            print(f"\nBenchmarking {second_name} implementation...")
            second_plugins = create_plugin_instances(config, SECOND_IMPL)
            second_results = await benchmark_plugin(
                second_plugins,
                config["sample_texts"],
                config,
                warmup_runs=WARMUP_RUNS,
                benchmark_runs=BENCHMARK_RUNS,
            )

            config_run_results.append({
                'run': run_num,
                'first_results': first_results,
                'second_results': second_results
            })

        # Store results for this config
        all_config_results.append({
            'config_path': config_path,
            'word_count': word_count,
            'config': config,
            'runs': config_run_results
        })

    # Print final summary for all configs
    print("\n" + "=" * 80)
    print("FINAL SUMMARY - ALL CONFIGURATIONS")
    print("=" * 80)

    for config_result in all_config_results:
        word_count = config_result['word_count']
        config = config_result['config']
        runs = config_result['runs']

        print(f"\n{'=' * 80}")
        print(f"Configuration: {word_count} words")
        print(f"{'=' * 80}")

        # Calculate sample text sizes for this config
        sample_text_sizes = [len(sample["text"]) for sample in config["sample_texts"]]
        if sample_text_sizes:
            print(
                f"Sample Text Sizes: min={min(sample_text_sizes)}, max={max(sample_text_sizes)}, avg={sum(sample_text_sizes) // len(sample_text_sizes)}")
            print("-" * 80)

        # Aggregate results across all runs
        all_first_medians = []
        all_second_medians = []
        all_first_p99s = []
        all_second_p99s = []
        all_first_totals = []
        all_second_totals = []

        for run_data in runs:
            first_res = run_data['first_results']
            second_res = run_data['second_results']

            first_medians = [c["timings"]["median_us"] for c in first_res["combinations"]]
            second_medians = [c["timings"]["median_us"] for c in second_res["combinations"]]
            first_p99s = [c["timings"]["p99_us"] for c in first_res["combinations"]]
            second_p99s = [c["timings"]["p99_us"] for c in second_res["combinations"]]

            all_first_medians.append(statistics.median(first_medians))
            all_second_medians.append(statistics.median(second_medians))
            all_first_p99s.append(statistics.median(first_p99s))
            all_second_p99s.append(statistics.median(second_p99s))
            all_first_totals.append(first_res["total_time_us"])
            all_second_totals.append(second_res["total_time_us"])

        # Calculate averages
        avg_first_median = statistics.mean(all_first_medians)
        avg_second_median = statistics.mean(all_second_medians)
        avg_first_p99 = statistics.mean(all_first_p99s)
        avg_second_p99 = statistics.mean(all_second_p99s)
        avg_first_total = statistics.mean(all_first_totals)
        avg_second_total = statistics.mean(all_second_totals)

        median_speedup = avg_first_median / avg_second_median if avg_second_median > 0 else 0
        p99_speedup = avg_first_p99 / avg_second_p99 if avg_second_p99 > 0 else 0
        total_speedup = avg_first_total / avg_second_total if avg_second_total > 0 else 0

        print(f"Runs: {RUNS_PER_CONFIG}")
        print(f"{'Metric':<20} {first_name:<15} {second_name:<15} {'Speedup':<15}")
        print("-" * 80)
        print(f"{'Avg Median':<20} {avg_first_median:>10.2f}μs {avg_second_median:>10.2f}μs {median_speedup:>10.2f}x")
        print(f"{'Avg P99':<20} {avg_first_p99:>10.2f}μs {avg_second_p99:>10.2f}μs {p99_speedup:>10.2f}x")
        print(
            f"{'Avg Total Time':<20} {avg_first_total / 1_000_000:>10.6f}s {avg_second_total / 1_000_000:>10.6f}s {total_speedup:>10.2f}x")
        print(f"\n {second_name} is {median_speedup:.2f}x faster (median, {word_count} words)")

    print("\n" + "=" * 80)

    # Assertions - check all runs
    for config_result in all_config_results:
        for run_data in config_result['runs']:
            first_mismatches = [
                c for c in run_data['first_results']["combinations"]
                if not c.get("matches_expected", True)
            ]
            second_mismatches = [
                c for c in run_data['second_results']["combinations"]
                if not c.get("matches_expected", True)
            ]

            assert len(first_mismatches) == 0, \
                f"{first_name} implementation has {len(first_mismatches)} mismatches in {config_result['config_path']}"
            assert len(second_mismatches) == 0, \
                f"{second_name} implementation has {len(second_mismatches)} mismatches in {config_result['config_path']}"
