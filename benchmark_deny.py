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


def print_summary(results: Dict[str, Any]):
    """Print a summary of benchmark results.
    
    Args:
        results: Dictionary containing benchmark results.
    """
    # Overall statistics - only median and p99
    all_medians = [c['timings']['median_us'] for c in results['combinations']]
    all_p99s = [c['timings']['p99_us'] for c in results['combinations']]
    
    total_time_s = results['total_time_us'] / 1_000_000
    
    # Check for mismatches
    mismatches = [c for c in results['combinations'] if not c.get('matches_expected', True)]
    total_tests = len(results['combinations'])
    passed_tests = total_tests - len(mismatches)
    
    print("\n" + "="*80)
    print("BENCHMARK RESULTS")
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


async def main(plugin_type: Type[Plugin] = DenyListPluginRust, 
               warmup_runs: int = 5,
               benchmark_runs: int = 100):
    """Main benchmark function.
    
    Args:
        plugin_type: The plugin class type to instantiate (defaults to DenyListPluginRust).
        warmup_runs: Number of warmup runs before benchmarking.
        benchmark_runs: Number of benchmark runs for timing.
    """
    print("="*80)
    print("DENY CHECK BENCHMARK - prompt_pre_fetch")
    print("="*80)
    print(f"Plugin Type: {plugin_type.__name__}")
    print(f"Warmup Runs: {warmup_runs}")
    print(f"Benchmark Runs: {benchmark_runs}")
    print("="*80)
    
    #print("\nLoading deny_check_config.json...")
    config = load_config()
    
    #print(f"\nFound {len(config['deny_word_lists'])} deny word lists")
    #print(f"Found {len(config['sample_texts'])} sample texts")
    
    #print(f"\nCreating {plugin_type.__name__} instances...")
    plugins = create_plugin_instances(config, plugin_type)
    
    print(f"\nSuccessfully created {len(plugins)} plugin instances")
    
    # Run benchmarks
    print("\nStarting benchmarks...")
    results = await benchmark_prompt_pre_fetch(
        plugins, 
        config['sample_texts'],
        config,
        warmup_runs=warmup_runs,
        benchmark_runs=benchmark_runs
    )
    
    # Print summary
    print_summary(results)
    
    # Save results to JSON
    output_file = "deny_check_results.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nDetailed results saved to: {output_file}")


if __name__ == "__main__":
    # Parse command line arguments for customization
    import argparse
    
    parser = argparse.ArgumentParser(description='Benchmark deny_check prompt_pre_fetch')
    parser.add_argument('--warmup', type=int, default=0, help='Number of warmup runs (default: 5)')
    parser.add_argument('--runs', type=int, default=10000, help='Number of benchmark runs (default: 100)')
    
    args = parser.parse_args()
    
#class DenyWarningFilter(logging.Filter):
#def filter(self, record):
#        return not (record.levelname == 'WARNING' and 'Deny word detected' in record.getMessage())

    #deny_logger = logging.getLogger("plugins.deny_filter.deny")
    #deny_logger.addFilter(DenyWarningFilter())
    logging.getLogger("plugins.deny_filter.deny").setLevel(logging.ERROR)

    
    
    asyncio.run(main(warmup_runs=args.warmup, benchmark_runs=args.runs,plugin_type=DenyListPlugin))
    asyncio.run(main(warmup_runs=args.warmup, benchmark_runs=args.runs,plugin_type=DenyListPluginRust))
