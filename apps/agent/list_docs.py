
from typing import Optional, Dict, List
from langchain_core.documents import Document
from langchain_chroma import Chroma
from database import get_vector_db

def get_all_documents_from_db(limit: Optional[int] = None, offset: Optional[int] = None) -> Dict:
    """
    Get all documents from the ChromaDB vector database.
    
    Args:
        limit: The number of documents to return. If None, returns all documents.
        offset: The offset to start returning results from. Useful for paging results with limit.
        
    Returns:
        A dict with keys: 'ids', 'embeddings', 'metadatas', 'documents'
        Example:
        {
            'ids': ['id1', 'id2', ...],
            'metadatas': [{...}, {...}, ...],
            'documents': ['doc1', 'doc2', ...],
            'embeddings': [[...], [...], ...]  # if included
        }
    """
    vectorstore = get_vector_db()
    
    result = vectorstore.get(
        ids=None,  
        where=None, 
        limit=limit,
        offset=offset,
        include=["metadatas", "documents"]
    )
    
    return result


def get_all_documents_as_langchain_docs() -> List[Document]:
    """
    Get all documents from ChromaDB and convert them to LangChain Document objects.
    
    Returns:
        List of Document objects with page_content and metadata
    """
    result = get_all_documents_from_db()
    
    documents = []
    for i, doc_id in enumerate(result.get('ids', [])):
        doc_content = result.get('documents', [])[i] if i < len(result.get('documents', [])) else ""
        doc_metadata = result.get('metadatas', [])[i] if i < len(result.get('metadatas', [])) else {}
        
        documents.append(Document(
            page_content=doc_content,
            metadata=doc_metadata
        ))
    
    return documents

# Get all documents as raw dict
all_docs = get_all_documents_from_db()
print(f"Total documents: {len(all_docs['ids'])}")

# Get all documents as LangChain Document objects
docs = get_all_documents_as_langchain_docs()
for doc in docs:
    print(f"Position: {doc.metadata.get('position_name')}")
    print(f"Company: {doc.metadata.get('company')}")