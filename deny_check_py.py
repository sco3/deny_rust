"""Python plugin-based deny check implementation using prehook approach."""

# Standard
import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any

# First-Party
from mcpgateway.plugins.framework import PluginConfig, PluginContext
from mcpgateway.plugins.framework.hooks.prompts import (
    PromptHookType,
    PromptPrehookPayload,
)
from mcpgateway.plugins.framework.models import GlobalContext

from plugins.deny_filter.deny import DenyListPlugin

# Suppress plugin logging output for cleaner performance metrics
logging.getLogger("plugins.deny_filter.deny").setLevel(logging.ERROR)
logging.getLogger("mcpgateway").setLevel(logging.ERROR)


async def run_test_combination(
    deny_list_name: str,
    deny_words: list[str],
    sample_name: str,
    sample_text: str,
    expected_block: bool,
    gctx: GlobalContext,
) -> tuple[str, float, bool]:
    """Run a single test combination using plugin prehook.

    Args:
        deny_list_name: Name of the deny list being tested
        deny_words: List of words to deny
        sample_name: Name of the sample text
        sample_text: The text to test
        expected_block: Whether this text should be blocked
        gctx: Global context for the plugin

    Returns:
        Tuple of (test_name, execution_time, was_blocked)
    """
    plugin_cfg = PluginConfig(
        name=f"deny_test_{deny_list_name}",
        kind="plugins.deny_filter.deny.DenyListPlugin",
        hooks=[PromptHookType.PROMPT_PRE_FETCH],
        priority=100,
        config={"words": deny_words},
    )
    ctx = PluginContext(global_context=gctx)
    plugin = DenyListPlugin(config=plugin_cfg)

    payload = PromptPrehookPayload(
        prompt_id=f"test-{deny_list_name}-{sample_name}", args={"text": sample_text}
    )

    start_time = time.perf_counter()
    result = await plugin.prompt_pre_fetch(payload, ctx)
    elapsed_time = time.perf_counter() - start_time

    was_blocked = result.violation is not None

    test_name = f"{deny_list_name} + {sample_name}"
    return test_name, elapsed_time, was_blocked


async def run_test_suite_py(config: dict[str, Any], count: int = 1) -> dict[str, Any]:
    """Run the test suite using Python plugin approach.

    Args:
        config: Configuration dictionary with deny_word_lists and sample_texts
        count: Number of times to run each test combination

    Returns:
        Dictionary with summary and detailed results
    """
    from deny_check import PerformanceStats

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
    stats = PerformanceStats()

    # Run all combinations
    total_combinations = len(deny_word_lists) * len(sample_texts)
    current_test = 0

    # Print wall time before starting tests
    start_wall_time = time.time()
    print(
        f"Starting tests at: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_wall_time))}"
    )
    print()

    for deny_list in deny_word_lists:
        deny_list_name = deny_list["name"]
        deny_words = deny_list["words"]

        for sample in sample_texts:
            sample_name = sample["name"]
            sample_text = sample["text"]

            # Determine if this specific combination should block
            # A text should only block if it contains a word from the current deny list
            should_block_for_this_list = any(word in sample_text for word in deny_words)

            # Run the test 'count' times
            for _ in range(count):
                test_name, elapsed_time, was_blocked = await run_test_combination(
                    deny_list_name,
                    deny_words,
                    sample_name,
                    sample_text,
                    should_block_for_this_list,
                    gctx,
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
