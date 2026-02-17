# Deny Words Plugin

A high-performance deny list filtering plugin for MCP Gateway that detects prohibited words in prompts. This plugin provides both Python and Rust
implementations, with the Rust version offering significant performance improvements through efficient pattern matching algorithms.

## Overview

The Deny Words Plugin scans incoming prompts for prohibited words or phrases before they are processed. When a deny word is detected, the plugin
rejects the prompt request, providing an additional security layer for your MCP Gateway deployment.

## Key Features

- **Fast Pattern Matching**: Rust implementation uses optimized pattern-matching algorithms for efficient word detection
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
uv run pytest -s -v tests/test_benchmark_comparison.py
```

### Performance Comparison

> **Note:** The benchmark table below was generated with pytest. To regenerate manually, run:
> ```bash
> uv run pytest -s -v tests/test_benchmark_comparison.py
> ```
> The Markdown table output will be printed to stdout.

<!-- BENCHMARK_TABLE_START -->
| Config Size | DenyListPlugin Median | DenyListPluginRustRs | Speedup | DenyListPluginRust | Speedup |
| :---------- | :--------------- | :------------------ | :--------- | :------------------ | :--------- |
| 10          |           7.65μs |           2.04μs |     3.74x |           1.98μs |     3.86x |
| 100         |         554.44μs |          16.07μs |    34.50x |           5.15μs |   107.66x |
| 200         |        1226.32μs |          16.90μs |    72.56x |          18.20μs |    67.36x |
<!-- BENCHMARK_TABLE_END -->

**Key Findings:**
- Both Rust implementations are consistently faster across all configuration sizes
- DenyListPluginRust **aho-corasick** excels with medium-sized lists
- DenyListPluginRustRs **regex crate (RegexSet)** shows more consistent scaling
- For high-throughput applications, the Rust implementation can reduce latency by an order of magnitude

## Prerequisites

- Python 3.12+
- Rust toolchain (for building Rust implementation)
- uv package manager

## Build and Install

```bash
# Install Python dependencies
uv sync

# Build Rust extension
make build-release

# Run tests
uv run pytest -s -v
```

## Usage

### Gateway Configuration

Add the plugin to your MCP Gateway configuration with a deny word list:

```yaml
# In your gateway config block
plugins:
  - name: deny_filter
    plugin: plugins.deny_filter.deny_rust_rs.DenyListPluginRustRs
    hooks:
      - prompt_pre_fetch
    priority: 100
    config:
      words:
        - spam
        - scam
        - phishing
```

Or with multiple deny word lists:

```yaml
plugins:
  - name: deny_filter_main
    plugin: plugins.deny_filter.deny_rust_rs.DenyListPluginRustRs
    hooks:
      - prompt_pre_fetch
    priority: 100
    config:
      words:
        - prohibited_word_1
        - prohibited_word_2
```

Enable the plugin for a specific route:

```yaml
routes:
  - path: /chat
    plugins:
      - deny_filter_main
```

### Example Payloads

Prompt without deny words - passes through:
```json
{
  "prompt_id": "test_prompt",
  "args": {"text": "This is a clean message"}
}
```

Prompt containing deny word - rejected:
```json
{
  "prompt_id": "test_prompt",
  "args": {"text": "This message contains prohibited content"}
}
```

## Testing

```bash
# Run all tests
uv run pytest -s -v
cargo test

# Run benchmark comparison
uv run pytest tests/test_benchmark_comparison.py -s -v
```

### Python Bindings

The Rust code is exposed to Python using PyO3, providing:
- Zero-copy data access where possible
- Async/await support
- Pythonic error handling
- Type safety across the boundary

## License

Apache-2.0
