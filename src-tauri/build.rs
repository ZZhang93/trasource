fn main() {
    println!("cargo:rustc-check-cfg=cfg(trasource_dev)");
    println!("cargo:rerun-if-env-changed=TRASOURCE_FORCE_SIDECAR");
    println!("cargo:rerun-if-changed=.trasource-dev-mode");
    if std::path::Path::new(".trasource-dev-mode").exists()
        && std::env::var_os("TRASOURCE_FORCE_SIDECAR").is_none()
    {
        println!("cargo:rustc-cfg=trasource_dev");
    }
    tauri_build::build()
}
