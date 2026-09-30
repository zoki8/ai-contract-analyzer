use std::sync::Mutex;

use tauri::Manager;
use tauri_plugin_shell::process::{CommandChild, CommandEvent};
use tauri_plugin_shell::ShellExt;

// the running backend, kept so it can be stopped when the app exits
struct Backend(Mutex<Option<CommandChild>>);

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }

            // start the packaged Python backend
            let (mut events, child) = app.shell().sidecar("clausewise-backend")?.spawn()?;
            app.manage(Backend(Mutex::new(Some(child))));

            // read the backend's output; if nobody reads it, the backend blocks
            tauri::async_runtime::spawn(async move {
                while let Some(event) = events.recv().await {
                    if let CommandEvent::Stdout(line) | CommandEvent::Stderr(line) = event {
                        println!("[backend] {}", String::from_utf8_lossy(&line).trim_end());
                    }
                }
            });
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(|app, event| {
            // stop the backend when the app closes
            if let tauri::RunEvent::Exit = event {
                if let Some(child) = app.state::<Backend>().0.lock().unwrap().take() {
                    let _ = child.kill();
                }
            }
        });
}