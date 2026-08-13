# Trasource

**AI-powered historical document retrieval engine.**

Trasource combines AI language models with full-text search to help researchers find and extract relevant passages from large collections of historical documents — newspapers, books, interviews, and more.

Instead of guessing which keywords to search for, describe your research topic in natural language. The AI expands your query with historically relevant terms, searches your document database, and extracts every related passage with full citations.

## Features

- **AI Query Expansion** — Describe a topic; AI generates historically relevant search terms with weights
- **Full-Text Search** — Weighted full-text search across your entire document library via DuckDB
- **AI Extraction** — Streaming AI reads matched documents and extracts every relevant passage verbatim with citations
- **Follow-up Chat** — Ask follow-up questions about extracted materials
- **Multi-Provider AI** — Gemini, Claude, ChatGPT, or local models (Ollama / vLLM)
- **Note-Taking** — Markdown notes linked to projects, with auto-save
- **Library Management** — Shared document library with per-project linking
- **Bilingual UI** — Chinese and English interface

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Desktop | [Tauri v2](https://tauri.app/) (Rust) |
| Frontend | Vue 3 + TypeScript + Tailwind CSS |
| Backend | Python FastAPI (bundled as sidecar binary) |
| Document DB | DuckDB (full-text search) |
| App DB | SQLite (notes, history, settings) |
| AI | Google Gemini / Anthropic Claude / OpenAI / OpenAI-compatible |

## How It Works

```
User Query: "How did People's Daily report on the Hundred Days No Children campaign?"
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               │
            Step 1: AI Expansion                    │
            Generates weighted keywords:            │
            冠县 ×10, 计划生育 ×10,                  │
            曾昭起 ×9, 百日无孩 ×8 ...               │
                    │                               │
                    ▼                               │
            Step 2: Weighted Search                  │
            Scans DuckDB with weighted              │
            tokens, returns top-K records           │
                    │                               │
                    ▼                               │
            Step 3: AI Extraction                   │
            Reads matched documents,                │
            extracts every relevant passage         │
            with date/source citations              │
                    │                               │
                    ▼                               │
            Results + Follow-up Chat ◄──────────────┘
```

## Prerequisites

- **Node.js** 22+
- **Rust** toolchain ([rustup.rs](https://rustup.rs/))
- **Python** 3.11+
- At least one AI API key (Gemini / Claude / OpenAI) or a local model server

## Getting Started

```bash
# Clone
git clone https://github.com/ZZhang93/trasource.git
cd trasource

# Install frontend dependencies
npm ci

# Create an isolated Python environment and install dependencies
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.lock

# Configure your API key (choose one method)
# Method 1: Create .env file
cp .env.example .env
# Edit .env and add your API key

# Method 2: Configure via the app's Settings UI after launch

# Start the desktop app. Tauri starts exactly one Python backend and the UI
# displays a startup screen while the sidecar is becoming ready.
./start.sh

# For browser-only frontend development, run these in separate terminals:
# python3 -m uvicorn backend.server:app --host 127.0.0.1 --port 8765
# npm run dev
```

On Windows, activate the environment with `.venv\Scripts\activate` and run
`npm run desktop:dev` instead of `./start.sh`.

### First Run

1. Keep the app open while the startup screen prepares the local backend. A packaged first launch can take 20–40 seconds.
2. Create a project from the sidebar.
3. Open **Settings**, choose an AI provider, add its API key, and test the connection.
4. Import documents into the project. CSV files must include a `文本内容` (or `content`) column.
5. Enter a research question. Finished AI excerpts appear as separate source cards; choose **View full original** to inspect the underlying record.

## Building

```bash
# Install runtime dependencies and the pinned release packager
python3 -m pip install -r requirements-build.txt

# Windows/Linux: build the frontend, target-specific sidecar, and bundle
npm run desktop:build

# macOS local distribution without a Developer ID certificate
APPLE_SIGNING_IDENTITY=- npm run desktop:build

# For a public macOS release, set APPLE_SIGNING_IDENTITY to a Developer ID
# Application identity and configure Apple notarization credentials instead.

# Output: src-tauri/target/release/bundle/
```

## Quality Checks

```bash
# Frontend build/type checks, translations, versions, and regression tests
npm run check

# Rust desktop shell (the first command prepares clean-clone sidecar metadata)
npm run prepare:sidecar:dev
(cd src-tauri && cargo check --locked)
```

## Supported Document Formats

| Format | Type | Notes |
|--------|------|-------|
| CSV | Newspapers | Auto-parses date, page, title, content columns |
| PDF | Books, papers | Text extraction via pypdf; scanned PDFs require OCR first |
| DOCX | Books, papers | Paragraph-level chunking |
| TXT | Any | Plain text import |
| EPUB | Books | Chapter-aware extraction |
| MOBI/AZW3 | Books | Requires Calibre's `ebook-convert` command |

## Configuration

All configuration is done through the **Settings** UI within the app:

- **AI Provider** — Select Gemini, Claude, ChatGPT, or local model
- **API Keys** — Stored locally in `settings.json`; they are sent only to the selected AI provider when making API requests
- **Model Selection** — Choose models for keyword analysis and document extraction independently
- **Custom Prompts** — Override the AI prompts for query expansion and extraction
- **Local Models** — Connect to Ollama, vLLM, or any OpenAI-compatible API

## Data and Backups

Packaged builds keep all projects, notes, settings, and databases in the platform's per-user data directory:

| Platform | Data directory |
|----------|----------------|
| macOS | `~/Library/Application Support/trasource` |
| Windows | `%LOCALAPPDATA%\trasource` |
| Linux | `${XDG_DATA_HOME:-~/.local/share}/trasource` |

Close the app before backing up or restoring this directory so DuckDB and SQLite files are copied consistently. Development mode stores runtime data in the repository root.

## Project Structure

```
trasource/
├── src/                    # Vue 3 frontend
│   ├── components/         # UI components
│   ├── views/              # Page views
│   ├── stores/             # Pinia state management
│   ├── i18n/               # Internationalization (zh/en)
│   └── api/                # API client
├── backend/                # Python FastAPI backend
│   ├── routes/             # API endpoints
│   └── server.py           # Entry point
├── core/                   # Core business logic
│   ├── llm_provider.py     # Multi-provider LLM abstraction
│   ├── query_expander.py   # AI query expansion
│   ├── retriever.py        # DuckDB full-text search
│   ├── db.py               # SQLite connection manager
│   └── ...
├── src-tauri/              # Tauri (Rust) desktop shell
├── requirements.txt        # Direct Python dependency ranges
└── requirements.lock       # Reproducible resolved Python environment
```

## License

The repository's [LICENSE](LICENSE) file is the authoritative license text (GNU AGPL v3).

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for the local
quality checks and pull-request expectations. Notable changes are tracked in
[CHANGELOG.md](CHANGELOG.md). Please report vulnerabilities using the private
process in [SECURITY.md](SECURITY.md).
