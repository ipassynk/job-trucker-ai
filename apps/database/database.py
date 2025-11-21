# Vector database configuration
import os
from pathlib import Path
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings

# Get VECTOR_DB_PATH from environment variable, with fallback to relative path
# In Docker, this should be set to an absolute path like /opt/airflow/chroma_db
# For local development, it defaults to a directory relative to this file
_default_vector_db_path = os.path.join(os.path.dirname(__file__), "chroma_db")
VECTOR_DB_PATH = os.getenv("VECTOR_DB_PATH", _default_vector_db_path)
COLLECTION_NAME = "job_descriptions"


# Initialize embeddings model (using Ollama)
_embeddings = None

def get_embeddings():
    """Get or create embeddings model instance."""
    global _embeddings
    if _embeddings is None:
        # Support custom Ollama base URL for Docker/remote connections
        base_url = os.getenv("OLLAMA_BASE_URL")
        kwargs = {"model": "nomic-embed-text"}
        if base_url:
            kwargs["base_url"] = base_url
        _embeddings = OllamaEmbeddings(**kwargs)
    return _embeddings

def get_vector_db():
    """
    Initialize and return ChromaDB vector database instance.
    If the database already exists, returns the existing instance.
    Otherwise, creates a new database.
    
    Returns:
        Chroma vector store instance
    """
    embeddings = get_embeddings()
    
    db_exists = (
        os.path.exists(VECTOR_DB_PATH) 
        and os.path.isdir(VECTOR_DB_PATH) 
        and len(os.listdir(VECTOR_DB_PATH)) > 0
    )
    
    if db_exists:
        return Chroma(
            persist_directory=VECTOR_DB_PATH,
            collection_name=COLLECTION_NAME,
            embedding_function=embeddings
        )
    else:
        return Chroma(
            persist_directory=VECTOR_DB_PATH,
            collection_name=COLLECTION_NAME,
            embedding_function=embeddings
        )
