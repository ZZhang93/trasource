use serde::{Serialize, Deserialize};
use futures_util::StreamExt;

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct Message {
    pub role: String,
    pub content: String,
}

#[derive(Clone)]
pub struct LLMConfig {
    pub provider: String,
    pub api_key: String,
    pub model: String,
    pub base_url: Option<String>,
    pub proxy_url: Option<String>,
    pub system_prompt: Option<String>,
    pub temperature: f32,
    pub max_tokens: i32,
}

pub async fn stream_chat<F>(config: LLMConfig, messages: Vec<Message>, callback: F) -> Result<(), String>
where
    F: Fn(String) + Send + 'static,
{
    match config.provider.as_str() {
        "gemini" => stream_gemini(config, messages, callback).await,
        "openai" | "kimi" | "openai_compatible" => stream_openai(config, messages, callback).await,
        "claude" => stream_claude(config, messages, callback).await,
        _ => Err(format!("Unknown provider: {}", config.provider)),
    }
}

async fn stream_gemini<F>(config: LLMConfig, messages: Vec<Message>, callback: F) -> Result<(), String>
where
    F: Fn(String) + Send + 'static,
{
    let url = format!(
        "https://generativelanguage.googleapis.com/v1beta/models/{}:streamGenerateContent?alt=sse&key={}",
        config.model, config.api_key
    );

    let mut contents = Vec::new();
    for msg in messages {
        let role = if msg.role == "user" { "user" } else { "model" };
        contents.push(serde_json::json!({
            "role": role,
            "parts": [{"text": msg.content}]
        }));
    }

    let mut body = serde_json::json!({
        "contents": contents,
        "generationConfig": {
            "temperature": config.temperature,
            "maxOutputTokens": config.max_tokens,
        }
    });

    if let Some(sys) = config.system_prompt {
        body["systemInstruction"] = serde_json::json!({
            "parts": [{"text": sys}]
        });
    }

    let client = create_client(config.proxy_url)?;
    let res = client.post(url)
        .json(&body)
        .send()
        .await
        .map_err(|e: reqwest::Error| e.to_string())?;

    let mut stream = res.bytes_stream();
    while let Some(item) = stream.next().await {
        let chunk = item.map_err(|e: reqwest::Error| e.to_string())?;
        let text = String::from_utf8_lossy(&chunk);
        for line in text.lines() {
            if line.starts_with("data: ") {
                let data_str = &line[6..];
                if let Ok(data) = serde_json::from_str::<serde_json::Value>(data_str) {
                    if let Some(candidates) = data["candidates"].as_array() {
                        if let Some(cand) = candidates.get(0) {
                            if let Some(parts) = cand["content"]["parts"].as_array() {
                                for part in parts {
                                    if let Some(t) = part["text"].as_str() {
                                        callback(t.to_string());
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    Ok(())
}

async fn stream_openai<F>(config: LLMConfig, messages: Vec<Message>, callback: F) -> Result<(), String>
where
    F: Fn(String) + Send + 'static,
{
    let base_url = config.base_url.unwrap_or_else(|| {
        if config.provider == "kimi" {
            "https://api.moonshot.cn/v1".to_string()
        } else {
            "https://api.openai.com/v1".to_string()
        }
    });
    let url = format!("{}/chat/completions", base_url);

    let mut oai_messages = Vec::new();
    if let Some(sys) = config.system_prompt {
        oai_messages.push(serde_json::json!({"role": "system", "content": sys}));
    }
    for msg in messages {
        oai_messages.push(serde_json::json!({"role": msg.role, "content": msg.content}));
    }

    let body = serde_json::json!({
        "model": config.model,
        "messages": oai_messages,
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
        "stream": true,
    });

    let client = create_client(config.proxy_url)?;
    let res = client.post(url)
        .header("Authorization", format!("Bearer {}", config.api_key))
        .json(&body)
        .send()
        .await
        .map_err(|e: reqwest::Error| e.to_string())?;

    let mut stream = res.bytes_stream();
    while let Some(item) = stream.next().await {
        let chunk = item.map_err(|e: reqwest::Error| e.to_string())?;
        let text = String::from_utf8_lossy(&chunk);
        for line in text.lines() {
            if line.starts_with("data: ") {
                let data_str = line[6..].trim();
                if data_str == "[DONE]" { break; }
                if let Ok(data) = serde_json::from_str::<serde_json::Value>(data_str) {
                    if let Some(choices) = data["choices"].as_array() {
                        if let Some(choice) = choices.get(0) {
                            if let Some(content) = choice["delta"]["content"].as_str() {
                                callback(content.to_string());
                            }
                        }
                    }
                }
            }
        }
    }

    Ok(())
}

async fn stream_claude<F>(config: LLMConfig, messages: Vec<Message>, callback: F) -> Result<(), String>
where
    F: Fn(String) + Send + 'static,
{
    let url = "https://api.anthropic.com/v1/messages";

    let mut body = serde_json::json!({
        "model": config.model,
        "max_tokens": config.max_tokens,
        "temperature": config.temperature,
        "messages": messages,
        "stream": true,
    });

    if let Some(sys) = config.system_prompt {
        body["system"] = serde_json::json!(sys);
    }

    let client = create_client(config.proxy_url)?;
    let res = client.post(url)
        .header("x-api-key", &config.api_key)
        .header("anthropic-version", "2023-06-01")
        .json(&body)
        .send()
        .await
        .map_err(|e: reqwest::Error| e.to_string())?;

    let mut stream = res.bytes_stream();
    while let Some(item) = stream.next().await {
        let chunk = item.map_err(|e: reqwest::Error| e.to_string())?;
        let text = String::from_utf8_lossy(&chunk);
        for line in text.lines() {
            if line.starts_with("data: ") {
                let data_str = line[6..].trim();
                if let Ok(data) = serde_json::from_str::<serde_json::Value>(data_str) {
                    if data["type"] == "content_block_delta" {
                        if let Some(t) = data["delta"]["text"].as_str() {
                            callback(t.to_string());
                        }
                    }
                }
            }
        }
    }

    Ok(())
}

pub async fn generate(config: LLMConfig, prompt: String) -> Result<String, String> {
    let (tx, mut rx) = tokio::sync::mpsc::channel(100);
    let messages = vec![Message { role: "user".to_string(), content: prompt }];
    
    let config_clone = config.clone();
    tokio::spawn(async move {
        let _ = stream_chat(config_clone, messages, move |chunk| {
            let _ = tx.blocking_send(chunk);
        }).await;
    });

    let mut full_text = String::new();
    while let Some(chunk) = rx.recv().await {
        full_text.push_str(&chunk);
    }
    Ok(full_text)
}

fn create_client(proxy_url: Option<String>) -> Result<reqwest::Client, String> {
    let mut builder = reqwest::Client::builder();
    if let Some(proxy) = proxy_url {
        if !proxy.is_empty() {
            builder = builder.proxy(reqwest::Proxy::all(proxy).map_err(|e| e.to_string())?);
        }
    }
    builder.build().map_err(|e| e.to_string())
}
