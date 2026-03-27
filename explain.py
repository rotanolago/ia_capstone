#!/usr/bin/env python3
import os
from dotenv import load_dotenv
import sys
import sqlite3
import requests
import chromadb
from sentence_transformers import SentenceTransformer
from transformers import logging as hf_logging

# Load .env file (if present)
load_dotenv()

# Use environment variable to select Ollama model
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")

# Initialize models and DB (lazy load in main to avoid import issues)
model = None
collection = None

hf_logging.set_verbosity_error()

def initialize_rag():
    global model, collection
    if model is None:
        print("Loading embedding model...")
        model = SentenceTransformer('all-MiniLM-L6-v2')
    if collection is None:
        print("Connecting to ChromaDB...")
        client = chromadb.PersistentClient(path="./chroma_db")
        try:
            collection = client.get_collection("man_pages")
        except:
            print("Vector database not found. Please run populate_vector_db.py first.")
            sys.exit(1)

def retrieve_relevant_chunks(question, command=None, top_k=5):
    initialize_rag()
    # Embed the question
    question_embedding = model.encode([question])[0]
    
    # Search vector DB
    where_clause = {"command": command} if command else None
    results = collection.query(
        query_embeddings=[question_embedding.tolist()],
        n_results=top_k,
        where=where_clause
    )
    
    return results['documents'][0] if results['documents'] else []

def get_man_text(command):
    conn = sqlite3.connect('manuales_ai.db')
    cursor = conn.cursor()
    cursor.execute('SELECT raw_man_text FROM man_pages WHERE comando = ? AND seccion_nombre = "FULL_TEXT" LIMIT 1', (command,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def generate_explanation(context, question):
    prompt = f"Based on the following man page excerpts, answer this question: {question}\n\n{context}\n\nAnswer:"
    data = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.5}
    }
    response = requests.post("http://localhost:11434/api/generate", json=data)
    if response.status_code == 200:
        return response.json()["response"].strip()
    else:
        raise Exception(f"Ollama error: {response.text}")

def rephrase_question(question):
    prompt = f"Rephrase this question about Unix commands to make it clearer or more specific do not offer any suggestions, only sentence: {question}\n\nRephrased question:"
    data = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.7}  # Slightly higher temperature for variety
    }
    response = requests.post("http://localhost:11434/api/generate", json=data)
    if response.status_code == 200:
        return response.json()["response"].strip()
    else:
        return question  # Fallback to original if rephrasing fails

def verify_answer(context, question, answer):
    prompt = f"Based on the following man page excerpts, rate from 0 to 100 how accurate and well-supported is this answer to the question. Question: {question}\nAnswer: {answer}\n\nMan page excerpts:\n{context}\n\nRespond with only a number from 0 to 100, nothing else."
    data = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.1}
    }
    response = requests.post("http://localhost:11434/api/generate", json=data)
    if response.status_code == 200:
        result = response.json()["response"].strip()
        try:
            score = int(result)
        except ValueError:
            score = 0
        return score
    else:
        return 0  # Assume 0 if error

def extract_command_with_llm(question):
    prompt = f"Extract the Unix command from this question about Unix commands. Return only the command name, nothing else: {question}\n\nCommand:"
    data = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.0}  # Deterministic extraction
    }
    response = requests.post("http://localhost:11434/api/generate", json=data)
    if response.status_code == 200:
        command = response.json()["response"].strip()
        return command
    else:
        raise Exception(f"Ollama error: {response.text}")

def main():
    print("Welcome to the Unix Command Explainer!")
    if len(sys.argv) < 2:
        print("Usage: python explain.py <question about a Unix command>")
        sys.exit(1)
    original_question = ' '.join(sys.argv[1:])
    print(f"Your question: {original_question}")
    
    print("Optimizing question for LLM...")
    try:
        optimized_question = rephrase_question(original_question)
        print(f"Optimized question: {optimized_question}")
    except Exception as e:
        print(f"Error optimizing question: {e}")
        optimized_question = original_question  # Fallback
    
    # Extract command from optimized question using LLM
    try:
        command = extract_command_with_llm(optimized_question)
        print(f"Extracted command: {command}")
    except Exception as e:
        print(f"Error extracting command: {e}")
        sys.exit(1)
    
    print("Retrieving relevant man page chunks...")
    relevant_chunks = retrieve_relevant_chunks(optimized_question, command, top_k=5)
    if not relevant_chunks:
        print(f"No relevant chunks found for command '{command}'.")
        sys.exit(1)
    context = "\n\n".join(relevant_chunks)
    
    for attempt in range(3):
        current_question = optimized_question if attempt == 0 else rephrase_question(optimized_question)
        print(f"\nAttempt {attempt + 1}: Using question: {current_question}")

        print("Generating answer...")
        try:
            answer = generate_explanation(context, current_question)
        except Exception as e:
            print(f"Error generating answer: {e}")
            sys.exit(1)

        print("Verifying answer against man page...")
        quality_score = verify_answer(context, current_question, answer)
        if quality_score >= 80:
            print("Answer verified as accurate.")
            print(answer)
            return  # Exit after successful verification
        else:
            print(f"Prompt answer quality: {quality_score}%")

        print("Answer not accurate enough. Rephrasing question..." if attempt < 2 else "Answer not accurate after 3 attempts.")
    
    print("I don't know.")

if __name__ == "__main__":
    main()
