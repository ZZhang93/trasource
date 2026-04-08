# Trasource

**AI-powered historical document retrieval engine.**

Trasource combines AI language models with full-text search to help researchers find and extract relevant passages from large collections of historical documents — newspapers, books, interviews, and more.

Instead of guessing which keywords to search for, describe your research topic in natural language. The AI expands your query with historically relevant terms, searches your document database, and extracts every related passage with full citations.

## Features

- **AI Query Expansion** — Describe a topic; AI generates historically relevant search terms with weights
- **Full-Text Search** — BM25 weighted search across your entire document library via DuckDB
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
User Query: "How did People's Daily report on the Characteristic of the 8th CPC National Congress?"
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               │
            Step 1: AI Expansion                    │
            Generates weighted keywords:            │
            8th CPC ×10, Characteristic ×10,        │
            Revolutionary experience ×9, ...        │
                    │                               │
                    ▼                               │
            Step 2: BM25 Search                     │
            Searches DuckDB with weighted           │
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

- **Node.js** 18+
- **Rust** toolchain ([rustup.rs](https://rustup.rs/))
- **Python** 3.10+
- At least one AI API key (Gemini / Claude / OpenAI) or a local model server

## Getting Started

```bash
# Clone
git clone https://github.com/YOUR_USERNAME/trasource.git
cd trasource

# Install frontend dependencies
npm install

# Install Python dependencies
pip install -r requirements.txt

# Configure your API key (choose one method)
# Method 1: Create .env file
cp .env.example .env
# Edit .env and add your API key

# Method 2: Configure via the app's Settings UI after launch

# Start development server
./start.sh
# Or manually:
# Terminal 1: python -m uvicorn backend.server:app --host 127.0.0.1 --port 8765
# Terminal 2: npm run tauri dev
```

## Building

```bash
# Build the Python sidecar
pip install pyinstaller
python -m PyInstaller trasource-backend.spec --clean --noconfirm

# Copy sidecar to Tauri binaries
cp dist/trasource-backend src-tauri/binaries/trasource-backend-$(rustc -vV | grep host | awk '{print $2}')

# Build the app
npm run tauri build

# Output: src-tauri/target/release/bundle/
```

## Supported Document Formats

| Format | Type | Notes |
|--------|------|-------|
| CSV | Newspapers | Auto-parses date, page, title, content columns |
| PDF | Books, papers | Text extraction via pdfplumber |
| DOCX | Books, papers | Paragraph-level chunking |
| TXT | Any | Plain text import |
| EPUB | Books | Chapter-aware extraction |
| MOBI/AZW3 | Books | Kindle format support |

## Configuration

All configuration is done through the **Settings** UI within the app:

- **AI Provider** — Select Gemini, Claude, ChatGPT, or local model
- **API Keys** — Stored locally in `settings.json`, never uploaded
- **Model Selection** — Choose models for keyword analysis and document extraction independently
- **Custom Prompts** — Override the AI prompts for query expansion and extraction
- **Local Models** — Connect to Ollama, vLLM, or any OpenAI-compatible API

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
└── requirements.txt        # Python dependencies
```

## License

AGPL

## Contributing

Contributions are welcome. Please open an issue first to discuss what you would like to change.
