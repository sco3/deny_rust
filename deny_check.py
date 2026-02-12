"""check how deny works - main entry point with mode selection"""

# Standard
import argparse
import asyncio
import json
import logging
from pathlib import Path
from typing import Any, TypedDict

# Suppress plugin logging output for cleaner performance metrics
logging.getLogger("plugins.deny_filter.deny").setLevel(logging.ERROR)
logging.getLogger("mcpgateway").setLevel(logging.ERROR)


class TestResult(TypedDict):
    """Type definition for test result."""

    test_name: str
    execution_time_ms: float
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
                "execution_time_ms": execution_time * 1000,
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
            "average_time_ms": avg_time * 1000,
            "min_time_ms": self.min_time * 1000 if self.min_time != float("inf") else 0,
            "max_time_ms": self.max_time * 1000,
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
    print(f"Average time per test:  {summary['average_time_ms']:.3f} ms")
    print(f"Min time:               {summary['min_time_ms']:.3f} ms")
    print(f"Max time:               {summary['max_time_ms']:.3f} ms")
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
    sorted_results = sorted(results, key=lambda x: x["execution_time_ms"], reverse=True)
    for i, result in enumerate(sorted_results[:5], 1):
        print(f"{i}. {result['test_name']:50s} | {result['execution_time_ms']:7.3f}ms")

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


async def run_test_suite_py_mode(count: int = 1) -> None:
    """Run the test suite using Python plugin mode.

    Args:
        count: Number of times to run each test combination
    """
    from deny_check_py import run_test_suite_py

    # Load configuration
    config_path = Path(__file__).parent / "deny_check_config.json"
    with open(config_path, "r") as f:
        config = json.load(f)

    result_data = await run_test_suite_py(config, count)
    print_results(result_data)


def run_test_suite_rs_mode(count: int = 1) -> None:
    """Run the test suite using Rust scan mode.

    Args:
        count: Number of times to run each test combination
    """
    from deny_check_rs import run_test_suite_rs

    # Load configuration
    config_path = Path(__file__).parent / "deny_check_config.json"
    with open(config_path, "r") as f:
        config = json.load(f)

    result_data = run_test_suite_rs(config, count)
    print_results(result_data)


def main() -> None:
    """Parse arguments and run tests."""
    parser = argparse.ArgumentParser(
        description="Test deny filter performance with configurable iterations and modes"
    )
    parser.add_argument(
        "--count",
        type=int,
        default=1,
        help="Number of times to run each test combination (default: 1)",
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["py", "rs"],
        default="py",
        help="Mode to use: 'py' for Python plugin (prehook), 'rs' for Rust (scan method) (default: py)",
    )
    args = parser.parse_args()

    if args.count < 1:
        print("Error: --count must be at least 1")
        return

    if args.mode == "py":
        asyncio.run(run_test_suite_py_mode(count=args.count))
    elif args.mode == "rs":
        run_test_suite_rs_mode(count=args.count)
    else:
        print(f"Error: Unknown mode '{args.mode}'. Use 'py' or 'rs'.")
        return


if __name__ == "__main__":
    main()
