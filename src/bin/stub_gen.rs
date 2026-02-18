use pyo3_stub_gen::Result;
use std::env;
use std::path::Path;

fn main() -> Result<()> {
    let stub = deny_filter::stub_info()?;
    //println!("{stub:?}");

    if let Some(module_name) = stub.modules.keys().next() {
        let target = Path::new(module_name);
        if !target.exists() {
            std::fs::create_dir_all(target).expect("failed to create dir");
        }
        env::set_current_dir(target).expect("failed to change dir");
    }

    Ok(())
}
