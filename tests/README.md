# Benchmark Tests

This directory contains pytest-benchmark tests for comparing Python and Rust implementations of the DenyListPlugin.

## Installation

Install the required dependencies:

```bash
uv sync --dev
```

## Running Benchmarks

### Quick Comparison (Recommended - Default)

Run all benchmarks to see Rust vs Python comparison in one go:
```bash
uv run pytest tests/test_benchmark_deny.py --benchmark-only
```

This will show a comparison table with both implementations side-by-side, displaying:
- Min/Max/Mean execution times
- Standard deviation and median
- Operations per second (OPS)
- Direct performance comparison

### Basic Usage

Run all benchmarks with test output:
```bash
uv run pytest tests/test_benchmark_deny.py -v
```

### Filter by Implementation

Run only Python benchmarks:
```bash
uv run pytest tests/test_benchmark_deny.py -k python -v
```

Run only Rust benchmarks:
```bash
uv run pytest tests/test_benchmark_deny.py -k rust -v
```

### Custom Configuration

Use a different configuration file:
```bash
uv run pytest tests/test_benchmark_deny.py --benchmark-config=deny_check_config_50.json
```

### Benchmark Options

Show benchmark statistics:
```bash
uv run pytest tests/test_benchmark_deny.py --benchmark-only
```

Save benchmark results:
```bash
uv run pytest tests/test_benchmark_deny.py --benchmark-save=baseline
```

Compare with saved baseline:
```bash
uv run pytest tests/test_benchmark_deny.py --benchmark-compare=baseline
```

Generate histogram:
```bash
uv run pytest tests/test_benchmark_deny.py --benchmark-histogram
```

Disable benchmarks (run as normal tests):
```bash
uv run pytest tests/test_benchmark_deny.py --benchmark-disable
```

### Advanced Options

Control benchmark rounds:
```bash
uv run pytest tests/test_benchmark_deny.py --benchmark-warmup=on --benchmark-warmup-iterations=10
```

Set minimum time:
```bash
uv run pytest tests/test_benchmark_deny.py --benchmark-min-time=0.001
```

Sort results:
```bash
uv run pytest tests/test_benchmark_deny.py --benchmark-sort=mean
```

## Output Format

The benchmark results include:
- **Min**: Minimum execution time
- **Max**: Maximum execution time
- **Mean**: Average execution time
- **StdDev**: Standard deviation
- **Median**: Median execution time
- **IQR**: Interquartile range
- **Outliers**: Number of outlier measurements
- **OPS**: Operations per second
- **Rounds**: Number of benchmark rounds
- **Iterations**: Iterations per round

## Comparison Example

```bash
# Save Python baseline
uv run pytest tests/test_benchmark_deny.py -k python --benchmark-save=python_baseline

# Save Rust baseline
uv run pytest tests/test_benchmark_deny.py -k rust --benchmark-save=rust_baseline

# Compare implementations
uv run pytest tests/test_benchmark_deny.py --benchmark-compare=0001,0002 --benchmark-compare-fail=mean:10%
```

## Configuration Files

The benchmark uses JSON configuration files with the following structure:

```json
{
  "deny_word_lists": [
    {
      "name": "list_name",
      "words": ["word1", "word2", ...]
    }
  ],
  "sample_texts": [
    {
      "name": "sample_name",
      "text": "sample text content"
    }
  ]
}
```

Available configurations:
- `deny_check_config.json` - Default configuration
- `deny_check_config_20.json` - 20 words
- `deny_check_config_50.json` - 50 words
- `deny_check_config_100.json` - 100 words
- `deny_check_config_200.json` - 200 words

## CI/CD Integration

Example GitHub Actions workflow:

```yaml
- name: Install uv
  uses: astral-sh/setup-uv@v4
  
- name: Run benchmarks
  run: |
    uv sync --dev
    uv run pytest tests/test_benchmark_deny.py --benchmark-only --benchmark-json=output.json
    
- name: Store benchmark result
  uses: benchmark-action/github-action-benchmark@v1
  with:
    tool: 'pytest'
    output-file-path: output.json
```

## Tips

1. **Consistent Environment**: Run benchmarks on the same machine with minimal background processes
2. **Multiple Runs**: Use `--benchmark-autosave` to automatically save each run
3. **Statistical Significance**: Use `--benchmark-compare-fail` to fail if performance regresses
4. **Profiling**: Combine with `--profile` for detailed profiling
5. **Parallel Execution**: Avoid `-n auto` with benchmarks as it affects timing

## Troubleshooting

### Import Errors

If you get import errors, ensure all dependencies are installed and use `uv run`:
```bash
uv sync --dev
uv run pytest tests/test_benchmark_deny.py
```

### Async Warnings

If you see async warnings, ensure all dev dependencies are installed:
```bash
uv sync --dev
```

### Benchmark Not Running

If benchmarks are skipped, ensure all dev dependencies are installed:
```bash
uv sync --dev
```
