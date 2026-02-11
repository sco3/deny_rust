uv run maturin build --release
.venv/bin/pip install --force-reinstall target/wheels/deny_rust-1.0.0b2-cp312-cp312-linux_x86_64.whl
.venv/bin/python main.py