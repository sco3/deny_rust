use deny_filter::pymodule::stub_info;
use pyo3_stub_gen::Result;
use std::path::{Path, PathBuf};

fn main() -> Result<()> {
    let stub = stub_info()?;
    //println!("{stub:?}");

    if let Some(module_name) = stub.modules.keys().next() {
        let target = Path::new(module_name);
        if !target.exists() {
            std::fs::create_dir_all(target)?;
        }
        stub.generate()?;
        // Move generated .pyi file to module_name/module_name.pyi
        let src = PathBuf::from(format!("{module_name}.pyi"));
        let dst = target.join(format!("{module_name}.pyi"));
        if src.exists() {
            std::fs::rename(&src, &dst)?;
        }
    } else {
        stub.generate()?;
    }
    Ok(())
}
