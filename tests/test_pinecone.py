#!/usr/bin/env python3
"""
Test script for Pinecone and OpenAI integration.
"""

import os
import sys
import traceback
from dotenv import load_dotenv
from pinecone import Pinecone
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Pinecone as LangchainPinecone

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    """Test Pinecone and OpenAI integration."""
    try:
        # Load environment variables
        print("Loading environment variables...")
        load_dotenv()
        
        # Get API keys
        pinecone_api_key = os.getenv("PINECONE_API_KEY")
        pinecone_index_name = os.getenv("PINECONE_INDEX")
        
        print(f"PINECONE_API_KEY exists: {bool(pinecone_api_key)}")
        print(f"PINECONE_INDEX exists: {bool(pinecone_index_name)}")
        
        if not pinecone_api_key or not pinecone_index_name:
            print("Missing API keys in .env file")
            return
        
        print("Initializing Pinecone...")
        pc = Pinecone(api_key=pinecone_api_key)
        
        print("Getting index...")
        index = pc.Index(pinecone_index_name)
        
        print("Getting index stats...")
        stats = index.describe_index_stats()
        print(f"Index stats: {stats}")
        
        print("Initializing OpenAI embeddings...")
        embeddings = OpenAIEmbeddings()
        
        print("Pinecone and OpenAI successfully configured!")
        print("Note: Full LangChain integration requires the langchain-pinecone package.")
        print("Run: pip install langchain-pinecone")
        
        return True
    except Exception as e:
        print(f"Error: {str(e)}")
        print("Traceback:")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    main() 