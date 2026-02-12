cargo build --release 
uv run maturin build --release
uv pip install --force-reinstall target/wheels/*.whl
uv run main_rs.py
