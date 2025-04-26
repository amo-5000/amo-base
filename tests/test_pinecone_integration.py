#!/usr/bin/env python3
"""
Test script to validate Pinecone and LangChain integration
"""

import os
import sys
from dotenv import load_dotenv
import logging

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_integration")

# Load environment variables
load_dotenv()

def test_imports():
    """Test that all imports work correctly with the installed package versions."""
    try:
        # Import Pinecone
        from pinecone import Pinecone
        logger.info("✅ Pinecone import successful")
        
        # Import LangChain components
        from langchain_pinecone import PineconeVectorStore
        from langchain_openai import OpenAIEmbeddings, ChatOpenAI
        logger.info("✅ LangChain imports successful")
        
        return True
    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        return False

def test_pinecone_connection():
    """Test connection to Pinecone."""
    try:
        from pinecone import Pinecone
        
        # Get API key
        api_key = os.getenv("PINECONE_API_KEY")
        if not api_key:
            logger.error("❌ PINECONE_API_KEY environment variable not set")
            return False
        
        # Initialize Pinecone client
        pc = Pinecone(api_key=api_key)
        
        # List indexes
        indexes = pc.list_indexes()
        logger.info(f"✅ Connected to Pinecone. Found {len(indexes)} indexes")
        
        # Log index names
        index_names = [index.name for index in indexes]
        logger.info(f"Available indexes: {', '.join(index_names)}")
        
        return True
    except Exception as e:
        logger.error(f"❌ Pinecone connection error: {e}")
        return False

def test_openai_connection():
    """Test connection to OpenAI."""
    try:
        from langchain_openai import OpenAIEmbeddings
        
        # Get API key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("❌ OPENAI_API_KEY environment variable not set")
            return False
        
        # Initialize embeddings
        embeddings = OpenAIEmbeddings(openai_api_key=api_key)
        
        # Test with a simple embedding
        result = embeddings.embed_query("Hello, world")
        
        logger.info(f"✅ Connected to OpenAI API. Generated embedding with {len(result)} dimensions")
        
        return True
    except Exception as e:
        logger.error(f"❌ OpenAI connection error: {e}")
        return False

def test_knowledge_base_initialization():
    """Test knowledge base initialization using our updated code."""
    try:
        from query_knowledge import initialize_knowledge_base
        
        # Initialize knowledge base
        success, vector_store, error = initialize_knowledge_base()
        
        if success:
            logger.info("✅ Knowledge base initialized successfully")
            return True
        else:
            logger.error(f"❌ Knowledge base initialization failed: {error}")
            return False
    except Exception as e:
        logger.error(f"❌ Knowledge base initialization error: {e}")
        return False

if __name__ == "__main__":
    logger.info("Testing Pinecone and LangChain integration...")
    
    # Test imports
    imports_ok = test_imports()
    
    # Skip remaining tests if imports failed
    if not imports_ok:
        logger.error("❌ Import tests failed. Skipping remaining tests.")
        exit(1)
    
    # Test connections
    pc_conn = test_pinecone_connection()
    openai_conn = test_openai_connection()
    
    # Test knowledge base initialization if connections are OK
    if pc_conn and openai_conn:
        kb_init = test_knowledge_base_initialization()
    else:
        logger.warning("⚠️ Skipping knowledge base initialization test due to connection failures")
    
    # Report overall status
    if imports_ok and pc_conn and openai_conn:
        if 'kb_init' in locals() and kb_init:
            logger.info("✅ All tests passed! The integration is working correctly")
        else:
            logger.warning("⚠️ Import and connection tests passed, but knowledge base initialization failed")
    else:
        logger.error("❌ Some tests failed. Please check the logs above") 