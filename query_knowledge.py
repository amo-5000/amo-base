#!/usr/bin/env python3
"""
AMO Events Knowledge Base Query Module.
This module provides functions for querying the knowledge base using LangChain and Pinecone.
"""

import os
import logging
import json
from typing import List, Dict, Any, Optional, Tuple, Union
from dotenv import load_dotenv

from langchain_pinecone import PineconeVectorStore
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.schema import Document
from langchain.callbacks.manager import CallbackManagerForChainRun
from langchain.chains import LLMChain
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.chains.combine_documents import create_stuff_documents_chain

from pinecone import Pinecone as PineconeClient

from knowledge_utils import format_sources_for_display
from utils.query_reformulation import reformulate_query, get_query_keywords

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("query_knowledge")

# Set constants
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "amo-events")
DEFAULT_TOP_K = 5
DEFAULT_MODEL = "gpt-3.5-turbo"
USE_QUERY_REFORMULATION = True

# Custom document loader for Pinecone index with JSON content
class CustomPineconeLoader:
    """Custom loader for Pinecone vectors with JSON content."""
    
    def __init__(self, index, embedding, namespace=""):
        """Initialize the loader."""
        self.index = index
        self.embedding = embedding
        self.namespace = namespace
    
    def similarity_search(self, query, k=5, filter=None):
        """Run similarity search and parse JSON node content."""
        # Generate the query embedding
        query_embedding = self.embedding.embed_query(query)
        
        # Try with default namespace first
        documents = self._query_namespace(query_embedding, self.namespace, k, filter)
        
        # If no results found and default namespace is empty, try other namespaces
        if not documents and not self.namespace:
            # Get index stats to find all namespaces
            try:
                stats = self.index.describe_index_stats()
                if hasattr(stats, 'namespaces'):
                    # Try each namespace
                    for namespace in stats.namespaces:
                        logger.info(f"Trying namespace: {namespace}")
                        docs = self._query_namespace(query_embedding, namespace, k, filter)
                        documents.extend(docs)
                        if documents:
                            break
            except Exception as e:
                logger.error(f"Error searching across namespaces: {e}")
        
        return documents
    
    def _query_namespace(self, query_embedding, namespace, k=5, filter=None):
        """Query a specific namespace and process results."""
        documents = []
        
        try:
            # Run the query
            results = self.index.query(
                vector=query_embedding,
                top_k=k,
                include_metadata=True,
                namespace=namespace,
                filter=filter
            )
            
            # Process the results
            for match in results.matches:
                try:
                    if hasattr(match, 'metadata') and '_node_content' in match.metadata:
                        # Parse the JSON string in _node_content
                        node_content = json.loads(match.metadata['_node_content'])
                        
                        # Extract the text content
                        if 'text' in node_content:
                            text = node_content['text']
                            
                            # Create a Document object
                            doc = Document(
                                page_content=text,
                                metadata={
                                    "score": match.score,
                                    "id": match.id,
                                    "source": match.metadata.get('file_path', 'Unknown'),
                                    "title": match.metadata.get('file_name', 'Untitled Document'),
                                    "topics": node_content.get('metadata', {}).get('topics', []),
                                    "namespace": namespace
                                }
                            )
                            documents.append(doc)
                        else:
                            logger.warning(f"No text field found in node_content for match {match.id}")
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse _node_content as JSON for match {match.id}")
                except Exception as e:
                    logger.error(f"Error processing match {match.id}: {e}")
        
        except Exception as e:
            logger.error(f"Error querying namespace '{namespace}': {e}")
        
        return documents

def initialize_knowledge_base(
    openai_api_key: Optional[str] = None,
    pinecone_api_key: Optional[str] = None,
    index_name: Optional[str] = None
) -> Tuple[bool, Union[CustomPineconeLoader, None], str]:
    """
    Initialize the knowledge base with Pinecone and OpenAI.
    
    Args:
        openai_api_key: OpenAI API key. If None, uses environment variable.
        pinecone_api_key: Pinecone API key. If None, uses environment variable.
        index_name: Name of the Pinecone index. If None, uses default.
        
    Returns:
        Tuple of (success_bool, vectorstore_instance, error_message)
    """
    try:
        # Use provided keys or get from environment
        openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        pinecone_api_key = pinecone_api_key or os.getenv("PINECONE_API_KEY")
        index_name = index_name or PINECONE_INDEX_NAME
        
        if not openai_api_key:
            return False, None, "OpenAI API key not found"
        
        if not pinecone_api_key:
            return False, None, "Pinecone API key not found"
        
        # Initialize Pinecone with new class-based approach
        pc = PineconeClient(api_key=pinecone_api_key)
        
        # Check if index exists
        indexes = [index.name for index in pc.list_indexes()]
        if index_name not in indexes:
            return False, None, f"Pinecone index '{index_name}' not found"
        
        # Get the index
        index = pc.Index(index_name)
        
        # Initialize embeddings
        embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)
        
        # Use custom loader instead of PineconeVectorStore
        loader = CustomPineconeLoader(
            index=index,
            embedding=embeddings,
            namespace=""  # Default namespace
        )
        
        logger.info(f"Successfully initialized knowledge base with index '{index_name}'")
        return True, loader, ""
        
    except Exception as e:
        error_msg = f"Error initializing knowledge base: {str(e)}"
        logger.error(error_msg)
        return False, None, error_msg

def get_relevant_documents(
    query: str,
    vector_store: CustomPineconeLoader,
    top_k: int = DEFAULT_TOP_K,
    filter_criteria: Optional[Dict[str, Any]] = None,
    use_reformulation: bool = USE_QUERY_REFORMULATION, 
    conversation_history: Optional[List[Dict[str, str]]] = None
) -> Tuple[bool, List[Document], str, str]:
    """
    Retrieve relevant documents from the knowledge base.
    
    Args:
        query: The user's query.
        vector_store: The custom Pinecone loader instance.
        top_k: Number of documents to retrieve.
        filter_criteria: Optional filter criteria for the query.
        use_reformulation: Whether to use query reformulation techniques.
        conversation_history: Optional list of previous messages for context.
        
    Returns:
        Tuple of (success_bool, document_list, used_query, error_message)
    """
    try:
        original_query = query
        used_query = query
        all_docs = []
        
        if use_reformulation:
            logger.info(f"Original query: '{query}'")
            
            # Extract just the text content from conversation history
            conversation_text = []
            if conversation_history:
                for msg in conversation_history:
                    if "human" in msg:
                        conversation_text.append(msg["human"])
            
            # Apply query reformulation using the utility function
            reformulated = reformulate_query(
                query=query,
                conversation_history=conversation_text
            )
            
            # Handle both single query and list of queries returned from reformulation
            if isinstance(reformulated, list):
                primary_query = reformulated[0]  # First query is primary
                alternative_queries = reformulated[1:] if len(reformulated) > 1 else []
            else:
                primary_query = reformulated
                alternative_queries = []
            
            # Start with the primary reformulated query
            logger.info(f"Using primary reformulated query: '{primary_query}'")
            used_query = primary_query
            
            all_docs = vector_store.similarity_search(
                query=primary_query,
                k=top_k,
                filter=filter_criteria
            )
            
            # If we have alternative queries from decomposition and need more results
            if alternative_queries and len(all_docs) < top_k:
                remaining_k = top_k - len(all_docs)
                docs_per_query = max(2, remaining_k // len(alternative_queries))
                
                logger.info(f"Adding results from {len(alternative_queries)} alternative queries")
                
                # Search with each alternative query and combine results
                for i, alt_query in enumerate(alternative_queries):
                    logger.info(f"Searching with alternative query {i+1}: '{alt_query}'")
                    alt_docs = vector_store.similarity_search(
                        query=alt_query,
                        k=docs_per_query,
                        filter=filter_criteria
                    )
                    all_docs.extend(alt_docs)
                
                # Deduplicate documents by ID
                seen_ids = set()
                unique_docs = []
                for doc in all_docs:
                    doc_id = doc.metadata.get("id", "")
                    if doc_id not in seen_ids:
                        seen_ids.add(doc_id)
                        unique_docs.append(doc)
                
                all_docs = unique_docs[:top_k]  # Limit to top_k
                used_query = f"{primary_query} + alternatives"
        else:
            # Use original query without reformulation
            all_docs = vector_store.similarity_search(
                query=query,
                k=top_k,
                filter=filter_criteria
            )
        
        # If no docs found with reformulation, try original query as fallback
        if use_reformulation and not all_docs:
            logger.info(f"No results with reformulated query. Trying original query: '{original_query}'")
            all_docs = vector_store.similarity_search(
                query=original_query,
                k=top_k,
                filter=filter_criteria
            )
            used_query = original_query
        
        logger.info(f"Retrieved {len(all_docs)} documents for query: '{used_query}'")
        return True, all_docs, used_query, ""
        
    except Exception as e:
        error_msg = f"Error retrieving documents: {str(e)}"
        logger.error(error_msg)
        return False, [], query, error_msg

def create_qa_chain(
    model_name: str = DEFAULT_MODEL,
    openai_api_key: Optional[str] = None,
    temperature: float = 0.7
) -> LLMChain:
    """
    Create a QA chain with the specified LLM.
    
    Args:
        model_name: Name of the OpenAI model to use.
        openai_api_key: OpenAI API key. If None, uses environment variable.
        temperature: Temperature parameter for the LLM.
        
    Returns:
        A LangChain QA chain.
    """
    openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
    
    # Initialize the LLM
    llm = ChatOpenAI(
        model_name=model_name,
        openai_api_key=openai_api_key,
        temperature=temperature
    )
    
    # Create a system message to help steer the model
    system_message = """You are an AI assistant for AMO Events, an events management platform that uses Webflow, Airtable, Xano, n8n, and WhatsApp API.
Answer the user's question based on the provided context. Be concise and clear.
If the context doesn't contain the answer, say "I don't have enough information about that."
Do not make up information. Always reference the source of information if available.
Focus on providing step-by-step instructions for implementation questions."""
    
    # Create a prompt template
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_message),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{question}"),
        ("human", "Context: {context}")
    ])
    
    # Create a simple chain that doesn't require document objects
    chain = LLMChain(llm=llm, prompt=prompt)
    
    return chain

def answer_question(
    query: str,
    docs: List[Document],
    chain: LLMChain,
    chat_history: Optional[List[Dict[str, str]]] = None
) -> Tuple[bool, str, List[Dict[str, Any]], str]:
    """
    Answer a question using the provided documents and LLM chain.
    
    Args:
        query: The user's question.
        docs: List of relevant documents.
        chain: The LLM chain to use.
        chat_history: Optional chat history for context.
        
    Returns:
        Tuple of (success_bool, answer_text, sources_list, error_message)
    """
    try:
        # If no documents were found
        if not docs:
            return True, "I don't have information about that topic in my knowledge base.", [], ""
        
        # Extract sources for attribution
        sources = format_sources_for_display(docs)
        
        # Format chat history if provided
        formatted_history = []
        if chat_history:
            for exchange in chat_history:
                if "human" in exchange:
                    formatted_history.append(("human", exchange["human"]))
                if "ai" in exchange:
                    formatted_history.append(("ai", exchange["ai"]))
        
        # Prepare document content for the chain
        context_parts = []
        for doc in docs:
            if hasattr(doc, 'page_content'):
                context_parts.append(doc.page_content)
            elif isinstance(doc, str):
                context_parts.append(doc)
            elif isinstance(doc, dict) and 'page_content' in doc:
                context_parts.append(doc['page_content'])
        
        context = "\n\n".join(context_parts)
        
        # Get answer from chain
        result = chain.invoke({
            "question": query,
            "context": context,
            "chat_history": formatted_history
        })
        
        # Extract answer text from result
        if isinstance(result, dict) and 'text' in result:
            answer = result['text']
        elif isinstance(result, str):
            answer = result
        else:
            # If we can't find a clear answer, use the whole result
            answer = str(result)
        
        logger.info(f"Generated answer for query: '{query}'")
        return True, answer, sources, ""
        
    except Exception as e:
        error_msg = f"Error generating answer: {str(e)}"
        logger.error(error_msg)
        return False, "", [], error_msg

def process_query(
    query: str,
    vector_store: CustomPineconeLoader,
    model_name: str = DEFAULT_MODEL,
    top_k: int = DEFAULT_TOP_K,
    filter_criteria: Optional[Dict[str, Any]] = None,
    chat_history: Optional[List[Dict[str, str]]] = None,
    temperature: float = 0.7,
    use_reformulation: bool = USE_QUERY_REFORMULATION
) -> Dict[str, Any]:
    """
    Process a user query from start to finish.
    
    Args:
        query: The user's question.
        vector_store: The custom Pinecone loader instance.
        model_name: Name of the OpenAI model to use.
        top_k: Number of documents to retrieve.
        filter_criteria: Optional filter criteria for the query.
        chat_history: Optional chat history for context.
        temperature: Temperature parameter for the LLM.
        use_reformulation: Whether to use query reformulation techniques.
        
    Returns:
        Dictionary with results including answer, sources, and status.
    """
    result = {
        "success": False,
        "answer": "",
        "sources": [],
        "used_query": query,
        "error": ""
    }
    
    # Extract query keywords for debugging
    keywords = get_query_keywords(query)
    logger.info(f"Query keywords: {keywords}")
    
    # Get relevant documents
    success, docs, used_query, error = get_relevant_documents(
        query=query,
        vector_store=vector_store,
        top_k=top_k,
        filter_criteria=filter_criteria,
        use_reformulation=use_reformulation,
        conversation_history=chat_history
    )
    
    result["used_query"] = used_query
    
    if not success:
        result["error"] = error
        return result
    
    # Create QA chain
    chain = create_qa_chain(
        model_name=model_name,
        temperature=temperature
    )
    
    # Get answer
    success, answer, sources, error = answer_question(
        query=query,
        docs=docs,
        chain=chain,
        chat_history=chat_history
    )
    
    result["success"] = success
    result["answer"] = answer
    result["sources"] = sources
    result["error"] = error
    
    return result

if __name__ == "__main__":
    # Example usage for testing
    load_dotenv()
    
    success, vector_store, error = initialize_knowledge_base()
    
    if success:
        test_queries = [
            "How do I set up event registration in Webflow?",
            "How do I create a form for guests to RSVP?",
            "How do I set up check-in and track attendance?",
            "What's the process for setting up Webflow and connecting it to Airtable?"
        ]
        
        for query in test_queries:
            print(f"\nQuestion: {query}")
            result = process_query(query, vector_store)
            
            print(f"Used query: {result['used_query']}")
            print(f"Answer: {result['answer']}")
            print("Sources:")
            for source in result["sources"]:
                print(f"- {source['title']} ({source['source']})")
    else:
        print(f"Error: {error}") 