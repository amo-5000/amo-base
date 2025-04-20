#!/usr/bin/env python3
"""
AMO Knowledge Base Query Script

This script allows users to query a knowledge base about AMO events platform
development practices. It uses:
- Pinecone for vector storage of documents
- OpenAI for embeddings and completions
- LangChain for the retrieval QA chain

Usage:
    python query.py "How do I connect Webflow forms to Airtable?"
"""

import os
import sys
import time
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Import LangChain components
from langchain.chains import RetrievalQA
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.llms import OpenAI
from langchain.vectorstores import Pinecone

# Import custom prompts
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.prompts import QA_PROMPT

# Import Pinecone
try:
    import pinecone
except ImportError:
    print("Error: Pinecone package not installed. Run 'pip install pinecone-client'")
    sys.exit(1)

def load_environment_variables() -> Dict[str, str]:
    """
    Load environment variables from .env file.
    
    Returns:
        Dict[str, str]: Dictionary of required environment variables
    
    Raises:
        ValueError: If any required environment variables are missing
    """
    # Load environment variables from .env file
    load_dotenv()
    
    # Required environment variables
    required_vars = {
        'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY'),
        'PINECONE_API_KEY': os.getenv('PINECONE_API_KEY'),
        'PINECONE_INDEX': os.getenv('PINECONE_INDEX')
    }
    
    # Check for missing environment variables
    missing_vars = [var for var, value in required_vars.items() if not value]
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    return required_vars

def initialize_pinecone(api_key: str) -> None:
    """
    Initialize Pinecone with API key.
    
    Args:
        api_key (str): Pinecone API key
    
    Raises:
        ConnectionError: If connection to Pinecone fails
    """
    try:
        # As of January 2024, Pinecone no longer requires environment parameter
        pinecone.init(api_key=api_key)
    except Exception as e:
        raise ConnectionError(f"Failed to initialize Pinecone: {str(e)}")

def create_retrieval_qa_chain(index_name: str) -> Optional[RetrievalQA]:
    """
    Create a retrieval QA chain using Pinecone and OpenAI.
    
    Args:
        index_name (str): Name of the Pinecone index
    
    Returns:
        Optional[RetrievalQA]: The retrieval QA chain if successful, None otherwise
    
    Raises:
        ValueError: If index_name is not found in Pinecone
    """
    try:
        # Check if index exists
        if index_name not in pinecone.list_indexes():
            raise ValueError(f"Index '{index_name}' not found in Pinecone")
        
        # Initialize OpenAI embeddings
        embeddings = OpenAIEmbeddings()
        
        # Initialize Pinecone vector store
        vectorstore = Pinecone.from_existing_index(
            index_name=index_name,
            embedding=embeddings
        )
        
        # Create retriever
        retriever = vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 5}
        )
        
        # Create LLM
        llm = OpenAI(temperature=0, model_name="gpt-4")
        
        # Create RetrievalQA chain
        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=retriever,
            chain_type_kwargs={"prompt": QA_PROMPT}
        )
        
        return qa_chain
    
    except Exception as e:
        print(f"Error creating retrieval QA chain: {str(e)}")
        return None

def format_response(query: str, response: Dict[str, Any]) -> str:
    """
    Format the response from the QA chain into a readable string.
    
    Args:
        query (str): The original query
        response (Dict[str, Any]): The response from the QA chain
    
    Returns:
        str: Formatted response
    """
    formatted_response = f"""
{'=' * 80}
QUERY: {query}
{'=' * 80}

{response['result']}
"""
    return formatted_response

def main():
    """Main function to run the query script."""
    # Check if a query was provided as a command-line argument
    if len(sys.argv) < 2:
        print("Usage: python query.py \"Your question about AMO events platform here\"")
        sys.exit(1)
    
    # Get query from command-line argument
    query = sys.argv[1]
    
    try:
        # Load environment variables
        env_vars = load_environment_variables()
        
        # Initialize Pinecone
        initialize_pinecone(env_vars['PINECONE_API_KEY'])
        
        # Print status message
        print(f"Connecting to Pinecone index '{env_vars['PINECONE_INDEX']}'...")
        
        # Create retrieval QA chain
        qa_chain = create_retrieval_qa_chain(env_vars['PINECONE_INDEX'])
        if not qa_chain:
            print("Failed to create retrieval QA chain. Please check your environment variables and Pinecone setup.")
            sys.exit(1)
        
        # Run query
        print(f"Querying: \"{query}\"...")
        start_time = time.time()
        response = qa_chain({"query": query})
        end_time = time.time()
        
        # Print formatted response
        print(format_response(query, response))
        print(f"Response time: {end_time - start_time:.2f} seconds")
    
    except ValueError as e:
        print(f"Error: {str(e)}")
        sys.exit(1)
    except ConnectionError as e:
        print(f"Connection error: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
