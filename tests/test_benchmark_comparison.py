#!/usr/bin/env python3
"""
Pytest-based benchmark comparison between Python and Rust deny list implementations.
This test always displays detailed output regardless of pytest flags.
"""
import pytest
import asyncio
import json
import statistics
from pathlib import Path
from typing import List, Dict, Any, Type

from plugins.deny_filter.deny_rust import DenyListPluginRust
from plugins.deny_filter.deny import DenyListPlugin
from mcpgateway.plugins.framework import PluginConfig, Plugin, PluginContext
from mcpgateway.plugins.framework.hooks.prompts import PromptHookType, PromptPrehookPayload
from mcpgateway.plugins.framework.models import GlobalContext

WARMUP_RUNS=3000
BENCHMARK_RUNS=10000
CONFIG_PATH="data/deny_check_config_200.json"


def load_config(config_path: str) -> Dict[str, Any]:
    """Load the deny check configuration from JSON file."""
    config_file = Path(config_path)
    if not config_file.exists():
        config_file = Path(__file__).parent / config_path
    
    with open(config_file, 'r') as f:
        return json.load(f)


def create_plugin_instances(config: Dict[str, Any], plugin_type: Type[Plugin]) -> List[tuple]:
    """Create plugin instances for each deny word list."""
    plugins = []
    
    for deny_list in config['deny_word_lists']:
        plugin_config = PluginConfig(
            name=f"deny_filter_{deny_list['name']}",
            kind=f"{plugin_type.__module__}.{plugin_type.__name__}",
            hooks=[PromptHookType.PROMPT_PRE_FETCH],
            priority=100,
            config={"words": deny_list['words']}
        )
        
        plugin = plugin_type(config=plugin_config)
        plugins.append((deny_list['name'], plugin))
    
    return plugins


async def benchmark_plugin(
    plugins: List[tuple[str, Plugin]], 
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
        "combinations": []
    }
    
    for plugin_name, plugin in plugins:
        plugin_deny_words = None
        for deny_list in config['deny_word_lists']:
            if deny_list['name'] == plugin_name:
                plugin_deny_words = deny_list['words']
                break
        
        for sample in sample_texts:
            should_block = any(word in sample['text'] for word in plugin_deny_words)
            
            payload = PromptPrehookPayload(
                prompt_id="benchmark_test",
                args={"text": sample['text']}
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
                    actual_blocked = result is None or (hasattr(result, 'violation') and result.violation is not None)
            
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
                "sample_name": sample['name'],
                "sample_text_length": len(sample['text']),
                "expected_block": should_block,
                "actual_blocked": actual_blocked,
                "matches_expected": actual_blocked == should_block,
                "timings": {
                    "median_us": round(median, 2),
                    "p99_us": round(p99, 2),
                    "mean_us": round(mean, 2),
                    "min_us": round(min_time, 2),
                    "total_us": round(total_time_combination, 2)
                }
            }
            
            results["combinations"].append(combination_result)
            results["total_time_us"] += total_time_combination
    
    return results


def print_summary(results: Dict[str, Any], plugin_name: str):
    """Print benchmark summary - always visible."""
    all_medians = [c['timings']['median_us'] for c in results['combinations']]
    all_p99s = [c['timings']['p99_us'] for c in results['combinations']]
    
    total_time_s = results['total_time_us'] / 1_000_000
    
    mismatches = [c for c in results['combinations'] if not c.get('matches_expected', True)]
    total_tests = len(results['combinations'])
    passed_tests = total_tests - len(mismatches)
    
    print("\n" + "="*80)
    print(f"BENCHMARK RESULTS - {plugin_name}")
    print("="*80)
    print(f"Median:     {statistics.median(all_medians):.2f}μs")
    print(f"P99:        {statistics.median(all_p99s):.2f}μs")
    print(f"Total Time: {total_time_s:.6f}s ({results['total_time_us']:.2f}μs)")
    print("="*80)
    print(f"\nTest Results: {passed_tests}/{total_tests} passed")
    
    if mismatches:
        print("\n" + "="*80)
        print("MISMATCHES DETECTED")
        print("="*80)
        for mismatch in mismatches:
            print(f"\nPlugin: {mismatch['plugin_name']}")
            print(f"Sample: {mismatch['sample_name']}")
            print(f"Expected Block: {mismatch['expected_block']}")
            print(f"Actual Blocked: {mismatch['actual_blocked']}")
            print("-" * 40)
    else:
        print("\n✓ All tests passed - actual behavior matches expected!")
    print("="*80)


def print_comparison(py_results: Dict[str, Any], rust_results: Dict[str, Any]):
    """Print comparison between Python and Rust - always visible."""
    py_medians = [c['timings']['median_us'] for c in py_results['combinations']]
    rust_medians = [c['timings']['median_us'] for c in rust_results['combinations']]
    
    py_p99s = [c['timings']['p99_us'] for c in py_results['combinations']]
    rust_p99s = [c['timings']['p99_us'] for c in rust_results['combinations']]
    
    py_median = statistics.median(py_medians)
    rust_median = statistics.median(rust_medians)
    
    py_p99 = statistics.median(py_p99s)
    rust_p99 = statistics.median(rust_p99s)
    
    py_total = py_results['total_time_us']
    rust_total = rust_results['total_time_us']
    
    median_speedup = py_median / rust_median if rust_median > 0 else 0
    p99_speedup = py_p99 / rust_p99 if rust_p99 > 0 else 0
    total_speedup = py_total / rust_total if rust_total > 0 else 0
    
    print("\n" + "="*80)
    print("PYTHON vs RUST COMPARISON")
    print("="*80)
    print(f"{'Metric':<20} {'Python':<15} {'Rust':<15} {'Speedup':<15}")
    print("-"*80)
    print(f"{'Median':<20} {py_median:>10.2f}μs {rust_median:>10.2f}μs {median_speedup:>10.2f}x")
    print(f"{'P99':<20} {py_p99:>10.2f}μs {rust_p99:>10.2f}μs {p99_speedup:>10.2f}x")
    print(f"{'Total Time':<20} {py_total/1_000_000:>10.6f}s {rust_total/1_000_000:>10.6f}s {total_speedup:>10.2f}x")
    print("="*80)
    print(f"\n🚀 Rust is {median_speedup:.2f}x faster than Python (median)")
    print(f"🚀 Rust is {p99_speedup:.2f}x faster than Python (p99)")
    print(f"🚀 Rust is {total_speedup:.2f}x faster than Python (total time)")
    print("="*80 + "\n")



@pytest.mark.asyncio
async def test_benchmark_comparison():
    """Benchmark comparison with config"""
    config_path = CONFIG_PATH
    warmup_runs = 5
    benchmark_runs = 100
    
    print("\n" + "="*80)
    print("DENY CHECK BENCHMARK - Python vs Rust Comparison")
    print("="*80)
    print(f"Config: {config_path}")
    print(f"Warmup Runs: {warmup_runs}")
    print(f"Benchmark Runs: {benchmark_runs}")
    print("="*80)
    
    config = load_config(config_path)
    
    # Python benchmark
    print("\nBenchmarking Python implementation...")
    py_plugins = create_plugin_instances(config, DenyListPlugin)
    py_results = await benchmark_plugin(
        py_plugins, 
        config['sample_texts'],
        config,
        warmup_runs=warmup_runs,
        benchmark_runs=benchmark_runs
    )
    print_summary(py_results, "DenyListPlugin (Python)")
    
    # Rust benchmark
    print("\nBenchmarking Rust implementation...")
    rust_plugins = create_plugin_instances(config, DenyListPluginRust)
    rust_results = await benchmark_plugin(
        rust_plugins, 
        config['sample_texts'],
        config,
        warmup_runs=warmup_runs,
        benchmark_runs=benchmark_runs
    )
    print_summary(rust_results, "DenyListPluginRust (Rust)")
    
    # Comparison
    print_comparison(py_results, rust_results)
    
    # Assertions
    py_mismatches = [c for c in py_results['combinations'] if not c.get('matches_expected', True)]
    rust_mismatches = [c for c in rust_results['combinations'] if not c.get('matches_expected', True)]
    
    assert len(py_mismatches) == 0, f"Python implementation has {len(py_mismatches)} mismatches"
    assert len(rust_mismatches) == 0, f"Rust implementation has {len(rust_mismatches)} mismatches"

# Made with Bob
