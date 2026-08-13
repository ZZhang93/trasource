#[cfg(trasource_dev)]
use std::path::Path;
#[cfg(trasource_dev)]
use std::process::{Child as DevChild, Command, Stdio};
use std::sync::Mutex;
use std::time::Duration;
use tauri::Manager;
#[cfg(not(trasource_dev))]
use tauri_plugin_shell::process::CommandChild;
#[cfg(not(trasource_dev))]
use tauri_plugin_shell::ShellExt;

enum BackendChild {
    #[cfg(trasource_dev)]
    Dev(DevChild),
    #[cfg(not(trasource_dev))]
    Sidecar(CommandChild),
}

struct BackendRuntime {
    child: Option<BackendChild>,
    instance_token: String,
}

struct BackendProcess {
    runtime: Mutex<BackendRuntime>,
    lifecycle: Mutex<()>,
}

fn new_instance_token() -> Result<String, String> {
    let mut bytes = [0_u8; 32];
    getrandom::fill(&mut bytes)
        .map_err(|error| format!("无法从操作系统生成后端认证令牌：{error}"))?;
    Ok(bytes.iter().map(|byte| format!("{byte:02x}")).collect())
}

fn ensure_backend_port_available() -> Result<(), String> {
    std::net::TcpListener::bind(("127.0.0.1", 8765))
        .map(drop)
        .map_err(|_| {
            "后端端口 8765 已被占用。请关闭其他问渠实例或占用该端口的程序后重试。".to_string()
        })
}

#[cfg(trasource_dev)]
fn spawn_dev_backend(instance_token: &str) -> std::io::Result<DevChild> {
    let project_root = Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .expect("src-tauri must live inside the project root");

    let mut candidates = Vec::new();
    if let Some(value) = std::env::var_os("TRASOURCE_PYTHON") {
        candidates.push(value);
    }
    if cfg!(windows) {
        candidates.push(
            project_root
                .join(".venv")
                .join("Scripts")
                .join("python.exe")
                .into_os_string(),
        );
        candidates.push("python".into());
    } else {
        candidates.push(
            project_root
                .join(".venv")
                .join("bin")
                .join("python")
                .into_os_string(),
        );
        candidates.push("python3".into());
        candidates.push("python".into());
    }

    let mut last_error = None;
    for python in candidates {
        match Command::new(&python)
            .args([
                "-m",
                "uvicorn",
                "backend.server:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8765",
                "--log-level",
                "warning",
            ])
            .env("TRASOURCE_INSTANCE_TOKEN", instance_token)
            .current_dir(project_root)
            .stdin(Stdio::null())
            .stdout(Stdio::inherit())
            .stderr(Stdio::inherit())
            .spawn()
        {
            Ok(child) => return Ok(child),
            Err(error) => last_error = Some(error),
        }
    }

    Err(last_error.unwrap_or_else(|| {
        std::io::Error::new(std::io::ErrorKind::NotFound, "Python interpreter not found")
    }))
}

fn spawn_owned_backend(_app: &tauri::AppHandle) -> Result<(BackendChild, String), String> {
    ensure_backend_port_available()?;
    let instance_token = new_instance_token()?;

    #[cfg(trasource_dev)]
    let child =
        BackendChild::Dev(spawn_dev_backend(&instance_token).map_err(|error| error.to_string())?);

    #[cfg(not(trasource_dev))]
    let child = {
        let sidecar_cmd = _app
            .shell()
            .sidecar("trasource-backend")
            .map_err(|error| error.to_string())?
            .env("TRASOURCE_INSTANCE_TOKEN", &instance_token);
        let (_rx, child) = sidecar_cmd.spawn().map_err(|error| error.to_string())?;
        BackendChild::Sidecar(child)
    };

    Ok((child, instance_token))
}

fn stop_backend(child: BackendChild) {
    match child {
        #[cfg(trasource_dev)]
        BackendChild::Dev(mut child) => {
            let _ = child.kill();
            let _ = child.wait();
        }
        #[cfg(not(trasource_dev))]
        BackendChild::Sidecar(child) => {
            let _ = child.kill();
        }
    }
}

#[tauri::command]
fn backend_instance_token(state: tauri::State<'_, BackendProcess>) -> Result<String, String> {
    let runtime = state.runtime.lock().map_err(|_| "后端状态锁已损坏")?;
    if runtime.instance_token.is_empty() {
        Err("后端尚未启动".into())
    } else {
        Ok(runtime.instance_token.clone())
    }
}

#[tauri::command]
fn restart_backend(
    app: tauri::AppHandle,
    state: tauri::State<'_, BackendProcess>,
) -> Result<String, String> {
    // Hold this guard across stop, port release, spawn, and state publication.
    // Otherwise concurrent retries can each spawn a child and overwrite the
    // stored handle, leaving an unowned backend process behind.
    let _lifecycle = state.lifecycle.lock().map_err(|_| "后端生命周期锁已损坏")?;
    let old_child = {
        let mut runtime = state.runtime.lock().map_err(|_| "后端状态锁已损坏")?;
        runtime.instance_token.clear();
        runtime.child.take()
    };
    if let Some(child) = old_child {
        stop_backend(child);
        // Give the OS a short moment to release the listening socket.
        std::thread::sleep(Duration::from_millis(200));
    }

    let (child, instance_token) = spawn_owned_backend(&app)?;
    let mut runtime = state.runtime.lock().map_err(|_| "后端状态锁已损坏")?;
    runtime.child = Some(child);
    runtime.instance_token = instance_token.clone();
    Ok(instance_token)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_opener::init())
        .manage(BackendProcess {
            runtime: Mutex::new(BackendRuntime {
                child: None,
                instance_token: String::new(),
            }),
            lifecycle: Mutex::new(()),
        })
        .invoke_handler(tauri::generate_handler![
            backend_instance_token,
            restart_backend
        ])
        .setup(|app| {
            // `trasource_dev` is written by the Tauri dev hook, so `tauri dev
            // --release` still runs source Python while `tauri build --debug`
            // still bundles and runs the release sidecar.
            let (child, instance_token) =
                spawn_owned_backend(app.handle()).map_err(|error| std::io::Error::other(error))?;
            let state = app.state::<BackendProcess>();
            let mut runtime = state.runtime.lock().unwrap();
            runtime.child = Some(child);
            runtime.instance_token = instance_token;
            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::Destroyed = event {
                let app_handle = window.app_handle();
                let state = app_handle.state::<BackendProcess>();
                // Serialize shutdown with an in-flight explicit restart so a
                // newly spawned child cannot be published after this event.
                let _lifecycle = state.lifecycle.lock().unwrap();
                let child = state.runtime.lock().unwrap().child.take();
                if let Some(child) = child {
                    stop_backend(child);
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

#[cfg(test)]
mod tests {
    use super::new_instance_token;

    #[test]
    fn instance_tokens_are_random_256_bit_hex_values() {
        let first = new_instance_token().expect("OS randomness should be available");
        let second = new_instance_token().expect("OS randomness should be available");
        assert_eq!(first.len(), 64);
        assert!(first.bytes().all(|byte| byte.is_ascii_hexdigit()));
        assert_ne!(first, second);
    }
}
