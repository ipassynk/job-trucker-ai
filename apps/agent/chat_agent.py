import os
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_ollama import ChatOllama
from langchain_core.output_parsers import StrOutputParser
from .database import get_vector_db


def create_jobs_agent():
    """
    Create a RAG agent that can only answer questions about jobs stored in the vector database.
    
    Returns:
        A JobsAgent instance that can be invoked with {"input": "question"} format
    """
    # Get the vector database
    vectorstore = get_vector_db()
    
    # Create a retriever from the vector store
    retriever = vectorstore.as_retriever(
        search_kwargs={"k": 5}  # Retrieve top 5 most relevant jobs
    )
    
    # Initialize LLM (using Ollama)
    ollama_model = os.getenv("OLLAMA_MODEL", "llama3.2")
    llm = ChatOllama(
        model=ollama_model,
        temperature=0.7,
    )
    
    # Create a prompt template that restricts the agent to only talk about jobs in the database
    system_prompt = """You are a helpful assistant that answers questions about job postings. 
You can ONLY answer questions about jobs that are stored in the database. 
If a question is asked about a job that is not in the database, politely inform the user that you can only discuss jobs that are saved in the database.

When answering questions about jobs:
- Use the context provided from the retrieved job documents
- Include relevant details like position name, company, salary, and job description
- If multiple jobs match the query, mention all relevant ones
- The retrieved jobs are semantically related to the query - present them even if the exact query term isn't explicitly mentioned in the description
- If a job is semantically related but doesn't explicitly mention the query term, you can say: "I found a related position: [position name] at [company]"
- Be accurate and only provide information that is in the retrieved context
- If you don't have enough information in the context to answer a question, say so

NEVER make up or hallucinate information about jobs. Only use information from the retrieved documents.
If jobs were retrieved, they are relevant to the query even if the exact wording isn't present - present them to the user.

Use the following context from the job database to answer the question:

{context}"""

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("human", "{input}")
    ])
    
    def format_docs(docs):
        """Format the retrieved documents for context."""
        if not docs:
            return "No jobs found in the database matching the query."
        formatted = []
        for i, doc in enumerate(docs, 1):
            metadata = doc.metadata
            formatted.append(f"""
Job {i}:
Position: {metadata.get('position_name', 'N/A')}
Company: {metadata.get('company', 'N/A')}
Salary: {metadata.get('salary', 'Not specified')}
URL: {metadata.get('url', 'N/A')}
Description: {doc.page_content[:1000]}...
""")
        return "\n".join(formatted)
    
    # Create the prompt and LLM chain
    chain = prompt | llm | StrOutputParser()
    
    # Wrap it to match the expected interface (takes {"input": "question"})
    def invoke_wrapper(input_dict):
        """Wrapper to handle the input format expected by the chat interface."""
        user_input = input_dict.get("input", "")
        # Retrieve relevant documents
        docs = retriever.invoke(user_input)
        # Format documents
        formatted_context = format_docs(docs)
        # Invoke the chain
        result = chain.invoke({
            "context": formatted_context,
            "input": user_input,
            "chat_history": input_dict.get("chat_history", [])
        })
        return result
    
    class JobsAgent:
        """Wrapper class for the jobs agent."""
        def invoke(self, input_dict):
            return invoke_wrapper(input_dict)
        
        def stream(self, input_dict):
            """Stream responses if needed."""
            user_input = input_dict.get("input", "")
            docs = retriever.invoke(user_input)
            formatted_context = format_docs(docs)
            return chain.stream({
                "context": formatted_context,
                "input": user_input,
                "chat_history": input_dict.get("chat_history", [])
            })
    
    return JobsAgent()


# Create the agent instance
agent = create_jobs_agent()

