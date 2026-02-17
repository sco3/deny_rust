# Deny Words Plugin

A high-performance deny list filtering plugin for MCP Gateway that detects prohibited words in prompts. This plugin provides both Python and Rust
implementations, with the Rust version offering significant performance improvements through efficient pattern matching algorithms.

## Overview

The Deny Words Plugin scans incoming prompts for prohibited words or phrases before they are processed. When a deny word is detected, the plugin
rejects the prompt request, providing an additional security layer for your MCP Gateway deployment.

## Key Features

- **Fast Pattern Matching**: Rust implementation uses optimized algorithms for efficient word detection
- **Multiple Implementation Options**:
    - `deny.DenyListPlugin` - Pure Python, easy to debug, good for small word lists
    - `deny_rust.DenyListPluginRust` - Python with Rust bindings (aho-corasick crate)
    - `deny_rust_rs.DenyListPluginRustRs` - Python with Rust bindings (regex crate - RegexSet)
- **Configurable Deny Lists**: Support for multiple deny word lists with different priorities
- **Pre-Hook Integration**: Operates at the `prompt_pre_fetch` hook stage
- **Comprehensive Testing**: Includes benchmark tests demonstrating performance characteristics

## Performance Benefits

The Rust implementation provides substantial performance improvements over pure Python:

### Benchmark Results

Run benchmarks with:
```bash
uv pytest -s -v tests/test_benchmark_comparison.py
```

### Performance Comparison

| Config Size | Python Median | Rust (aho-corasick) | Speedup | Rust (regex) | Speedup |
| :---------- | :------------ | :------------------ | :------ | :----------- | :------ |
| 10 words    | 7.51µs        | 1.96µs              | 3.83x   | 2.00µs       | 3.80x   |
| 100 words   | 553.41µs      | 5.18µs              | 106.84x | 16.09µs      | 34.76x  |
| 200 words   | 1225.17µs     | 18.12µs             | 67.61x  | 16.85µs      | 72.90x  |

**Key Findings:**
- Both Rust implementations are consistently faster across all configuration sizes
- **aho-corasick** excels with medium-sized lists (100 words: 106.84x speedup)
- **regex crate (RegexSet)** shows more consistent scaling (72.90x at 200 words vs 67.61x for aho-corasick)
- For high-throughput applications, the Rust implementation can reduce latency by an order of magnitude

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

```bash
# Run all tests
uv pytest -s -v
cargo test

# Run benchmark comparison
uv pytest tests/test_benchmark_comparison.py -s -v
```

### Python Bindings

The Rust code is exposed to Python using PyO3, providing:
- Zero-copy data access where possible
- Async/await support
- Pythonic error handling
- Type safety across the boundary

## License

Apache-2.0
