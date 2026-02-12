"""Rust-based deny check implementation using scan method approach."""

# Standard
import time
from typing import Any

# Third-party
import deny_rust


def run_test_combination_rs(
    deny_list_name: str,
    deny_words: list[str],
    sample_name: str,
    sample_text: str,
    expected_block: bool,
) -> tuple[str, float, bool]:
    """Run a single test combination using Rust prompt_pre_fetch method.

    Args:
        deny_list_name: Name of the deny list being tested
        deny_words: List of words to deny
        sample_name: Name of the sample text
        sample_text: The text to test
        expected_block: Whether this text should be blocked

    Returns:
        Tuple of (test_name, execution_time, was_blocked)
    """
    # Create Rust-based deny list configuration and plugin
    config = deny_rust.DenyListConfig(words=deny_words)
    deny_list = deny_rust.DenyListPlugin(config=config)

    # Use prompt_pre_fetch method - matches Python plugin approach
    # Pass the text as args dictionary
    start_time = time.perf_counter()
    result = deny_list.prompt_pre_fetch({"text": sample_text})
    elapsed_time = time.perf_counter() - start_time

    # Check if blocked
    # Result has a violation field - if not None, text was blocked
    was_blocked = result.violation is not None

    test_name = f"{deny_list_name} + {sample_name}"
    return test_name, elapsed_time, was_blocked


def run_test_suite_rs(config: dict[str, Any], count: int = 1) -> dict[str, Any]:
    """Run the test suite using Rust scan method approach.

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
    print("DENY FILTER PERFORMANCE TEST (Rust Scan Mode)")
    print("=" * 80)
    print(f"Deny word lists: {len(deny_word_lists)}")
    print(f"Sample texts: {len(sample_texts)}")
    print(f"Total combinations: {len(deny_word_lists) * len(sample_texts)}")
    print(f"Iterations per combination: {count}")
    print(f"Total test runs: {len(deny_word_lists) * len(sample_texts) * count}")
    print("=" * 80)
    print()

    # Warmup phase - 3000 tests
    print("=" * 80)
    print("WARMUP PHASE - Running 3000 tests (not counted in benchmark)")
    print("=" * 80)
    warmup_start = time.time()
    warmup_count = 0
    warmup_target = 3000
    
    while warmup_count < warmup_target:
        for deny_list in deny_word_lists:
            deny_list_name = deny_list["name"]
            deny_words = deny_list["words"]

            for sample in sample_texts:
                if warmup_count >= warmup_target:
                    break
                    
                sample_name = sample["name"]
                sample_text = sample["text"]
                should_block_for_this_list = any(word in sample_text for word in deny_words)

                run_test_combination_rs(
                    deny_list_name,
                    deny_words,
                    sample_name,
                    sample_text,
                    should_block_for_this_list,
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

        for sample in sample_texts:
            sample_name = sample["name"]
            sample_text = sample["text"]

            # Determine if this specific combination should block
            # A text should only block if it contains a word from the current deny list
            should_block_for_this_list = any(word in sample_text for word in deny_words)

            # Run the test 'count' times
            for _ in range(count):
                test_name, elapsed_time, was_blocked = run_test_combination_rs(
                    deny_list_name,
                    deny_words,
                    sample_name,
                    sample_text,
                    should_block_for_this_list,
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
