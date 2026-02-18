use pyo3_stub_gen::Result;
use std::path::{Path, PathBuf};

fn main() -> Result<()> {
    let stub = deny_filter::stub_info()?;
    //println!("{stub:?}");

    if let Some(module_name) = stub.modules.keys().next() {
        let target = Path::new(module_name);
        if !target.exists() {
            std::fs::create_dir_all(target).expect("failed to create dir");
        }

        stub.generate()?;

        // Move generated .pyi file to module_name/module_name.pyi
        let src = PathBuf::from(format!("{module_name}.pyi"));
        let dst = target.join(format!("{module_name}.pyi"));
        if src.exists() {
            std::fs::rename(&src, &dst).expect("failed to move .pyi file");
        }
    } else {
        stub.generate()?;
    }

    Ok(())
}
