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
    "data/deny_check_config_100.json",
    "data/deny_check_config_200.json",
]
RUNS_PER_CONFIG = 1
FIRST_IMPL = DenyListPlugin
SECOND_IMPL = DenyListPluginRustRs
THIRD_IMPL = DenyListPluginRust
ALL_IMPLS = [FIRST_IMPL, SECOND_IMPL, THIRD_IMPL]


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
                },
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


def print_markdown_table(
    all_config_results: List[Dict[str, Any]],
    impls: List[Type[Plugin]],
):
    """Print results in Markdown table format similar to README.

    Args:
        all_config_results: Aggregated benchmark results per config.
        impls: List of implementation classes (e.g., ALL_IMPLS). First impl is used as baseline for speedup calculations.
    """
    print("\n" + "=" * 80)
    print("MARKDOWN TABLE OUTPUT (for README)")
    print("=" * 80)

    impl_names = [impl.__name__ for impl in impls]

    # Build header dynamically: first impl is baseline, others show speedup vs baseline
    header_parts = ["Config Size"]
    separator_parts = [":----------"]
    for i, name in enumerate(impl_names):
        if i == 0:
            header_parts.append(f"{name} Median")
            separator_parts.append(":---------------")
        else:
            header_parts.append(f"{name}")
            header_parts.append("Speedup")
            separator_parts.append(":------------------")
            separator_parts.append(":---------")

    print("\n### Performance Comparison\n")
    print("| " + " | ".join(header_parts) + " |")
    print("| " + " | ".join(separator_parts) + " |")

    for config_result in all_config_results:
        word_count = config_result["word_count"]
        runs = config_result["runs"]

        # Aggregate results across all runs - dynamic based on impls
        all_impl_medians = {impl.__name__: [] for impl in impls}

        for run_data in runs:
            for impl in impls:
                impl_name = impl.__name__
                impl_results = run_data[impl_name]
                medians = [
                    c["timings"]["median_us"] for c in impl_results["combinations"]
                ]
                all_impl_medians[impl_name].append(statistics.median(medians))

        # Calculate averages
        avg_medians = {
            name: statistics.mean(vals) for name, vals in all_impl_medians.items()
        }

        # First impl is baseline for speedup calculations
        baseline_median = avg_medians[impl_names[0]]

        # Build row dynamically
        row_parts = [f"{word_count:<11}"]
        for i, name in enumerate(impl_names):
            if i == 0:
                row_parts.append(f"{avg_medians[name]:>14.2f}μs")
            else:
                speedup = (
                    baseline_median / avg_medians[name] if avg_medians[name] > 0 else 0
                )
                row_parts.append(f"{avg_medians[name]:>14.2f}μs")
                row_parts.append(f"{speedup:>8.2f}x")

        print("| " + " | ".join(row_parts) + " |")

    print("\n" + "=" * 80)


@pytest.mark.asyncio
async def test_benchmark_comparison():
    """Benchmark comparison with config - runs all configs multiple times"""

    impl_names = [impl.__name__ for impl in ALL_IMPLS]

    print("\n" + "=" * 80)
    print(f"DENY CHECK BENCHMARK - {len(impl_names)} Implementation Comparison")
    print("=" * 80)
    print(f"Configs: {len(CONFIG_FILES)} files x {RUNS_PER_CONFIG} runs each")
    print(f"Warmup Runs: {WARMUP_RUNS}")
    print(f"Benchmark Runs: {BENCHMARK_RUNS}")
    print(f"Implementations: {', '.join(impl_names)}")
    print("=" * 80)

    # Store all results for final summary
    all_config_results = []

    for config_path in CONFIG_FILES:
        config = load_config(config_path)

        # Calculate actual word count from config
        word_count = sum(
            len(deny_list["words"]) for deny_list in config["deny_word_lists"]
        )

        print(f"\n{'=' * 80}")
        print(f"CONFIG: {config_path} ({word_count} words)")
        print(f"{'=' * 80}")

        # Run each config RUNS_PER_CONFIG times
        config_run_results = []

        for run_num in range(1, RUNS_PER_CONFIG + 1):
            print(
                f"\n--- Run {run_num}/{RUNS_PER_CONFIG} for {word_count} words config ---"
            )

            run_results = {"run": run_num}

            # Benchmark all implementations
            for impl in ALL_IMPLS:
                impl_name = impl.__name__
                print(f"\nBenchmarking {impl_name} implementation...")
                plugins = create_plugin_instances(config, impl)
                results = await benchmark_plugin(
                    plugins,
                    config["sample_texts"],
                    config,
                )
                run_results[impl_name] = results

            config_run_results.append(run_results)

        # Store results for this config
        all_config_results.append(
            {
                "config_path": config_path,
                "word_count": word_count,
                "config": config,
                "runs": config_run_results,
            }
        )

    # Print final summary for all configs
    print("\n" + "=" * 80)
    print("FINAL SUMMARY - ALL CONFIGURATIONS")
    print("=" * 80)

    for config_result in all_config_results:
        word_count = config_result["word_count"]
        config = config_result["config"]
        runs = config_result["runs"]

        print(f"\n{'=' * 80}")
        print(f"Configuration: {word_count} words")
        print(f"{'=' * 80}")

        # Calculate sample text sizes for this config
        sample_text_sizes = [len(sample["text"]) for sample in config["sample_texts"]]
        if sample_text_sizes:
            print(
                f"Sample Text Sizes: min={min(sample_text_sizes)}, max={max(sample_text_sizes)}, avg={sum(sample_text_sizes) // len(sample_text_sizes)}"
            )
            print("-" * 80)

        # Aggregate results across all runs for all implementations
        all_impl_medians = {impl.__name__: [] for impl in ALL_IMPLS}
        all_impl_p99s = {impl.__name__: [] for impl in ALL_IMPLS}
        all_impl_totals = {impl.__name__: [] for impl in ALL_IMPLS}

        for run_data in runs:
            for impl in ALL_IMPLS:
                impl_name = impl.__name__
                impl_results = run_data[impl_name]

                medians = [c["timings"]["median_us"] for c in impl_results["combinations"]]
                p99s = [c["timings"]["p99_us"] for c in impl_results["combinations"]]

                all_impl_medians[impl_name].append(statistics.median(medians))
                all_impl_p99s[impl_name].append(statistics.median(p99s))
                all_impl_totals[impl_name].append(impl_results["total_time_us"])

        # Calculate averages for all implementations
        avg_medians = {
            name: statistics.mean(vals) for name, vals in all_impl_medians.items()
        }
        avg_p99s = {
            name: statistics.mean(vals) for name, vals in all_impl_p99s.items()
        }
        avg_totals = {
            name: statistics.mean(vals) for name, vals in all_impl_totals.items()
        }

        # Calculate dynamic column widths based on header and value widths
        # Header width for each impl column: max(len(name), width of formatted values)
        # Value formats: "{avg_medians[name]:>10.2f}μs" (12 chars), "{avg_p99s[name]:>10.2f}μs" (12 chars), "{avg_totals[name]/1_000_000:>10.6f}s" (11 chars)
        metric_col_width = 20  # Width for the "Metric" column
        impl_col_widths = []
        for name in impl_names:
            # Value width: max of header name length and formatted value width (12 chars for median/p99, 11 for total)
            value_width = max(len(name), 12)
            impl_col_widths.append(value_width)

        # Print comparison table
        print(f"Runs: {RUNS_PER_CONFIG}")
        header = f"{'Metric':<{metric_col_width}}"
        for i, name in enumerate(impl_names):
            header += f" {name:<{impl_col_widths[i]}}"
        print(header)
        separator_width = metric_col_width + sum(impl_col_widths) + len(impl_names)
        print("-" * separator_width)

        # Median row
        median_row = f"{'Avg Median':<{metric_col_width}}"
        for i, name in enumerate(impl_names):
            median_row += f" {avg_medians[name]:>{impl_col_widths[i]}.2f}μs"
        print(median_row)

        # P99 row
        p99_row = f"{'Avg P99':<{metric_col_width}}"
        for i, name in enumerate(impl_names):
            p99_row += f" {avg_p99s[name]:>{impl_col_widths[i]}.2f}μs"
        print(p99_row)

        # Total Time row
        total_row = f"{'Avg Total Time':<{metric_col_width}}"
        for i, name in enumerate(impl_names):
            total_row += f" {avg_totals[name] / 1_000_000:>{impl_col_widths[i]}.6f}s"
        print(total_row)

        # Speedup calculations (relative to first implementation - Python)
        first_name = impl_names[0]
        print(f"\nSpeedup vs {first_name}:")
        for name in impl_names[1:]:
            median_speedup = (
                avg_medians[first_name] / avg_medians[name]
                if avg_medians[name] > 0
                else 0
            )
            p99_speedup = (
                avg_p99s[first_name] / avg_p99s[name] if avg_p99s[name] > 0 else 0
            )
            total_speedup = (
                avg_totals[first_name] / avg_totals[name]
                if avg_totals[name] > 0
                else 0
            )
            print(
                f"  {name}: {median_speedup:.2f}x (median), {p99_speedup:.2f}x (p99), {total_speedup:.2f}x (total)"
            )

    # Print Markdown table for README
    print_markdown_table(all_config_results, ALL_IMPLS)

    print("\n" + "=" * 80)

    # Assertions - check all runs for all implementations
    for config_result in all_config_results:
        for run_data in config_result["runs"]:
            for impl in ALL_IMPLS:
                impl_name = impl.__name__
                mismatches = [
                    c
                    for c in run_data[impl_name]["combinations"]
                    if not c.get("matches_expected", True)
                ]

                assert (
                    len(mismatches) == 0
                ), f"{impl_name} implementation has {len(mismatches)} mismatches in {config_result['config_path']}"
