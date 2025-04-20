#!/usr/bin/env python3
"""
AMO Knowledge Base Chat Interface

This script provides an interactive chat interface for the AMO events platform
knowledge base. It maintains conversation history for contextual follow-up questions.

Features:
- Maintains conversation history for context
- Uses Pinecone for vector storage of documents
- Uses OpenAI for embeddings and language model
- Allows for natural follow-up questions

Usage:
    python chat.py
"""

import os
import sys
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Import LangChain components
from langchain.chains import ConversationalRetrievalChain
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.llms import OpenAI
from langchain.memory import ConversationBufferMemory
from langchain.vectorstores import Pinecone

# Import custom prompts
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.prompts import AMO_SYSTEM_PROMPT

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
    # Load environment variables
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

def create_conversational_chain(index_name: str) -> Optional[ConversationalRetrievalChain]:
    """
    Create a conversational retrieval chain using Pinecone and OpenAI.
    
    Args:
        index_name (str): Name of the Pinecone index
    
    Returns:
        Optional[ConversationalRetrievalChain]: The conversational chain if successful, None otherwise
    
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
        
        # Create memory
        memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        
        # Create LLM
        llm = OpenAI(temperature=0, model_name="gpt-4")
        
        # Create ConversationalRetrievalChain
        conversational_chain = ConversationalRetrievalChain.from_llm(
            llm=llm,
            retriever=retriever,
            memory=memory,
            condense_question_prompt=AMO_SYSTEM_PROMPT
        )
        
        return conversational_chain
    
    except Exception as e:
        print(f"Error creating conversational chain: {str(e)}")
        return None

def interactive_chat(chain: ConversationalRetrievalChain) -> None:
    """
    Run an interactive chat session with the given conversational chain.
    
    Args:
        chain (ConversationalRetrievalChain): The conversational retrieval chain
    """
    print("\n" + "=" * 80)
    print("Welcome to the AMO Events Platform Knowledge Assistant!")
    print("Ask questions about integrating Webflow, Airtable, Xano, n8n, and WhatsApp API.")
    print("Type 'exit' or 'quit' to end the session.")
    print("=" * 80 + "\n")
    
    while True:
        # Get user input
        query = input("\nQuestion: ")
        
        # Check if user wants to exit
        if query.lower() in ['exit', 'quit', 'q']:
            print("\nThank you for using the AMO Knowledge Assistant. Goodbye!")
            break
        
        # Skip empty queries
        if not query.strip():
            continue
        
        try:
            # Run query through the chain
            response = chain({"question": query})
            
            # Print response
            print("\nAssistant:", response['answer'])
        
        except Exception as e:
            print(f"\nError processing your question: {str(e)}")
            print("Please try again or rephrase your question.")

def main():
    """Main function to run the chat interface."""
    try:
        # Load environment variables
        env_vars = load_environment_variables()
        
        # Initialize Pinecone
        initialize_pinecone(env_vars['PINECONE_API_KEY'])
        
        # Print status message
        print(f"Connecting to Pinecone index '{env_vars['PINECONE_INDEX']}'...")
        
        # Create conversational chain
        conversational_chain = create_conversational_chain(env_vars['PINECONE_INDEX'])
        if not conversational_chain:
            print("Failed to create conversational chain. Please check your environment variables and Pinecone setup.")
            sys.exit(1)
        
        # Start interactive chat
        interactive_chat(conversational_chain)
    
    except ValueError as e:
        print(f"Error: {str(e)}")
        sys.exit(1)
    except ConnectionError as e:
        print(f"Connection error: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nSession terminated by user. Goodbye!")
        sys.exit(0)

if __name__ == "__main__":
    main()
