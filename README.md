# Unix Command Explainer (RAG + Ollama)

This project uses a local man-page SQLite database and a Retrieval-Augmented Generation (RAG) pipeline to answer natural language questions about Unix commands.

It works by:
1. Extracting relevant chunks from man pages using a vector database (ChromaDB + sentence-transformers embeddings).
2. Asking an LLM (via Ollama) to answer the question using the retrieved chunks.

---

## ✅ Prerequisites

- Python 3.10+ (the project runs in a venv)
- A working Ollama installation and server running at `http://localhost:11434`
- A local SQLite DB file named `manuales_ai.db` containing a `man_pages` table.

> **Note:** Ollama should have a model installed that you reference in `explain.py` (default is `llama3.1:8b`).

---

## 1) Set up the Python environment

```bash
cd /path/to/ia_capstone
python -m venv ia_capstone
# Activate the venv (Windows PowerShell)
./ia_capstone/Scripts/Activate.ps1
# MacOS
source ia_capstone/bin/activate

# Install dependencies
python -m pip install -r requirements.txt
```

---

## 2) Populate the vector database (RAG)

This step reads the `manuales_ai.db` man pages and creates a ChromaDB vector store with embeddings.

```bash
python populate_vector_db.py
```

If it completes successfully, you should see a `chroma_db/chroma.sqlite3` file.

---

## 3) Run the explainer

Ask a question about a Unix command:

```bash
python explain.py "what parameter can i use to list hidden files in ls?"
```

The script will:
1. Rephrase the question for better LLM understanding
2. Extract the command using the LLM
3. Retrieve relevant man page chunks from ChromaDB
4. Generate and verify an answer using Ollama
5. If the level of alucination is high, it will refuse to answer.

---

## Troubleshooting

### `embeddings.position_ids | UNEXPECTED |` warning
This is a harmless warning from the HuggingFace model loader and can be ignored.

### Ollama errors / model not found
If you get a model-not-found error, ensure the model name in `explain.py` matches an installed Ollama model (e.g. `llama3.1:8b`).

### No vectors found in `chroma_db`
If the vector DB is empty, rerun:
```bash
python populate_vector_db.py
```

---

## Notes

- `populate_vector_db.py` uses `sentence-transformers` to create embeddings.
- `explain.py` uses Ollama for LLM generation and verification.

Enjoy exploring Unix commands with RAG-powered explanations! 🎯
