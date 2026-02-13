"""Pytest benchmark suite for deny_check prompt_pre_fetch functionality.

This module provides comprehensive benchmarks comparing Python and Rust implementations
of the DenyListPlugin using pytest-benchmark.

The benchmark automatically displays a performance comparison summary at the end,
showing which implementation is faster and by how much.

Usage:
    # Run all benchmarks with automatic comparison (recommended)
    uv run pytest tests/test_benchmark_deny.py

    # Run only Python benchmarks
    uv run pytest tests/test_benchmark_deny.py -k python

    # Run only Rust benchmarks
    uv run pytest tests/test_benchmark_deny.py -k rust

    # Run with specific config file
    uv run pytest tests/test_benchmark_deny.py --benchmark-config=deny_check_config_50.json

Advanced Options:
    # Save results for later comparison
    uv run pytest tests/test_benchmark_deny.py --benchmark-save=baseline

    # Compare with saved baseline
    uv run pytest tests/test_benchmark_deny.py --benchmark-compare=baseline

    # Generate detailed comparison report
    uv run pytest tests/test_benchmark_deny.py --benchmark-compare
"""
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest

# Add parent directory to path to import plugins
sys.path.insert(0, str(Path(__file__).parent.parent))

from plugins.deny_filter.deny import DenyListPlugin
from plugins.deny_filter.deny_rust import DenyListPluginRust
from mcpgateway.plugins.framework import Plugin, PluginConfig, PluginContext
from mcpgateway.plugins.framework.hooks.prompts import (
    PromptHookType,
    PromptPrehookPayload,
)
from mcpgateway.plugins.framework.models import GlobalContext


@pytest.fixture(scope="session")
def benchmark_config() -> Dict[str, Any]:
    """Load benchmark configuration from JSON file.
    
    Returns:
        Dictionary containing deny word lists and sample texts.
    """
    # Use tests/data directory for test configuration files
    config_file = Path(__file__).parent / "data" / "deny_check_config_200.json"
    
    with open(config_file, "r") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def plugin_context() -> PluginContext:
    """Create a reusable plugin context for benchmarks.
    
    Returns:
        PluginContext instance with global context.
    """
    gctx = GlobalContext(request_id="benchmark-test")
    return PluginContext(global_context=gctx)


@pytest.fixture(scope="session")
def python_plugins(benchmark_config: Dict[str, Any]) -> List[tuple[str, Plugin]]:
    """Create Python DenyListPlugin instances for each deny word list.
    
    Args:
        benchmark_config: Loaded configuration dictionary.
        
    Returns:
        List of (name, plugin) tuples.
    """
    plugins = []
    
    for deny_list in benchmark_config["deny_word_lists"]:
        plugin_config = PluginConfig(
            name=f"deny_filter_{deny_list['name']}",
            kind="plugins.deny_filter.deny.DenyListPlugin",
            hooks=[PromptHookType.PROMPT_PRE_FETCH],
            priority=100,
            config={"words": deny_list["words"]},
        )
        
        plugin = DenyListPlugin(config=plugin_config)
        plugins.append((deny_list["name"], plugin, deny_list["words"]))
    
    return plugins


@pytest.fixture(scope="session")
def rust_plugins(benchmark_config: Dict[str, Any]) -> List[tuple[str, Plugin]]:
    """Create Rust DenyListPlugin instances for each deny word list.
    
    Args:
        benchmark_config: Loaded configuration dictionary.
        
    Returns:
        List of (name, plugin) tuples.
    """
    plugins = []
    
    for deny_list in benchmark_config["deny_word_lists"]:
        plugin_config = PluginConfig(
            name=f"deny_filter_{deny_list['name']}",
            kind="plugins.deny_filter.deny_rust.DenyListPluginRust",
            hooks=[PromptHookType.PROMPT_PRE_FETCH],
            priority=100,
            config={"words": deny_list["words"]},
        )
        
        plugin = DenyListPluginRust(config=plugin_config)
        plugins.append((deny_list["name"], plugin, deny_list["words"]))
    
    return plugins


def generate_test_cases(benchmark_config: Dict[str, Any], plugins: List[tuple]) -> List[tuple]:
    """Generate test case combinations of plugins and sample texts.
    
    Args:
        benchmark_config: Configuration with sample texts.
        plugins: List of (name, plugin, words) tuples.
        
    Returns:
        List of (plugin_name, plugin, sample_name, sample_text, expected_block) tuples.
    """
    test_cases = []
    
    for plugin_name, plugin, deny_words in plugins:
        for sample in benchmark_config["sample_texts"]:
            # Determine if this specific plugin should block this text
            expected_block = any(word in sample["text"] for word in deny_words)
            
            test_cases.append(
                (plugin_name, plugin, sample["name"], sample["text"], expected_block)
            )
    
    return test_cases


@pytest.fixture(scope="session")
def python_test_cases(benchmark_config: Dict[str, Any], python_plugins: List[tuple]) -> List[tuple]:
    """Generate test cases for Python implementation."""
    return generate_test_cases(benchmark_config, python_plugins)


@pytest.fixture(scope="session")
def rust_test_cases(benchmark_config: Dict[str, Any], rust_plugins: List[tuple]) -> List[tuple]:
    """Generate test cases for Rust implementation."""
    return generate_test_cases(benchmark_config, rust_plugins)


def pytest_generate_tests(metafunc):
    """Dynamically generate test parameters for benchmark tests."""
    if "python_test_case" in metafunc.fixturenames:
        # Load config from tests/data directory
        config_path = Path(__file__).parent / "data" / "deny_check_config_200.json"
        
        with open(config_path, "r") as f:
            config = json.load(f)
        
        # Generate test cases
        test_cases = []
        ids = []
        
        for deny_list in config["deny_word_lists"]:
            for sample in config["sample_texts"]:
                expected_block = any(word in sample["text"] for word in deny_list["words"])
                test_cases.append((deny_list, sample, expected_block))
                ids.append(f"{deny_list['name']}-{sample['name']}")
        
        metafunc.parametrize("python_test_case", test_cases, ids=ids)
    
    elif "rust_test_case" in metafunc.fixturenames:
        # Load config from tests/data directory
        config_path = Path(__file__).parent / "data" / "deny_check_config_200.json"
        
        with open(config_path, "r") as f:
            config = json.load(f)
        
        # Generate test cases
        test_cases = []
        ids = []
        
        for deny_list in config["deny_word_lists"]:
            for sample in config["sample_texts"]:
                expected_block = any(word in sample["text"] for word in deny_list["words"])
                test_cases.append((deny_list, sample, expected_block))
                ids.append(f"{deny_list['name']}-{sample['name']}")
        
        metafunc.parametrize("rust_test_case", test_cases, ids=ids)


def test_python_prompt_pre_fetch(benchmark, plugin_context: PluginContext, python_test_case):
    """Benchmark Python DenyListPlugin.prompt_pre_fetch() execution.
    
    This test benchmarks each combination of deny word list and sample text,
    ensuring that the blocking behavior matches expectations.
    """
    deny_list, sample, expected_block = python_test_case
    
    # Create plugin
    plugin_config = PluginConfig(
        name=f"deny_filter_{deny_list['name']}",
        kind="plugins.deny_filter.deny.DenyListPlugin",
        hooks=[PromptHookType.PROMPT_PRE_FETCH],
        priority=100,
        config={"words": deny_list["words"]},
    )
    plugin = DenyListPlugin(config=plugin_config)
    
    # Create payload
    payload = PromptPrehookPayload(
        prompt_id="test",
        args={"text": sample["text"]},
    )
    
    # Benchmark the async function with reused event loop
    import asyncio
    
    # Create event loop ONCE before benchmarking
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    def run_check():
        # Reuse the same event loop for all iterations
        return loop.run_until_complete(plugin.prompt_pre_fetch(payload, plugin_context))
    
    result = benchmark(run_check)
    
    # Clean up event loop ONCE after benchmarking
    loop.close()
    
    # Verify blocking behavior
    actual_blocked = result is None or (
        hasattr(result, "violation") and result.violation is not None
    )
    assert actual_blocked == expected_block, (
        f"Expected block={expected_block}, got {actual_blocked} "
        f"for {deny_list['name']} x {sample['name']}"
    )


def test_rust_prompt_pre_fetch(benchmark, plugin_context: PluginContext, rust_test_case):
    """Benchmark Rust DenyListPlugin.prompt_pre_fetch() execution.
    
    This test benchmarks each combination of deny word list and sample text,
    ensuring that the blocking behavior matches expectations.
    """
    deny_list, sample, expected_block = rust_test_case
    
    # Create plugin
    plugin_config = PluginConfig(
        name=f"deny_filter_{deny_list['name']}",
        kind="plugins.deny_filter.deny_rust.DenyListPluginRust",
        hooks=[PromptHookType.PROMPT_PRE_FETCH],
        priority=100,
        config={"words": deny_list["words"]},
    )
    plugin = DenyListPluginRust(config=plugin_config)
    
    # Create payload
    payload = PromptPrehookPayload(
        prompt_id="test",
        args={"text": sample["text"]},
    )
    
    # Benchmark the async function with reused event loop
    import asyncio
    
    # Create event loop ONCE before benchmarking
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    def run_check():
        # Reuse the same event loop for all iterations
        return loop.run_until_complete(plugin.prompt_pre_fetch(payload, plugin_context))
    
    result = benchmark(run_check)
    
    # Clean up event loop ONCE after benchmarking
    loop.close()
    
    # Verify blocking behavior
    actual_blocked = result is None or (
        hasattr(result, "violation") and result.violation is not None
    )
    assert actual_blocked == expected_block, (
        f"Expected block={expected_block}, got {actual_blocked} "
        f"for {deny_list['name']} x {sample['name']}"
    )


def test_benchmark_summary(benchmark_config: Dict[str, Any]):
    """Display benchmark configuration summary.
    
    This test provides context about what is being benchmarked.
    """
    num_deny_lists = len(benchmark_config["deny_word_lists"])
    num_samples = len(benchmark_config["sample_texts"])
    total_combinations = num_deny_lists * num_samples
    
    print(f"\n{'='*80}")
    print("BENCHMARK CONFIGURATION")
    print(f"{'='*80}")
    print(f"Deny Word Lists: {num_deny_lists}")
    print(f"Sample Texts: {num_samples}")
    print(f"Total Combinations: {total_combinations}")
    print(f"{'='*80}\n")
    
    # This test always passes - it's just for information
    assert True
