uv cache clean deny_rust
cargo build --release 
uv sync
uv run main_rs.py
