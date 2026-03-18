#!/usr/bin/env python3
import chromadb
import sqlite3
from sentence_transformers import SentenceTransformer

def simple_text_splitter(text, chunk_size=1000, overlap=200):
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = words[i:i + chunk_size]
        chunks.append(' '.join(chunk))
        i += chunk_size - overlap
    return chunks


def populate_vector_db():
    print("Loading embedding model...")
    model = SentenceTransformer('all-MiniLM-L6-v2')

    print("Connecting to SQLite database...")
    conn = sqlite3.connect('manuales_ai.db')
    cursor = conn.cursor()

    print("Initializing ChromaDB...")
    client = chromadb.PersistentClient(path="./chroma_db")
    collection = client.get_or_create_collection("man_pages")

    print("Processing man pages...")
    cursor.execute("SELECT comando, seccion_nombre, raw_man_text FROM man_pages")
    rows = cursor.fetchall()
    print(f"Found {len(rows)} man pages to process.")

    for i, row in enumerate(rows):
        command, section, text = row
        print(f"Processing {i+1}/{len(rows)}: {command} - {section}")
        
        # Split into chunks
        chunks = simple_text_splitter(text, chunk_size=1000, overlap=200)
        print(f"  Split into {len(chunks)} chunks")
        
        if chunks:
            # Generate embeddings
            embeddings = model.encode(chunks)
            
            # Add to vector DB
            collection.add(
                embeddings=embeddings.tolist(),
                documents=chunks,
                metadatas=[{"command": command, "section": section, "chunk_idx": j} for j in range(len(chunks))],
                ids=[f"{command}_{section}_{j}" for j in range(len(chunks))]
            )

    conn.close()
    print("Vector DB populated successfully!")


if __name__ == "__main__":
    populate_vector_db()