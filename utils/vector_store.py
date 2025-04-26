"""
Utility functions for initializing and working with Pinecone vector store.
"""
import os
import logging
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from langchain_pinecone import PineconeVectorStore
from langchain_openai import OpenAIEmbeddings
from pinecone import Pinecone

# Configure logging
logger = logging.getLogger(__name__)

def initialize_vector_store() -> PineconeVectorStore:
    """
    Initialize the Pinecone vector store with OpenAI embeddings
    
    Returns:
        PineconeVectorStore: Initialized vector store for similarity search
    """
    # Load environment variables
    load_dotenv()
    
    # Get API keys
    pinecone_api_key = os.getenv("PINECONE_API_KEY")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    index_name = os.getenv("PINECONE_INDEX", "amo-events")
    
    if not pinecone_api_key:
        raise ValueError("PINECONE_API_KEY not found in environment variables")
    
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables")
    
    logger.info(f"Initializing Pinecone with index: {index_name}")
    
    # Initialize Pinecone
    pc = Pinecone(api_key=pinecone_api_key)
    
    # Initialize embeddings
    embeddings = OpenAIEmbeddings(
        openai_api_key=openai_api_key,
        model="text-embedding-ada-002"
    )
    
    # Create vector store
    vector_store = PineconeVectorStore(
        index=pc.Index(index_name),
        embedding=embeddings,
        text_key="text"
    )
    
    return vector_store

def search_vector_store(
    query: str,
    vector_store: PineconeVectorStore,
    namespace: Optional[str] = None,
    filter_dict: Optional[Dict[str, Any]] = None,
    top_k: int = 5
):
    """
    Search the vector store with a query
    
    Args:
        query (str): The search query
        vector_store (PineconeVectorStore): The vector store to search
        namespace (Optional[str]): Specific namespace to search in
        filter_dict (Optional[Dict[str, Any]]): Additional filters
        top_k (int): Number of results to return
        
    Returns:
        List of (document, score) tuples
    """
    # Prepare the filter
    search_filter = {}
    
    if namespace:
        search_filter["namespace"] = namespace
    
    if filter_dict:
        search_filter.update(filter_dict)
    
    # If no filters, set to None
    if not search_filter:
        search_filter = None
    
    # Perform the search
    results = vector_store.similarity_search_with_score(
        query=query,
        k=top_k,
        filter=search_filter
    )
    
    return results 