use std::sync::Mutex;
use std::fs;
use std::path::PathBuf;
use once_cell::sync::Lazy;
use jieba_rs::Jieba;
use regex::Regex;
use serde::{Serialize, Deserialize};
use chrono::Local;
use tauri::{Manager, Emitter};
use tauri_plugin_shell::ShellExt;
use tauri_plugin_shell::process::CommandChild;

mod llm;
use llm::{Message, LLMConfig};

static JIEBA: Lazy<Jieba> = Lazy::new(Jieba::new);

#[derive(Serialize, Deserialize, Debug, Clone)]
struct SearchRecord {
    id: i64,
    source_file: String,
    file_type: String,
    doc_type: String,
    year: String,
    date: String,
    page: String,
    title: String,
    author: String,
    pub_year: String,
    publisher: String,
    chapter: String,
    section: String,
    page_num: String,
    interviewee: String,
    interview_date: String,
    interview_location: String,
    content: String,
    relevance_score: f64,
}

#[derive(Serialize, Deserialize, Debug, Clone)]
struct SearchResult {
    records: Vec<SearchRecord>,
    total_found: usize,
    context: String,
    context_chars: usize,
    truncated: bool,
    tokens: Vec<String>,
}

#[derive(Serialize, Deserialize, Debug, Clone)]
struct Project {
    name: String,
    description: String,
    created_at: String,
    updated_at: String,
    file_count: i32,
    record_count: i32,
    files: Vec<String>,
    shared_files: Vec<String>,
}

struct BackendProcess(Mutex<Option<CommandChild>>);

// ──────────────────────────────────────────────
// Helpers
// ──────────────────────────────────────────────

fn get_data_dir(app_handle: &tauri::AppHandle) -> PathBuf {
    #[cfg(debug_assertions)]
    { std::env::current_dir().unwrap() }
    #[cfg(not(debug_assertions))]
    { app_handle.path().app_data_dir().unwrap() }
}

fn get_settings_path(app_handle: &tauri::AppHandle) -> PathBuf {
    get_data_dir(app_handle).join("settings.json")
}

fn get_projects_dir(app_handle: &tauri::AppHandle) -> PathBuf {
    get_data_dir(app_handle).join("projects")
}

fn format_citation(rec: &SearchRecord) -> String {
    match rec.doc_type.as_str() {
        "newspaper" => {
            let date = if !rec.date.is_empty() { &rec.date } else if !rec.year.is_empty() { &rec.year } else { "日期不详" };
            let page = if !rec.page.is_empty() { &rec.page } else { "版次不详" };
            let title = if !rec.title.is_empty() { &rec.title } else { "无标题" };
            format!("[日期：{} / 版面：{} / 标题：{}]", date, page, title)
        }
        "book" => {
            let mut parts = Vec::new();
            if !rec.author.is_empty() { parts.push(rec.author.clone()); }
            if !rec.title.is_empty() { parts.push(format!("《{}》", rec.title)); }
            if !rec.publisher.is_empty() { parts.push(rec.publisher.clone()); }
            if !rec.pub_year.is_empty() { parts.push(rec.pub_year.clone()); }
            if !rec.chapter.is_empty() { parts.push(rec.chapter.clone()); }
            if !rec.section.is_empty() { parts.push(rec.section.clone()); }
            if !rec.page_num.is_empty() { parts.push(rec.page_num.clone()); }
            format!("[{}]", parts.join("，"))
        }
        "interview" => {
            let mut parts = Vec::new();
            if !rec.interviewee.is_empty() { parts.push(format!("受访：{}", rec.interviewee)); }
            if !rec.interview_date.is_empty() { parts.push(format!("时间：{}", rec.interview_date)); }
            if !rec.interview_location.is_empty() { parts.push(format!("地点：{}", rec.interview_location)); }
            if !rec.title.is_empty() { parts.push(format!("来源：{}", rec.title)); }
            format!("[{}]", parts.join("，"))
        }
        _ => {
            let mut parts = Vec::new();
            if !rec.title.is_empty() { parts.push(format!("来源：{}", rec.title)); }
            if !rec.author.is_empty() { parts.push(format!("作者：{}", rec.author)); }
            if !rec.date.is_empty() { parts.push(format!("日期：{}", rec.date)); }
            if !rec.chapter.is_empty() { parts.push(format!("章节：{}", rec.chapter)); }
            if !rec.page_num.is_empty() { parts.push(format!("页码：{}", rec.page_num)); }
            if parts.is_empty() { "[来源不详]".to_string() } else { format!("[{}]", parts.join("，")) }
        }
    }
}

// ──────────────────────────────────────────────
// Settings Commands
// ──────────────────────────────────────────────

#[tauri::command]
fn get_settings(app_handle: tauri::AppHandle) -> Result<serde_json::Value, String> {
    let path = get_settings_path(&app_handle);
    let mut settings_map = if path.exists() {
        let content = fs::read_to_string(path).map_err(|e| e.to_string())?;
        serde_json::from_str::<serde_json::Map<String, serde_json::Value>>(&content).unwrap_or_default()
    } else { serde_json::Map::new() };

    let defaults = serde_json::json!({
        "provider": "gemini", "gemini_model": "gemini-3-flash-preview", "gemini_expansion_model": "gemini-3-flash-preview",
        "gemini_extraction_model": "gemini-3-flash-preview", "claude_model": "claude-sonnet-4-6", "openai_model": "gpt-4o", "top_k": 50
    });

    if let serde_json::Value::Object(default_map) = defaults {
        for (k, v) in default_map { if !settings_map.contains_key(&k) { settings_map.insert(k, v); } }
    }

    let keys_to_mask = ["gemini_api_key", "claude_api_key", "openai_api_key", "kimi_api_key", "local_api_key"];
    for key in keys_to_mask {
        if let Some(val) = settings_map.get(key) {
            if let Some(s) = val.as_str() {
                let masked = if s.len() > 8 { format!("{}••••••••", &s[..8]) } else if !s.is_empty() { "••••••••".to_string() } else { "".to_string() };
                settings_map.insert(format!("{}_masked", key), serde_json::Value::String(masked));
            }
        }
    }
    Ok(serde_json::Value::Object(settings_map))
}

#[tauri::command]
fn update_settings(app_handle: tauri::AppHandle, new_settings: serde_json::Value) -> Result<(), String> {
    let path = get_settings_path(&app_handle);
    let data_dir = get_data_dir(&app_handle);
    if !data_dir.exists() { fs::create_dir_all(&data_dir).map_err(|e| e.to_string())?; }
    let content = serde_json::to_string_pretty(&new_settings).map_err(|e| e.to_string())?;
    fs::write(path, content).map_err(|e| e.to_string())?;
    Ok(())
}

// ──────────────────────────────────────────────
// Project Commands
// ──────────────────────────────────────────────

#[tauri::command]
fn list_projects(app_handle: tauri::AppHandle) -> Result<Vec<Project>, String> {
    let projects_dir = get_projects_dir(&app_handle);
    if !projects_dir.exists() {
        fs::create_dir_all(&projects_dir).map_err(|e| e.to_string())?;
        return Ok(vec![]);
    }
    let mut projects = Vec::new();
    if let Ok(entries) = fs::read_dir(projects_dir) {
        for entry in entries.flatten() {
            let path = entry.path();
            if path.is_dir() {
                let name = path.file_name().unwrap().to_str().unwrap();
                if name == "_shared" { continue; }
                let meta_path = path.join("project.json");
                if meta_path.exists() {
                    if let Ok(content) = fs::read_to_string(meta_path) {
                        if let Ok(project) = serde_json::from_str::<Project>(&content) { projects.push(project); }
                    }
                }
            }
        }
    }
    projects.sort_by(|a, b| b.updated_at.cmp(&a.updated_at));
    Ok(projects)
}

#[tauri::command]
fn create_project(app_handle: tauri::AppHandle, name: String, description: String) -> Result<Project, String> {
    let projects_dir = get_projects_dir(&app_handle);
    let project_dir = projects_dir.join(&name);
    if project_dir.exists() { return Err(format!("项目「{}」已存在", name)); }
    fs::create_dir_all(project_dir.join("db")).map_err(|e| e.to_string())?;
    fs::create_dir_all(project_dir.join("raw_files")).map_err(|e| e.to_string())?;
    let now = Local::now().to_rfc3339();
    let project = Project { name, description, created_at: now.clone(), updated_at: now, file_count: 0, record_count: 0, files: vec![], shared_files: vec![] };
    let meta_path = project_dir.join("project.json");
    let content = serde_json::to_string_pretty(&project).map_err(|e| e.to_string())?;
    fs::write(meta_path, content).map_err(|e| e.to_string())?;
    Ok(project)
}

#[tauri::command]
fn delete_project(app_handle: tauri::AppHandle, name: String) -> Result<(), String> {
    let projects_dir = get_projects_dir(&app_handle);
    let project_dir = projects_dir.join(name);
    if project_dir.exists() { fs::remove_dir_all(project_dir).map_err(|e| e.to_string())?; }
    Ok(())
}

#[tauri::command]
fn get_project_files(app_handle: tauri::AppHandle, project_name: String) -> Result<Vec<String>, String> {
    let p_dir = get_projects_dir(&app_handle);
    let project_meta_path = p_dir.join(&project_name).join("project.json");
    if project_meta_path.exists() {
        let content = fs::read_to_string(project_meta_path).map_err(|e| e.to_string())?;
        let meta: serde_json::Value = serde_json::from_str(&content).map_err(|e| e.to_string())?;
        let files = meta.get("shared_files").and_then(|v| v.as_array()).map(|arr| arr.iter().filter_map(|v| v.as_str().map(|s| s.to_string())).collect()).unwrap_or_else(Vec::new);
        Ok(files)
    } else { Err("项目不存在".to_string()) }
}

// ──────────────────────────────────────────────
// Search Command
// ──────────────────────────────────────────────

#[tauri::command]
fn execute_search(
    app_handle: tauri::AppHandle,
    project_name: String,
    query: String,
    weighted_tokens: Option<Vec<(String, i32)>>,
    _date_from: Option<String>,
    _date_to: Option<String>,
    _file_filter_list: Option<Vec<String>>,
    _doc_type_filter: Option<String>,
    top_k: Option<usize>,
    language: Option<String>,
) -> Result<SearchResult, String> {
    let p_dir = get_projects_dir(&app_handle);
    let shared_db_path = p_dir.join("_shared/db/history.duckdb");
    let project_meta_path = p_dir.join(&project_name).join("project.json");
    let allowed_files: Option<Vec<String>> = if project_meta_path.exists() {
        let content = fs::read_to_string(project_meta_path).map_err(|e| e.to_string())?;
        let meta: serde_json::Value = serde_json::from_str(&content).map_err(|e| e.to_string())?;
        meta.get("shared_files").and_then(|v| v.as_array()).map(|arr| arr.iter().filter_map(|v| v.as_str().map(|s| s.to_string())).collect())
    } else { None };

    let mut tokens_with_weights = Vec::new();
    if let Some(wt) = weighted_tokens { tokens_with_weights = wt; }
    else {
        let lang = language.unwrap_or_else(|| "zh".to_string());
        if lang == "en" {
            let re = Regex::new(r"[a-zA-Z]{2,}").unwrap();
            for mat in re.find_iter(&query.to_lowercase()) { tokens_with_weights.push((mat.as_str().to_string(), 1)); }
        } else {
            let words = JIEBA.cut_for_search(&query, true);
            for w in words { if w.chars().count() >= 2 { tokens_with_weights.push((w.to_string(), 1)); } }
        }
        tokens_with_weights.push((query.clone(), 1));
    }

    if tokens_with_weights.is_empty() { return Ok(SearchResult { records: vec![], total_found: 0, context: "".to_string(), context_chars: 0, truncated: false, tokens: vec![] }); }

    let mut conditions = Vec::new();
    let mut score_parts = Vec::new();
    let mut params: Vec<Box<dyn duckdb::ToSql>> = Vec::new();
    for (token, weight) in &tokens_with_weights {
        let pattern = format!("%{}%", token);
        conditions.push("(title LIKE ? OR content LIKE ? OR chapter LIKE ? OR author LIKE ?)");
        for _ in 0..4 { params.push(Box::new(pattern.clone())); }
        score_parts.push(format!("(CASE WHEN title LIKE ? THEN {} ELSE 0 END + CASE WHEN chapter LIKE ? THEN {} ELSE 0 END + CASE WHEN content LIKE ? THEN {} ELSE 0 END)", weight * 3, weight * 2, weight * 1));
        for _ in 0..3 { params.push(Box::new(pattern.clone())); }
    }
    let sql = format!("SELECT id, source_file, file_type, doc_type, year, date, page, title, author, pub_year, publisher, chapter, section, page_num, interviewee, interview_date, interview_location, content, ({}) AS relevance_score FROM documents WHERE ({}) {} ORDER BY relevance_score DESC LIMIT 5000",
        score_parts.join(" + "), conditions.join(" OR "), 
        if let Some(af) = allowed_files { 
            let qmarks = vec!["?"; af.len()].join(",");
            params.extend(af.into_iter().map(|s| Box::new(s) as Box<dyn duckdb::ToSql>));
            format!("AND source_file IN ({})", qmarks)
        } else { "".to_string() }
    );

    let conn = duckdb::Connection::open(shared_db_path).map_err(|e| e.to_string())?;
    let mut stmt = conn.prepare(&sql).map_err(|e| e.to_string())?;
    let params_refs: Vec<&dyn duckdb::ToSql> = params.iter().map(|b| b.as_ref()).collect();
    let rows = stmt.query_map(params_refs.as_slice(), |row| {
        Ok(SearchRecord { id: row.get(0)?, source_file: row.get(1)?, file_type: row.get(2)?, doc_type: row.get(3)?, year: row.get(4)?, date: row.get(5)?, page: row.get(6)?, title: row.get(7)?, author: row.get(8)?, pub_year: row.get(9)?, publisher: row.get(10)?, chapter: row.get(11)?, section: row.get(12)?, page_num: row.get(13)?, interviewee: row.get(14)?, interview_date: row.get(15)?, interview_location: row.get(16)?, content: row.get(17)?, relevance_score: row.get(18)? })
    }).map_err(|e| e.to_string())?;

    let mut records = Vec::new();
    for row in rows { records.push(row.map_err(|e| e.to_string())?); }
    let total_found = records.len();
    let k = top_k.unwrap_or(50);
    let records_for_llm = if records.len() > k { &records[..k] } else { &records };
    let mut context_parts = Vec::new();
    for r in records_for_llm { context_parts.push(format!("【文献信息】{}\n【内容】{}\n{}", format_citation(r), r.content, "─".repeat(60))); }
    let mut full_context = context_parts.join("\n\n");
    if full_context.len() > 1_500_000 { full_context = full_context[..1_500_000].to_string(); }
    Ok(SearchResult { records, total_found, context_chars: full_context.len(), context: full_context, truncated: total_found > k, tokens: tokens_with_weights.into_iter().map(|(t, _)| t).collect() })
}

// ──────────────────────────────────────────────
// LLM Commands
// ──────────────────────────────────────────────

fn get_expansion_model_name(settings: &serde_json::Value) -> String {
    let p = settings["provider"].as_str().unwrap_or("gemini");
    match p {
        "gemini" => settings["gemini_expansion_model"].as_str().or(settings["gemini_model"].as_str()).unwrap_or("gemini-3-flash-preview").to_string(),
        "claude" => settings["claude_expansion_model"].as_str().or(settings["claude_model"].as_str()).unwrap_or("claude-sonnet-4-6").to_string(),
        "openai" => settings["openai_expansion_model"].as_str().or(settings["openai_model"].as_str()).unwrap_or("gpt-4o").to_string(),
        "kimi" => settings["kimi_expansion_model"].as_str().or(settings["kimi_model"].as_str()).unwrap_or("moonshot-v1-8k").to_string(),
        "openai_compatible" => settings["local_expansion_model"].as_str().or(settings["local_model"].as_str()).unwrap_or("").to_string(),
        _ => "".to_string(),
    }
}

fn get_extraction_model_name(settings: &serde_json::Value) -> String {
    let p = settings["provider"].as_str().unwrap_or("gemini");
    match p {
        "gemini" => settings["gemini_extraction_model"].as_str().or(settings["gemini_model"].as_str()).unwrap_or("gemini-3-flash-preview").to_string(),
        "claude" => settings["claude_extraction_model"].as_str().or(settings["claude_model"].as_str()).unwrap_or("claude-sonnet-4-6").to_string(),
        "openai" => settings["openai_extraction_model"].as_str().or(settings["openai_model"].as_str()).unwrap_or("gpt-4o").to_string(),
        "kimi" => settings["kimi_extraction_model"].as_str().or(settings["kimi_model"].as_str()).unwrap_or("moonshot-v1-8k").to_string(),
        "openai_compatible" => settings["local_extraction_model"].as_str().or(settings["local_model"].as_str()).unwrap_or("").to_string(),
        _ => "".to_string(),
    }
}

fn get_api_key(settings: &serde_json::Value) -> String {
    let p = settings["provider"].as_str().unwrap_or("gemini");
    match p {
        "gemini" => settings["gemini_api_key"].as_str().unwrap_or("").to_string(),
        "claude" => settings["claude_api_key"].as_str().unwrap_or("").to_string(),
        "openai" => settings["openai_api_key"].as_str().unwrap_or("").to_string(),
        "kimi" => settings["kimi_api_key"].as_str().unwrap_or("").to_string(),
        "openai_compatible" => settings["local_api_key"].as_str().unwrap_or("").to_string(),
        _ => "".to_string(),
    }
}

#[tauri::command]
async fn llm_expand_query(app_handle: tauri::AppHandle, query: String, language: String, sources: String) -> Result<serde_json::Value, String> {
    let settings = get_settings(app_handle.clone())?;
    let provider = settings["provider"].as_str().unwrap_or("gemini").to_string();
    let model = get_expansion_model_name(&settings);
    let api_key = get_api_key(&settings);
    let config = LLMConfig { provider, api_key, model, base_url: settings["local_base_url"].as_str().map(|s| s.to_string()), proxy_url: settings["proxy_url"].as_str().map(|s| s.to_string()), system_prompt: None, temperature: 0.2, max_tokens: 4096 };
    let prompt = if language == "en" { format!("You are a history expert... Database contents: {}\n\nQuery: \"{}\"\n\nOutput JSON directly: {{\"intent\":..., \"terms\": {{\"term\": weight}}}}", sources, query) }
    else { format!("你是一位中国近现代史研究专家... 数据库内容：{}\n\n用户想检索：\"{}\"\n\n请生成10-20个搜索词，标注权重(1-10)。直接输出JSON对象：\n{{\"intent\":\"检索意图\",\"terms\":{{\"词1\":权重,\"词2\":权重}}}}", sources, query) };
    let raw_text = llm::generate(config, prompt).await?;
    let mut result: serde_json::Value = if let Some(start) = raw_text.find('{') { if let Some(end) = raw_text.rfind('}') { serde_json::from_str(&raw_text[start..end+1]).map_err(|e| e.to_string())? } else { return Err("Invalid JSON".to_string()); } } else { return Err("No JSON found".to_string()); };
    result["success"] = serde_json::json!(true);
    result["raw_query"] = serde_json::json!(query);
    Ok(result)
}

#[tauri::command]
async fn llm_chat_stream(app_handle: tauri::AppHandle, messages: Vec<Message>, system_prompt: Option<String>, temperature: Option<f32>, is_extraction: Option<bool>) -> Result<(), String> {
    let settings = get_settings(app_handle.clone())?;
    let provider = settings["provider"].as_str().unwrap_or("gemini").to_string();
    let model = if is_extraction.unwrap_or(false) { get_extraction_model_name(&settings) } else { get_extraction_model_name(&settings) };
    let api_key = get_api_key(&settings);
    let config = LLMConfig { provider, api_key, model, base_url: settings["local_base_url"].as_str().map(|s| s.to_string()), proxy_url: settings["proxy_url"].as_str().map(|s| s.to_string()), system_prompt, temperature: temperature.unwrap_or(0.7), max_tokens: 4096 };
    let handle_clone = app_handle.clone();
    llm::stream_chat(config, messages, move |chunk| { let _ = handle_clone.emit("llm-chunk", chunk); }).await?;
    app_handle.emit("llm-done", ()).map_err(|e: tauri::Error| e.to_string())?;
    Ok(())
}

// ──────────────────────────────────────────────
// Metadata Commands
// ──────────────────────────────────────────────

#[tauri::command]
fn get_model_info() -> serde_json::Value {
    serde_json::json!({
        "gemini": [{"label": "Gemini 3 Flash", "value": "gemini-3-flash-preview"}, {"label": "Gemini 3.1 Pro", "value": "gemini-3.1-pro-preview"}],
        "claude": [{"label": "Claude Sonnet 4.6", "value": "claude-sonnet-4-6"}],
        "openai": [{"label": "GPT-4o", "value": "gpt-4o"}],
        "providers": [{"value": "gemini", "label": "Google Gemini"}, {"value": "claude", "label": "Claude"}, {"value": "openai", "label": "OpenAI"}]
    })
}

#[tauri::command]
fn get_default_prompts() -> serde_json::Value {
    serde_json::json!({ "extraction_prompt": "你是一位史料摘录员...", "expansion_prompt": "你是一位史学专家..." })
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init()).plugin(tauri_plugin_shell::init()).plugin(tauri_plugin_opener::init())
        .manage(BackendProcess(Mutex::new(None)))
        .setup(|app| {
            let p_dir = get_projects_dir(&app.handle());
            if !p_dir.exists() { let _ = fs::create_dir_all(&p_dir); }
            let shared_dir = p_dir.join("_shared");
            if !shared_dir.exists() {
                let _ = fs::create_dir_all(shared_dir.join("db"));
                let _ = fs::create_dir_all(shared_dir.join("raw_files"));
                let now = Local::now().to_rfc3339();
                let shared_meta = Project { name: "_shared".to_string(), description: "全局共享文件库".to_string(), created_at: now.clone(), updated_at: now, file_count: 0, record_count: 0, files: vec![], shared_files: vec![] };
                let _ = fs::write(shared_dir.join("project.json"), serde_json::to_string_pretty(&shared_meta).unwrap());
            }
            let sidecar_cmd = app.shell().sidecar("trasource-backend")?;
            let (_rx, child) = sidecar_cmd.spawn()?;
            app.manage(BackendProcess(Mutex::new(Some(child))));
            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::Destroyed = event {
                if let Some(state) = window.app_handle().try_state::<BackendProcess>() {
                    if let Ok(mut lock) = state.0.lock() { if let Some(child) = lock.take() { let _ = child.kill(); } }
                }
            }
        })
        .invoke_handler(tauri::generate_handler![
            get_settings, update_settings, list_projects, create_project, delete_project, 
            get_project_files, execute_search, llm_expand_query, llm_chat_stream, get_model_info, get_default_prompts
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
