uv cache clean deny_rust
uv maturin build --release 
uv run main_rs.py
