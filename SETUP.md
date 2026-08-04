# Developer Setup

## Prerequisites

- **Python 3.11+** (check: `python3 --version`)
- **Node.js 20+** (check: `node --version`)
- **Git** (check: `git --version`)
- **Make** (optional, for convenience commands)

## Quick Start

### 1. Clone and setup backend

```bash
git clone https://github.com/aniketshaw29/Developer-document-assistant.git
cd Developer-document-assistant

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # macOS/Linux

# Install dependencies
cd backend
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys
```

### 2. Setup frontend

```bash
cd frontend
npm install
```

### 3. Run

```bash
# Terminal 1 — Backend
cd backend
uvicorn app.main:app --reload --port 8000

# Terminal 2 — Frontend
cd frontend
npm run dev
```

Open http://localhost:5173

## Environment Variables

```bash
# backend/.env

# Required (at least one)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Optional — Ollama (no key needed, runs locally)
OLLAMA_BASE_URL=http://localhost:11434

# Optional — Configuration
DEFAULT_PROVIDER=openai          # openai | anthropic | ollama
DEFAULT_MODEL=gpt-4o             # Model name for default provider
EMBEDDING_MODEL=text-embedding-3-small
CHROMA_PERSIST_DIR=./data/chroma
LOG_LEVEL=info
CORS_ORIGINS=http://localhost:5173
```

## Requirements

### backend/requirements.txt

```
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
pydantic>=2.0
pydantic-settings>=2.0
python-dotenv>=1.0
llama-index-core>=0.14.0
llama-index-llms-openai>=0.4.0
llama-index-llms-anthropic>=0.4.0
llama-index-llms-ollama>=0.4.0
llama-index-embeddings-openai>=0.4.0
llama-index-embeddings-ollama>=0.4.0
llama-index-vector-stores-chroma>=0.4.0
litellm>=1.40.0
chromadb>=0.5.0
PyMuPDF>=1.24.0
gitpython>=3.1.0
pyyaml>=6.0
httpx>=0.27.0
python-multipart>=0.0.9
```

### frontend/package.json (key deps)

```json
{
  "dependencies": {
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "react-markdown": "^9.0.0",
    "react-syntax-highlighter": "^15.5.0",
    "lucide-react": "^0.400.0"
  },
  "devDependencies": {
    "typescript": "^5.5.0",
    "@types/react": "^18.3.0",
    "vite": "^5.4.0",
    "@vitejs/plugin-react": "^4.3.0",
    "tailwindcss": "^3.4.0",
    "autoprefixer": "^10.4.0",
    "postcss": "^8.4.0"
  }
}
```

## Available Commands

```bash
# Backend
make dev-backend     # Run backend with auto-reload
make install-backend # Install Python dependencies

# Frontend
make dev-frontend    # Run frontend dev server
make install-frontend # Install Node dependencies

# Both
make dev             # Run both backend and frontend
make install         # Install all dependencies
```

## Troubleshooting

### "No module named 'tree_sitter'"
```bash
pip install tree-sitter-languages
```

### ChromaDB errors
Delete the local database and restart:
```bash
rm -rf data/chroma
```

### Ollama not connecting
Make sure Ollama is running:
```bash
ollama serve
ollama pull llama3.1
ollama pull nomic-embed-text
```

### CORS errors
Ensure `CORS_ORIGINS` in `.env` matches your frontend URL (default: `http://localhost:5173`).

### Port conflicts
Backend runs on 8000, frontend on 5173. Change in uvicorn/vite config if needed.
