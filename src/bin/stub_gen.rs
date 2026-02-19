use deny_filter::pymodule::stub_info;
use pyo3_stub_gen::Result;
/// Generate or update the `.pyi` stub file for the current pyo3 package.
///
/// This inspects the package metadata and writes a type stub suitable for IDEs and type checkers.
///
/// # Errors
///
/// Returns an error if the package metadata is invalid or if stub generation fails.
///
/// # Examples
///
/// ```
/// // Generate or update the stub; will panic on error in example code.
/// main().unwrap();
/// ```
fn main() -> Result<()> {
    let stub = stub_info()?;
    stub.generate()?;
    Ok(())
}