#!/usr/bin/env -S uv run
# -*- coding: utf-8 -*-
"""Benchmark script for deny_check prompt_pre_fetch functionality.

This script reads deny_check_config.json, creates DenyListPlugin instances
for every element of deny_word_lists, and benchmarks prompt_pre_fetch execution
for each sample_text against each plugin instance.
"""
import logging
import asyncio
import json
import sys
import time
import statistics
from pathlib import Path
from typing import List, Dict, Any, Type

# Add parent directory to path to import plugins
sys.path.insert(0, str(Path(__file__).parent.parent))

from plugins.deny_filter.deny_rust import DenyListPluginRust
from plugins.deny_filter.deny import DenyListPlugin
from mcpgateway.plugins.framework import PluginConfig, Plugin, PluginContext
from mcpgateway.plugins.framework.hooks.prompts import PromptHookType, PromptPrehookPayload
from mcpgateway.plugins.framework.models import GlobalContext


def load_config(config_path: str = "deny_check_config.json") -> Dict[str, Any]:
    """Load the deny check configuration from JSON file.
    
    Args:
        config_path: Path to the configuration file.
        
    Returns:
        Dictionary containing the configuration.
    """
    config_file = Path(config_path)
    if not config_file.exists():
        # Try relative to script location
        config_file = Path(__file__).parent / config_path
    
    with open(config_file, 'r') as f:
        return json.load(f)


def create_plugin_instances(config: Dict[str, Any], plugin_type: Type[Plugin]) -> List[Plugin]:
    """Create DenyListPlugin instances for each deny word list.
    
    Args:
        config: The loaded configuration dictionary.
        plugin_type: The plugin class type to instantiate.
        
    Returns:
        List of plugin instances.
    """
    plugins = []
    
    for deny_list in config['deny_word_lists']:
        # Create PluginConfig for each deny word list
        plugin_config = PluginConfig(
            name=f"deny_filter_{deny_list['name']}",
            kind=f"{plugin_type.__module__}.{plugin_type.__name__}",
            hooks=[PromptHookType.PROMPT_PRE_FETCH],
            priority=100,
            config={
                "words": deny_list['words']
            }
        )
        
        # Create plugin instance
        plugin = plugin_type(config=plugin_config)
        plugins.append((deny_list['name'], plugin))
        
        #print(f"Created plugin for '{deny_list['name']}' with {len(deny_list['words'])} words")
    
    return plugins


async def benchmark_prompt_pre_fetch(
    plugins: List[tuple[str, Plugin]], 
    sample_texts: List[Dict[str, Any]],
    config: Dict[str, Any],
    warmup_runs: int = 5,
    benchmark_runs: int = 100
) -> Dict[str, Any]:
    """Benchmark prompt_pre_fetch execution for all combinations.
    
    Args:
        plugins: List of (name, plugin) tuples.
        sample_texts: List of sample text dictionaries.
        warmup_runs: Number of warmup runs before benchmarking.
        benchmark_runs: Number of benchmark runs for timing.
        
    Returns:
        Dictionary containing benchmark results.
    """
    # Create context once
    gctx = GlobalContext(request_id="deny-benchmark")
    ctx = PluginContext(global_context=gctx)
    
    results = {
        "total_combinations": len(plugins) * len(sample_texts),
        "warmup_runs": warmup_runs,
        "benchmark_runs": benchmark_runs,
        "total_time_us": 0.0,
        "combinations": []
    }
    
    total_combinations = len(plugins) * len(sample_texts)
    current = 0
    
    for plugin_name, plugin in plugins:
        # Get the deny words for this specific plugin
        plugin_deny_words = None
        for deny_list in config['deny_word_lists']:
            if deny_list['name'] == plugin_name:
                plugin_deny_words = deny_list['words']
                break
        
        for sample in sample_texts:
            current += 1
            #print(f"\n[{current}/{total_combinations}] Benchmarking: {plugin_name} x {sample['name']}")
            
            # Calculate if THIS specific plugin should block THIS specific text
            # by checking if any of THIS plugin's deny words are in the text
            should_block_for_this_combination = any(word in sample['text'] for word in plugin_deny_words)
            
            # Create payload
            payload = PromptPrehookPayload(
                prompt_id="benchmark_test",
                args={"text": sample['text']}
            )
            
            # Warmup runs
            #print(f"  Warmup ({warmup_runs} runs)...", end=" ", flush=True)
            for _ in range(warmup_runs):
                await plugin.prompt_pre_fetch(payload, ctx)
            #print("Done")
            
            # Benchmark runs
            #print(f"  Benchmark ({benchmark_runs} runs)...", end=" ", flush=True)
            timings_us = []
            actual_blocked = None
            
            for i in range(benchmark_runs):
                start = time.perf_counter()
                result = await plugin.prompt_pre_fetch(payload, ctx)
                elapsed = time.perf_counter() - start
                timings_us.append(elapsed * 1_000_000)  # Convert to microseconds
                
                # Capture blocking result from first run
                if i == 0:
                    # Check if result indicates blocking (result is None or has a violation)
                    actual_blocked = result is None or (hasattr(result, 'violation') and result.violation is not None)
            
            #print("Done")
            
            # Calculate statistics
            timings_us.sort()
            median = statistics.median(timings_us)
            p99_index = int(len(timings_us) * 0.99)
            p99 = timings_us[p99_index]
            mean = statistics.mean(timings_us)
            min_time = min(timings_us)
            max_time = max(timings_us)
            
            # Calculate total time for this combination
            total_time_combination = sum(timings_us)
            
            expected_block = should_block_for_this_combination
            matches_expected = actual_blocked == expected_block
            
            combination_result = {
                "plugin_name": plugin_name,
                "sample_name": sample['name'],
                "sample_text_length": len(sample['text']),
                "expected_block": expected_block,
                "actual_blocked": actual_blocked,
                "matches_expected": matches_expected,
                "timings": {
                    "median_us": round(median, 2),
                    "p99_us": round(p99, 2),
                    "mean_us": round(mean, 2),
                    "min_us": round(min_time, 2),
                    "max_us": round(max_time, 2),
                    "total_us": round(total_time_combination, 2)
                }
            }
            
            results["combinations"].append(combination_result)
            results["total_time_us"] += total_time_combination
            
            # Results collected silently
    
    return results


def print_summary(results: Dict[str, Any], plugin_name: str = ""):
    """Print a summary of benchmark results.
    
    Args:
        results: Dictionary containing benchmark results.
        plugin_name: Name of the plugin being benchmarked.
    """
    # Overall statistics - median, p99, and max
    all_medians = [c['timings']['median_us'] for c in results['combinations']]
    all_p99s = [c['timings']['p99_us'] for c in results['combinations']]
    all_maxs = [c['timings']['max_us'] for c in results['combinations']]
    
    total_time_s = results['total_time_us'] / 1_000_000
    
    # Check for mismatches
    mismatches = [c for c in results['combinations'] if not c.get('matches_expected', True)]
    total_tests = len(results['combinations'])
    passed_tests = total_tests - len(mismatches)
    
    print("\n" + "="*80)
    print(f"BENCHMARK RESULTS - {plugin_name}")
    print("="*80)
    print(f"Median:     {statistics.median(all_medians):.2f}μs")
    print(f"P99:        {statistics.median(all_p99s):.2f}μs")
    print(f"Max:        {max(all_maxs):.2f}μs")
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
    """Print comparison between Python and Rust implementations.
    
    Args:
        py_results: Benchmark results for Python implementation.
        rust_results: Benchmark results for Rust implementation.
    """
    py_medians = [c['timings']['median_us'] for c in py_results['combinations']]
    rust_medians = [c['timings']['median_us'] for c in rust_results['combinations']]
    
    py_p99s = [c['timings']['p99_us'] for c in py_results['combinations']]
    rust_p99s = [c['timings']['p99_us'] for c in rust_results['combinations']]
    
    py_maxs = [c['timings']['max_us'] for c in py_results['combinations']]
    rust_maxs = [c['timings']['max_us'] for c in rust_results['combinations']]
    
    py_median = statistics.median(py_medians)
    rust_median = statistics.median(rust_medians)
    
    py_p99 = statistics.median(py_p99s)
    rust_p99 = statistics.median(rust_p99s)
    
    py_max = max(py_maxs)
    rust_max = max(rust_maxs)
    
    py_total = py_results['total_time_us']
    rust_total = rust_results['total_time_us']
    
    # Calculate speedup coefficients
    median_speedup = py_median / rust_median if rust_median > 0 else 0
    p99_speedup = py_p99 / rust_p99 if rust_p99 > 0 else 0
    max_speedup = py_max / rust_max if rust_max > 0 else 0
    total_speedup = py_total / rust_total if rust_total > 0 else 0
    
    print("\n" + "="*80)
    print("PYTHON vs RUST COMPARISON")
    print("="*80)
    print(f"{'Metric':<20} {'Python':<15} {'Rust':<15} {'Speedup':<15}")
    print("-"*80)
    print(f"{'Median':<20} {py_median:>10.2f}μs {rust_median:>10.2f}μs {median_speedup:>10.2f}x")
    print(f"{'P99':<20} {py_p99:>10.2f}μs {rust_p99:>10.2f}μs {p99_speedup:>10.2f}x")
    print(f"{'Max':<20} {py_max:>10.2f}μs {rust_max:>10.2f}μs {max_speedup:>10.2f}x")
    print(f"{'Total Time':<20} {py_total/1_000_000:>10.6f}s {rust_total/1_000_000:>10.6f}s {total_speedup:>10.2f}x")
    print("="*80)
    print(f"\n🚀 Rust is {median_speedup:.2f}x faster than Python (median)")
    print(f"🚀 Rust is {p99_speedup:.2f}x faster than Python (p99)")
    print(f"🚀 Rust is {max_speedup:.2f}x faster than Python (max)")
    print(f"🚀 Rust is {total_speedup:.2f}x faster than Python (total time)")
    print("="*80)


async def run_benchmark(plugin_type: Type[Plugin],
                       warmup_runs: int,
                       benchmark_runs: int,
                       config_path: str) -> Dict[str, Any]:
    """Run benchmark for a specific plugin type.
    
    Args:
        plugin_type: The plugin class type to instantiate.
        warmup_runs: Number of warmup runs before benchmarking.
        benchmark_runs: Number of benchmark runs for timing.
        config_path: Path to the JSON configuration file.
        
    Returns:
        Dictionary containing benchmark results.
    """
    print("="*80)
    print(f"BENCHMARKING: {plugin_type.__name__}")
    print("="*80)
    print(f"Warmup Runs: {warmup_runs}")
    print(f"Benchmark Runs: {benchmark_runs}")
    print("="*80)
    
    config = load_config(config_path)
    plugins = create_plugin_instances(config, plugin_type)
    
    print(f"\nSuccessfully created {len(plugins)} plugin instances")
    print("\nStarting benchmarks...")
    
    results = await benchmark_prompt_pre_fetch(
        plugins, 
        config['sample_texts'],
        config,
        warmup_runs=warmup_runs,
        benchmark_runs=benchmark_runs
    )
    
    print_summary(results, plugin_type.__name__)
    
    return results


async def main(warmup_runs: int = 5,
               benchmark_runs: int = 100,
               config_path: str = "deny_check_config.json"):
    """Main benchmark function that compares Python and Rust implementations.
    
    Args:
        warmup_runs: Number of warmup runs before benchmarking.
        benchmark_runs: Number of benchmark runs for timing.
        config_path: Path to the JSON configuration file.
    """
    print("\n" + "="*80)
    print("DENY CHECK BENCHMARK - Python vs Rust Comparison")
    print("="*80)
    
    # Run Python benchmark
    py_results = await run_benchmark(
        DenyListPlugin,
        warmup_runs,
        benchmark_runs,
        config_path
    )
    
    # Run Rust benchmark
    rust_results = await run_benchmark(
        DenyListPluginRust,
        warmup_runs,
        benchmark_runs,
        config_path
    )
    
    # Print comparison
    print_comparison(py_results, rust_results)
    
    # Save results to JSON
    output_data = {
        "python": py_results,
        "rust": rust_results,
        "comparison": {
            "median_speedup": statistics.median([c['timings']['median_us'] for c in py_results['combinations']]) / 
                            statistics.median([c['timings']['median_us'] for c in rust_results['combinations']]),
            "p99_speedup": statistics.median([c['timings']['p99_us'] for c in py_results['combinations']]) / 
                         statistics.median([c['timings']['p99_us'] for c in rust_results['combinations']]),
            "total_speedup": py_results['total_time_us'] / rust_results['total_time_us']
        }
    }
    
    output_file = "deny_check_results.json"
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)
    print(f"\nDetailed results saved to: {output_file}")


if __name__ == "__main__":
    # Parse command line arguments for customization
    import argparse
    
    parser = argparse.ArgumentParser(description='Benchmark deny_check prompt_pre_fetch')
    parser.add_argument('--warmup', type=int, default=3000, help='Number of warmup runs (default: 5)')
    parser.add_argument('--runs', type=int, default=30000, help='Number of benchmark runs (default: 100)')
    parser.add_argument('--data', type=str, default='deny_check_config.json', help='JSON config file name (default: deny_check_config.json)')
    
    args = parser.parse_args()
    
#class DenyWarningFilter(logging.Filter):
#def filter(self, record):
#        return not (record.levelname == 'WARNING' and 'Deny word detected' in record.getMessage())

    #deny_logger = logging.getLogger("plugins.deny_filter.deny")
    #deny_logger.addFilter(DenyWarningFilter())
    logging.getLogger("plugins.deny_filter.deny").setLevel(logging.ERROR)
    
    asyncio.run(main(warmup_runs=args.warmup, benchmark_runs=args.runs, config_path=args.data))
