#!/usr/bin/env -S uv run 
"""Unified deny filter performance test - supports both Python and Rust implementations."""

# Standard
import argparse
import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any, TypedDict

# Suppress plugin logging output for cleaner performance metrics
class DenyWarningFilter(logging.Filter):
    def filter(self, record):
        return not (record.levelname == 'WARNING' and 'Deny word detected' in record.getMessage())

deny_logger = logging.getLogger("plugins.deny_filter.deny")
deny_logger.addFilter(DenyWarningFilter())
logging.getLogger("plugins.deny_filter").setLevel(logging.CRITICAL)


class TestResult(TypedDict):
    """Type definition for test result."""

    test_name: str
    execution_time_us: float
    blocked: bool
    expected_block: bool
    correct: bool


class PerformanceStats:
    """Track performance statistics for test runs."""

    def __init__(self) -> None:
        self.total_tests: int = 0
        self.total_time: float = 0.0
        self.min_time: float = float("inf")
        self.max_time: float = 0.0
        self.blocked_count: int = 0
        self.passed_count: int = 0
        self.results: list[TestResult] = []

    def add_result(
        self, test_name: str, execution_time: float, blocked: bool, expected_block: bool
    ) -> None:
        """Add a test result."""
        self.total_tests += 1
        self.total_time += execution_time
        self.min_time = min(self.min_time, execution_time)
        self.max_time = max(self.max_time, execution_time)

        if blocked:
            self.blocked_count += 1
        else:
            self.passed_count += 1

        correct = blocked == expected_block
        self.results.append(
            {
                "test_name": test_name,
                "execution_time_us": execution_time * 1_000_000,
                "blocked": blocked,
                "expected_block": expected_block,
                "correct": correct,
            }
        )

    def get_summary(self) -> dict[str, Any]:
        """Get summary statistics."""
        avg_time = self.total_time / self.total_tests if self.total_tests > 0 else 0
        correct_count = sum(1 for r in self.results if r["correct"])
        accuracy = (
            (correct_count / self.total_tests * 100) if self.total_tests > 0 else 0
        )

        return {
            "total_tests": self.total_tests,
            "total_time_seconds": self.total_time,
            "average_time_us": avg_time * 1_000_000,
            "min_time_us": self.min_time * 1_000_000 if self.min_time != float("inf") else 0,
            "max_time_us": self.max_time * 1_000_000,
            "blocked_count": self.blocked_count,
            "passed_count": self.passed_count,
            "accuracy_percent": accuracy,
            "correct_predictions": correct_count,
        }


def print_results(result_data: dict[str, Any]) -> None:
    """Print test results in a formatted way.

    Args:
        result_data (dict[str, Any]): Dictionary containing summary, detailed_results, and timing info.
    """
    summary = result_data["summary"]
    results = result_data["detailed_results"]
    wall_time_elapsed = result_data["wall_time"]

    # Print summary
    print("\n" + "=" * 80)
    print("PERFORMANCE SUMMARY")
    print("=" * 80)

    overhead = wall_time_elapsed - summary["total_time_seconds"]
    overhead_percent = (
        (overhead / wall_time_elapsed * 100) if wall_time_elapsed > 0 else 0
    )

    print(f"Total tests run:        {summary['total_tests']}")
    print(f"Wall clock time:        {wall_time_elapsed:.6f} seconds")
    print(
        f"Pure execution time:    {summary['total_time_seconds']:.6f} seconds (sum of individual test times)"
    )
    print(
        f"Overhead time:          {overhead:.6f} seconds ({overhead_percent:.1f}% - setup, plugin init, etc.)"
    )
    print(f"Average time per test:  {summary['average_time_us']:.2f} μs")
    print(f"Min time:               {summary['min_time_us']:.2f} μs")
    print(f"Max time:               {summary['max_time_us']:.2f} μs")
    print(f"Tests blocked:          {summary['blocked_count']}")
    print(f"Tests passed:           {summary['passed_count']}")
    print(f"Accuracy:               {summary['accuracy_percent']:.1f}%")
    print(
        f"Correct predictions:    {summary['correct_predictions']}/{summary['total_tests']}"
    )

    # Find slowest tests
    print("\n" + "=" * 80)
    print("TOP 5 SLOWEST TESTS")
    print("=" * 80)
    sorted_results = sorted(results, key=lambda x: x["execution_time_us"], reverse=True)
    for i, result in enumerate(sorted_results[:5], 1):
        print(f"{i}. {result['test_name']:50s} | {result['execution_time_us']:9.2f}μs")

    # Count mismatches
    mismatches = [r for r in results if not r["correct"]]
    if mismatches:
        print("\n" + "=" * 80)
        print("MISMATCHES (Unexpected Results)")
        print("=" * 80)

        # Count by type
        false_positives = sum(
            1 for r in mismatches if r["blocked"] and not r["expected_block"]
        )
        false_negatives = sum(
            1 for r in mismatches if not r["blocked"] and r["expected_block"]
        )

        print(f"Total mismatches:       {len(mismatches)}")
        print(f"False positives:        {false_positives} (blocked when should pass)")
        print(f"False negatives:        {false_negatives} (passed when should block)")
        print(f"\nNote: Detailed mismatch list saved to JSON file")

    # Save detailed results to JSON
    output_path = Path(__file__).parent / "deny_check_results.json"
    output_data = {"summary": summary, "detailed_results": results}

    with open(output_path, "w") as f:
        json.dump(output_data, f, indent=2)

    print(f"\n{'=' * 80}")
    print(f"Detailed results saved to: {output_path}")
    print("=" * 80)


# ============================================================================
# PYTHON PLUGIN IMPLEMENTATION
# ============================================================================

async def run_test_combination_py(
    deny_list_name: str,
    plugin: Any,
    sample_name: str,
    sample_text: str,
    expected_block: bool,
    ctx: Any,
) -> tuple[str, float, bool]:
    """Run a single test combination using Python plugin prehook.

    Args:
        deny_list_name: Name of the deny list being tested
        plugin: Pre-initialized DenyListPlugin instance
        sample_name: Name of the sample text
        sample_text: The text to test
        expected_block: Whether this text should be blocked
        ctx: Plugin context for the plugin

    Returns:
        Tuple of (test_name, execution_time, was_blocked)
    """
    from mcpgateway.plugins.framework.hooks.prompts import PromptPrehookPayload

    payload = PromptPrehookPayload(
        prompt_id=f"test-{deny_list_name}-{sample_name}", args={"text": sample_text}
    )

    start_time = time.perf_counter()
    result = await plugin.prompt_pre_fetch(payload, ctx)
    elapsed_time = time.perf_counter() - start_time

    was_blocked = result.violation is not None

    test_name = f"{deny_list_name} + {sample_name}"
    return test_name, elapsed_time, was_blocked


async def run_test_suite_py(config: dict[str, Any], count: int = 1, config_class: type = None, plugin_class: type = None) -> dict[str, Any]:
    """Run the test suite using Python plugin approach.

    Args:
        config: Configuration dictionary with deny_word_lists and sample_texts
        count: Number of times to run each test combination
        config_class: Config class type
        plugin_class: Plugin class type

    Returns:
        Dictionary with summary and detailed results
    """
    from mcpgateway.plugins.framework import PluginContext
    from mcpgateway.plugins.framework.hooks.prompts import PromptHookType
    from mcpgateway.plugins.framework.models import GlobalContext
    
    # Use default classes if not provided
    if config_class is None:
        from mcpgateway.plugins.framework import PluginConfig
        config_class = PluginConfig
    
    if plugin_class is None:
        from plugins.deny_filter.deny import DenyListPlugin
        plugin_class = DenyListPlugin
    
    ConfigClass = config_class
    PluginClass = plugin_class

    deny_word_lists = config["deny_word_lists"]
    sample_texts = config["sample_texts"]

    print("=" * 80)
    print("DENY FILTER PERFORMANCE TEST (Python Plugin Mode)")
    print("=" * 80)
    print(f"Deny word lists: {len(deny_word_lists)}")
    print(f"Sample texts: {len(sample_texts)}")
    print(f"Total combinations: {len(deny_word_lists) * len(sample_texts)}")
    print(f"Iterations per combination: {count}")
    print(f"Total test runs: {len(deny_word_lists) * len(sample_texts) * count}")
    print("=" * 80)
    print()

    gctx = GlobalContext(request_id="deny-test-batch")
    ctx = PluginContext(global_context=gctx)
    
    # Create plugin instances once for each deny list (outside the test loops)
    print("Creating plugin instances...")
    deny_list_plugins = {}
    for deny_list in deny_word_lists:
        deny_list_name = deny_list["name"]
        deny_words = deny_list["words"]
        plugin_cfg = ConfigClass(
            name=f"deny_test_{deny_list_name}",
            kind=f"{plugin_class.__module__}.{plugin_class.__name__}",
            hooks=[PromptHookType.PROMPT_PRE_FETCH],
            priority=100,
            config={"words": deny_words},
        )
        deny_list_plugins[deny_list_name] = PluginClass(config=plugin_cfg)
    print(f"Created {len(deny_list_plugins)} plugin instances")
    print()
    
    # Warmup phase - 13000 tests
    print("=" * 80)
    print("WARMUP PHASE - Running 13000 tests (not counted in benchmark)")
    print("=" * 80)
    warmup_start = time.time()
    warmup_count = 0
    warmup_target = 13000
    
    while warmup_count < warmup_target:
        for deny_list in deny_word_lists:
            deny_list_name = deny_list["name"]
            deny_words = deny_list["words"]
            plugin = deny_list_plugins[deny_list_name]

            for sample in sample_texts:
                if warmup_count >= warmup_target:
                    break
                    
                sample_name = sample["name"]
                sample_text = sample["text"]
                should_block_for_this_list = any(word in sample_text for word in deny_words)

                await run_test_combination_py(
                    deny_list_name,
                    plugin,
                    sample_name,
                    sample_text,
                    should_block_for_this_list,
                    ctx,
                )
                warmup_count += 1
                
                if warmup_count % 500 == 0:
                    print(f"Warmup progress: {warmup_count}/{warmup_target} tests ({warmup_count*100//warmup_target}%)")
            
            if warmup_count >= warmup_target:
                break
    
    warmup_elapsed = time.time() - warmup_start
    print(f"Warmup completed: {warmup_count} tests in {warmup_elapsed:.2f} seconds")
    print("=" * 80)
    print()

    stats = PerformanceStats()

    # Run all combinations
    total_combinations = len(deny_word_lists) * len(sample_texts)
    current_test = 0

    # Print wall time before starting tests
    start_wall_time = time.time()
    print(
        f"Starting benchmark at: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_wall_time))}"
    )
    print()

    for deny_list in deny_word_lists:
        deny_list_name = deny_list["name"]
        deny_words = deny_list["words"]
        plugin = deny_list_plugins[deny_list_name]

        for sample in sample_texts:
            sample_name = sample["name"]
            sample_text = sample["text"]

            # Determine if this specific combination should block
            should_block_for_this_list = any(word in sample_text for word in deny_words)

            # Run the test 'count' times
            for _ in range(count):
                test_name, elapsed_time, was_blocked = await run_test_combination_py(
                    deny_list_name,
                    plugin,
                    sample_name,
                    sample_text,
                    should_block_for_this_list,
                    ctx,
                )

                stats.add_result(
                    test_name, elapsed_time, was_blocked, should_block_for_this_list
                )

            # Show progress every 10 combinations
            current_test += 1
            if current_test % 10 == 0 or current_test == total_combinations:
                print(
                    f"Progress: {current_test}/{total_combinations} combinations tested ({current_test*100//total_combinations}%)"
                )

    # Print wall time after completing tests
    end_wall_time = time.time()
    print()
    print(
        f"Completed tests at: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(end_wall_time))}"
    )
    print(f"Total wall time: {end_wall_time - start_wall_time:.2f} seconds")

    summary = stats.get_summary()
    return {
        "summary": summary,
        "detailed_results": stats.results,
        "wall_time": end_wall_time - start_wall_time,
        "start_time": start_wall_time,
        "end_time": end_wall_time,
    }


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

async def run_test_suite_py_mode(count: int = 1, config_class: type = None, plugin_class: type = None) -> None:
    """Run the test suite using Python plugin mode.

    Args:
        count: Number of times to run each test combination
        config_class: Config class type
        plugin_class: Plugin class type
    """
    # Load configuration
    config_path = Path(__file__).parent / "deny_check_config.json"
    with open(config_path, "r") as f:
        config = json.load(f)

    result_data = await run_test_suite_py(config, count, config_class, plugin_class)
    print_results(result_data)


def run_test_suite_rs_mode(count: int = 1) -> None:
    """Run the test suite using Rust scan mode.

    Args:
        count: Number of times to run each test combination
    """
    # Load configuration
    config_path = Path(__file__).parent / "deny_check_config.json"
    with open(config_path, "r") as f:
        config = json.load(f)

    result_data = run_test_suite_rs(config, count)
    print_results(result_data)


def main() -> None:
    """Parse arguments and run tests."""
    from mcpgateway.plugins.framework import PluginConfig
    from plugins.deny_filter.deny import DenyListPlugin
    from plugins.deny_filter.deny_rust import DenyListPluginRust
    
    parser = argparse.ArgumentParser(
        description="Test deny filter performance with configurable iterations and modes"
    )
    parser.add_argument(
        "--count",
        type=int,
        default=1000,
        help="Number of times to run each test combination (default: 1)",
    )
    args = parser.parse_args()

    if args.count < 1:
        print("Error: --count must be at least 1")
        return

    asyncio.run(run_test_suite_py_mode(count=args.count, config_class=PluginConfig, plugin_class=DenyListPlugin))


if __name__ == "__main__":
    main()