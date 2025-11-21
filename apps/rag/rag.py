import json
import os
import sys
from datetime import datetime
from typing import Optional, List, Dict
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from bs4 import BeautifulSoup
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_core.output_parsers import PydanticOutputParser
from langchain_chroma import Chroma
from langchain_core.documents import Document

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from apps.database import get_vector_db

# Load .env from project root (../../.env relative to this file)
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)


class JobInfo(BaseModel):
    """Structured output for job information extraction."""

    position_name: str = Field(description="The job title or position name")
    position_description: str = Field(description="The detailed job description")
    company: str = Field(description="The company name offering the position")
    salary: Optional[str] = Field(
        default=None, description="Salary information if available"
    )


def parse_html_with_bs4(html_content: str) -> str:
    """
    Parse HTML content using BeautifulSoup to extract text content.

    Args:
        html_content: Raw HTML string

    Returns:
        Extracted text content from HTML
    """
    soup = BeautifulSoup(html_content, "html.parser")

    # Remove non-content elements (scripts, styles, navigation, forms, media, etc.)
    elements_to_remove = [
        "script", "style", "meta", "link", 
        "nav", "header", "footer", "aside",  
        "form", "button", "input", "select", "textarea", 
        "iframe", "svg", "img", "canvas", "audio", "video", "embed", "object", 
        "noscript", "template",
    ]
    for element in soup(elements_to_remove):
        element.decompose()

    # Get text content
    text = soup.get_text(separator=" ", strip=True)

    # Clean up whitespace
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = " ".join(chunk for chunk in chunks if chunk)

    return text


def extract_job_info(json_file_path: str) -> JobInfo:
    """
    Read a JSON file containing job HTML, extract the HTML content,
    and use LangChain to parse and extract job information.

    Args:
        json_file_path: Path to the JSON file containing url and html fields

    Returns:
        JobInfo object with extracted job information
    """
    # Read the JSON file
    with open(json_file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    html_content = data.get("html", "")
    url = data.get("url", "")

    if not html_content:
        raise ValueError("No HTML content found in the JSON file")

    # Parse HTML using BeautifulSoup
    html_text = parse_html_with_bs4(html_content)
    print(f"HTML text length: {len(html_text)} characters")

    # Initialize LLM (using Ollama - ensure Ollama is running locally or accessible)
    # Default model is "llama3.2" but can be changed via environment variable
    ollama_model = os.getenv("OLLAMA_MODEL", "llama3.2")
    ollama_base_url = os.getenv("OLLAMA_BASE_URL")
    # Get timeout from environment (default 5 minutes for large HTML processing)
    ollama_timeout = int(os.getenv("OLLAMA_TIMEOUT", "300"))  # 5 minutes default
    
    llm_kwargs = {
        "model": ollama_model,
        "temperature": 0,
        "model_kwargs": {
            "num_predict": 4096,
            "num_ctx": 4096,
        },
        "verbose": True,
        "timeout": ollama_timeout,  # Add timeout to prevent hanging
    }
    if ollama_base_url:
        llm_kwargs["base_url"] = ollama_base_url
    llm = ChatOllama(**llm_kwargs)

    # Create output parser
    parser = PydanticOutputParser(pydantic_object=JobInfo)

    # Create prompt template
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """You are an expert at extracting job information from HTML content.
        
        IMPORTANT: Extract information for ONLY ONE job posting. If the HTML contains multiple job listings, 
        extract the PRIMARY job that matches the URL or the most prominent job in the content.
        All fields must be SINGLE STRING VALUES, not arrays or lists.
        
        Extract the following information from the provided HTML:
        - position_name: The job title or position name (single string, not a list)
        - position_description: The full job description. Do not truncate the description. (single string, not a list)
        - company: The company name (single string, not a list)
        - salary: Salary information if available (leave as None if not found). Look for "Salary" or "Compensation" or any info that has CA or dollar sign. (single string or None, not a list)
        
        Here are examples of salary information:
        - Salary: $100,000 - $120,000 per year
        - Compensation: $100,000 - $120,000 per year
        - Salary: $100,000 - $120,000 per year
        - CA$90/hr - CA$100/hr
        - CA$120K/yr - CA$175K/yr

        {format_instructions}
        
        Focus on extracting accurate information from the HTML structure. Return only ONE job as a single object with string values.""",
            ),
            (
                "human",
                """Extract job information from the following HTML content:
        
        {html_content}
        
        URL: {url}
        """,
            ),
        ]
    ).partial(format_instructions=parser.get_format_instructions())

    # Create chain
    chain = prompt | llm | parser

    # Limit content to avoid token limits
    truncated_html = html_text[:80000] if len(html_text) > 80000 else html_text

    # Extract information
    print(f"Invoking LLM chain with timeout of {ollama_timeout} seconds...")
    print(f"HTML content length: {len(truncated_html)} characters")
    print(f"Ollama model: {ollama_model}, base_url: {ollama_base_url or 'default'}")
    
    try:
        print("Starting LLM chain invocation...")
        result = chain.invoke({"html_content": truncated_html, "url": url})
        
    except Exception as e:
        import traceback
        print(f"Full traceback:\n{traceback.format_exc()}")
        raise

    return result


def save_job_to_vector_db(
    job_info: JobInfo, url: str, timestamp: Optional[str] = None
) -> str:
    """
    Save job description to vector database with metadata.

    Args:
        job_info: JobInfo object containing extracted job information
        url: URL of the job posting
        timestamp: Timestamp string (defaults to current time if not provided)

    Returns:
        Document ID of the saved job
    """
    if timestamp is None:
        timestamp = datetime.now().isoformat()

    # Create vector database instance
    vectorstore = get_vector_db()

    # print the job info
    print(f"URL: {url}")
    print(f"Timestamp: {timestamp}")
    print(f"Position Name: {job_info.position_name}")
    print(f"Company: {job_info.company}")
    print(f"Salary: {job_info.salary or 'Not specified'}")
    print(f"Position Description: {job_info.position_description}")

    # Create document with job description and metadata
    document = Document(
        page_content=job_info.position_description,
        metadata={
            "url": url,
            "time": timestamp,
            "position_name": job_info.position_name,
            "company": job_info.company,
            "salary": job_info.salary or "Not specified",
            "position_description": job_info.position_description,
        },
    )

    # Add document to vector store
    ids = vectorstore.add_documents([document])

    return ids[0] if ids else None


if __name__ == "__main__":
    # FIXME
    json_file_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "server",
        "jobs",
        "2025-11-18_15-29-31.json",
    )

    try:
        with open(json_file_path, "r", encoding="utf-8") as f:
            json_data = json.load(f)

        url = json_data.get("url", "")
        timestamp = json_data.get("date", datetime.now().isoformat())

        # Extract job information
        job_info = extract_job_info(json_file_path)
        print("\n" + "=" * 50)
        print("EXTRACTED JOB INFORMATION")
        print("=" * 50)
        print(f"\nPosition Name: {job_info.position_name}")
        print(f"\nCompany: {job_info.company}")
        print(f"\nSalary: {job_info.salary or 'Not specified'}")
        print(f"\nPosition Description:\n{job_info.position_description[:500]}...")
        print("\n" + "=" * 50)

        # Save to vector database
        print("\n" + "=" * 50)
        print("SAVING TO VECTOR DATABASE")
        print("=" * 50)
        doc_id = save_job_to_vector_db(job_info, url, timestamp)
        print(f"Job description saved to vector database with ID: {doc_id}")

        # Also output as JSON
        print("\nJSON Output:")
        print(json.dumps(job_info.model_dump(), indent=2, ensure_ascii=False))

    except Exception as e:
        print(f"Error extracting job information: {e}")
        raise
