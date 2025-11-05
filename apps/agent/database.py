# Vector database configuration
import os
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings


VECTOR_DB_PATH = os.path.join(os.path.dirname(__file__), "chroma_db")
COLLECTION_NAME = "job_descriptions"


# Initialize embeddings model (using Ollama)
_embeddings = None

def get_embeddings():
    """Get or create embeddings model instance."""
    global _embeddings
    if _embeddings is None:
        _embeddings = OllamaEmbeddings(model="nomic-embed-text")
    return _embeddings

def get_vector_db():
    """
    Initialize and return ChromaDB vector database instance.
    
    Returns:
        Chroma vector store instance
    """
    embeddings = get_embeddings()
    return Chroma(
        persist_directory=VECTOR_DB_PATH,
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings
    )
