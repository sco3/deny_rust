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
    - Python with Rust bindings (DenyListPluginRust - aho-corasic crate)
    - Python with Rust bindings (DenyListPluginRustRs - regex crate (RegexSet))
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

### Performance Comparison

#### DenyListPluginRust (aho-corasick crate)

| Config Size (deny words) | Python Median | Rust Median | Speedup  |
| :----------------------- | :------------ | :---------- | :------- |
| 10                       | 7.51µs        | 1.96µs      | 3.83x    |
| 100                      | 553.41µs      | 5.18µs      | 106.84x  |
| 200                      | 1225.17µs     | 18.12µs     | 67.61x   |

#### DenyListPluginRustRs (regex crate - RegexSet)

| Config Size (deny words) | Python Median | Rust Median | Speedup  |
| :----------------------- | :------------ | :---------- | :------- |
| 10                       | 7.62µs        | 2.00µs      | 3.80x    |
| 100                      | 559.13µs      | 16.09µs     | 34.76x   |
| 200                      | 1228.33µs     | 16.85µs     | 72.90x   |

**Key Findings:**
- Both Rust implementations are consistently faster across all configuration sizes
- **aho-corasick** excels with medium-sized lists (100 words: 106.84x speedup)
- **regex crate (RegexSet)** shows more consistent scaling (72.90x at 200 words vs 67.61x for aho-corasick)
- At 10 words, both implementations perform similarly (~3.8x speedup)
- For large deny word lists (200 words), regex crate has slightly better median performance (16.85µs vs 18.12µs)

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

Prompt without deny words - passes through
```json
{
"prompt_id": "test_prompt",
"args": {"text": "This is a clean message"}
}
```

Prompt containing deny word - rejected
```json
{
"prompt_id": "test_prompt",
"args": {"text": "This message contains prohibited content"}
}
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
