# Deny Words Plugin

A high-performance deny list filtering plugin for MCP Gateway that detects prohibited words in prompts. This plugin provides both Python and Rust
implementations, with the Rust version offering significant performance improvements through efficient pattern matching algorithms.

## Overview

The Deny Words Plugin scans incoming prompts for prohibited words or phrases before they are processed. When a deny word is detected, the plugin
rejects the prompt request, providing an additional security layer for your MCP Gateway deployment.

## Key Features

- Fast Pattern Matching: Rust implementation uses optimized algorithms for efficient word detection
- Multiple Implementation Options:
    - Pure Python implementation (DenyListPlugin)
    - Python with Rust bindings (DenyListPluginRust)
    - Pure Rust implementation (DenyListPluginRustRs)
- Configurable Deny Lists: Support for multiple deny word lists with different priorities
- Pre-Hook Integration: Operates at the prompt_pre_fetch hook stage
- Comprehensive Testing: Includes benchmark tests demonstrating performance characteristics

## Performance Benefits

The Rust implementation provides substantial performance improvements over pure Python:

### Benchmark Results

Run benchmarks with:
   ```
   uv pytest -s -v tests/test_benchmark_comparison.py
   ```

## Performance Comparison

### Test data

Modify your configuration or update the deny word lists in test data files:

```bash
   tests/data/deny_check_config_10.json   # 10 words
   tests/data/deny_check_config_20.json   # 20 words
   tests/data/deny_check_config_100.json  # 100 words
   tests/data/deny_check_config_200.json  # 200 words
```
Results:

| Config Size (deny words) | Python Median | Rust Median | Increase |
| :----------------------- | :------------ | :---------- | :------- |
| 3                        | 2.27µs        | 1.58µs      | 1.44x    |
| 20                       | 11.73µs       | 2.07µs      | 5.67x    |
| 100                      | 556.36µs      | 5.20µs      | 107x     |
| 200                      | 1226.27µs     | 18.10µs     | 68x      |

Key Findings:
- Rust implementation is consistently faster across all configuration sizes
- Performance advantage increases dramatically with larger deny word lists
- At 100 words: Rust is 107x faster than Python
- At 200 words: Rust maintains 68x speedup over Python

Note: Actual performance depends on text size, word list size, and system specifications

The Rust implementation becomes increasingly advantageous as:
- The number of deny words increases
- The text size grows
- The request volume increases

For high-throughput applications processing thousands of prompts per second, the Rust implementation can reduce latency by an order of magnitude.

### Prerequisites

- Python 3.12+
- Rust toolchain (for building Rust implementation)
- uv package manager

### Build and Install

```bash
# Install Python dependencies
uv sync

# Build Rust extension
make build-release

# Run tests
uv pytest -s -v
```


### Implementation Selection

Choose the implementation that best fits your needs:

- **deny.DenyListPlugin**: Pure Python, easy to debug, good for small word lists
- **deny_rust.DenyListPluginRust**: Hybrid approach with aho-corasic crate
- **deny_rust_rs.DenyListPluginRustRs**: Hybrid approach with regex crate (RegexSet)

## Usage

Once configured, the plugin automatically scans all prompts at the prompt_pre_fetch stage:

```python
# Prompt without deny words - passes through
{
"prompt_id": "test_prompt",
"args": {"text": "This is a clean message"}
}
# ✓ Allowed
```

```python
# Prompt containing deny word - rejected
{
"prompt_id": "test_prompt",
"args": {"text": "This message contains prohibited content"}
}
# ✗ Blocked: "Prompt not allowed (A deny word was found in the prompt)"
```

## Testing

### Run All Tests

```bash

# Run with verbose output
uv pytest -s -v
cargo test
```

### Benchmark Tests

The benchmark suite compares implementations across different configurations:

```bash
# Run comprehensive benchmarks
uv pytest tests/test_benchmark_comparison.py -s -v

# Output includes:
# - Median latency
# - P99 latency
# - Total execution time
# - Speedup factors
# - Performance across different word list sizes
```




### Python Bindings

The Rust code is exposed to Python using PyO3, providing:
- Zero-copy data access where possible
- Async/await support
- Pythonic error handling
- Type safety across the boundary

## License

Apache-2.0
