#!/usr/bin/env python3
"""
Knowledge Base Airtable Sync Tool

This script integrates the AMO Events knowledge base with Airtable to maintain
a record of important topics and their summaries. It includes bidirectional sync,
topic discovery, and document relationship management.
"""
import os
import sys
import argparse
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import logging
from dotenv import load_dotenv
import requests
from pyairtable import Api, Base, Table
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

# Add parent directory to path to import project modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.vector_store import initialize_vector_store

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("kb_airtable_sync")

# Load environment variables
load_dotenv()

# Define output models for topic analysis
class DocumentInfo(BaseModel):
    title: str = Field(description="The title of the document")
    source: str = Field(description="The source of the document")
    relevance: int = Field(description="Relevance score from 1-10, with 10 being most relevant")
    key_points: List[str] = Field(description="Key points from this document related to the topic")

class TopicSummary(BaseModel):
    topic: str = Field(description="The main topic name")
    description: str = Field(description="A concise description of the topic")
    key_attributes: List[str] = Field(description="Key attributes or features of this topic")
    related_topics: List[str] = Field(description="Related topics that are connected")
    documents: List[DocumentInfo] = Field(description="Information about relevant documents")
    best_practices: List[str] = Field(description="Best practices for this topic")
    common_challenges: List[str] = Field(description="Common challenges with this topic")

def initialize_airtable():
    """Initialize Airtable connection and return base object"""
    api_key = os.getenv("AIRTABLE_API_KEY")
    base_id = os.getenv("AIRTABLE_BASE_ID")
    
    if not api_key:
        raise ValueError("AIRTABLE_API_KEY not found in environment variables")
    if not base_id:
        raise ValueError("AIRTABLE_BASE_ID not found in environment variables")
    
    # Initialize direct API connection for testing
    try:
        # Test connection by making a simple API call
        headers = {"Authorization": f"Bearer {api_key}"}
        response = requests.get(f"https://api.airtable.com/v0/meta/bases/{base_id}", headers=headers)
        
        if response.status_code == 200:
            logger.info(f"Successfully connected to Airtable base: {base_id}")
        else:
            logger.error(f"Failed to connect to Airtable: {response.status_code} - {response.text}")
            raise ValueError(f"Could not connect to Airtable. Please check your API key and base ID.")
    except Exception as e:
        logger.error(f"Error testing Airtable connection: {str(e)}")
        raise ValueError(f"Could not connect to Airtable. Error: {str(e)}")
    
    # Initialize PyAirtable connection
    api = Api(api_key)
    base = Base(api, base_id)
    
    logger.info(f"Initialized Airtable connection to base: {base_id}")
    return base

def ensure_tables_exist(base):
    """Ensure that necessary tables exist in Airtable, create them if they don't"""
    topics_table = None
    documents_table = None
    
    # Simple function to check if a table exists
    def table_exists(base, table_name):
        try:
            # Try a simple read operation to check if the table exists
            base.table(table_name).all(maxRecords=1)
            return True
        except Exception:
            return False
    
    # Try to use MCP tools if available
    try:
        import subprocess
        
        # Check if Topics table exists
        if table_exists(base, "Topics"):
            logger.info("Topics table exists")
            topics_table = base.table("Topics")
        else:
            logger.info("Creating Topics table using MCP tool")
            try:
                # Run the MCP tool to create Topics table
                result = subprocess.run([
                    "python", "-c", 
                    f"""
import os
from dotenv import load_dotenv
load_dotenv()
import sys
sys.path.append('/home/sk/webflow/webflow')
from mcp_airtable_create_table import mcp_airtable_create_table
result = mcp_airtable_create_table(
    base_id='{base.id}',
    table_name='Topics',
    fields=[
        {{"name": "Name", "type": "singleLineText"}},
        {{"name": "Description", "type": "multilineText"}},
        {{"name": "Key Attributes", "type": "multilineText"}},
        {{"name": "Best Practices", "type": "multilineText"}},
        {{"name": "Common Challenges", "type": "multilineText"}}
    ]
)
print(result)
                    """
                ], check=True, capture_output=True, text=True)
                logger.info(f"MCP tool result: {result.stdout}")
                # Get the table now that it's created
                topics_table = base.table("Topics")
            except Exception as e:
                logger.error(f"Error creating Topics table with MCP tool: {str(e)}")
                # Fall back to direct API method
                url = f"https://api.airtable.com/v0/meta/bases/{base.id}/tables"
                headers = {
                    "Authorization": f"Bearer {base.api.api_key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "name": "Topics",
                    "fields": [
                        {"name": "Name", "type": "singleLineText"},
                        {"name": "Description", "type": "multilineText"},
                        {"name": "Key Attributes", "type": "multilineText"},
                        {"name": "Best Practices", "type": "multilineText"},
                        {"name": "Common Challenges", "type": "multilineText"}
                    ]
                }
                response = requests.post(url, headers=headers, json=payload)
                if response.status_code in [200, 201]:
                    topics_table = base.table("Topics")
                    logger.info("Created Topics table using direct API call")
                else:
                    logger.error(f"Failed to create Topics table: {response.status_code} - {response.text}")
        
        # Check if Documents table exists
        if table_exists(base, "Documents"):
            logger.info("Documents table exists")
            documents_table = base.table("Documents")
        else:
            logger.info("Creating Documents table using MCP tool")
            try:
                # Run the MCP tool to create Documents table
                result = subprocess.run([
                    "python", "-c", 
                    f"""
import os
from dotenv import load_dotenv
load_dotenv()
import sys
sys.path.append('/home/sk/webflow/webflow')
from mcp_airtable_create_table import mcp_airtable_create_table
result = mcp_airtable_create_table(
    base_id='{base.id}',
    table_name='Documents',
    fields=[
        {{"name": "Title", "type": "singleLineText"}},
        {{"name": "Source", "type": "singleLineText"}},
        {{"name": "Key Points", "type": "multilineText"}},
        {{"name": "Content Preview", "type": "multilineText"}},
        {{"name": "Namespace", "type": "singleLineText"}},
        {{"name": "Vector IDs", "type": "multilineText"}}
    ]
)
print(result)
                    """
                ], check=True, capture_output=True, text=True)
                logger.info(f"MCP tool result: {result.stdout}")
                # Get the table now that it's created
                documents_table = base.table("Documents")
            except Exception as e:
                logger.error(f"Error creating Documents table with MCP tool: {str(e)}")
                # Fall back to direct API method
                url = f"https://api.airtable.com/v0/meta/bases/{base.id}/tables"
                headers = {
                    "Authorization": f"Bearer {base.api.api_key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "name": "Documents",
                    "fields": [
                        {"name": "Title", "type": "singleLineText"},
                        {"name": "Source", "type": "singleLineText"},
                        {"name": "Key Points", "type": "multilineText"},
                        {"name": "Content Preview", "type": "multilineText"},
                        {"name": "Namespace", "type": "singleLineText"},
                        {"name": "Vector IDs", "type": "multilineText"}
                    ]
                }
                response = requests.post(url, headers=headers, json=payload)
                if response.status_code in [200, 201]:
                    documents_table = base.table("Documents")
                    logger.info("Created Documents table using direct API call")
                else:
                    logger.error(f"Failed to create Documents table: {response.status_code} - {response.text}")
        
        # Add additional fields and relationships after tables exist
        if topics_table and documents_table:
            try:
                # Try to add fields that weren't included in initial creation
                try:
                    topics_table.create_field({
                        "name": "Last Updated", 
                        "type": "dateTime"
                    })
                except:
                    logger.info("Last Updated field might already exist in Topics table")
                
                try:
                    topics_table.create_field({
                        "name": "Confidence Score", 
                        "type": "number", 
                        "options": {"precision": 1}
                    })
                except:
                    logger.info("Confidence Score field might already exist in Topics table")
                
                try:
                    documents_table.create_field({
                        "name": "Last Indexed", 
                        "type": "dateTime"
                    })
                except:
                    logger.info("Last Indexed field might already exist in Documents table")
                
                try:
                    documents_table.create_field({
                        "name": "Relevance Score", 
                        "type": "number", 
                        "options": {"precision": 1}
                    })
                except:
                    logger.info("Relevance Score field might already exist in Documents table")
                
                # Add linked fields
                try:
                    topics_table.create_field({
                        "name": "Related Topics", 
                        "type": "multipleRecordLinks",
                        "options": {"linkedTableName": "Topics"}
                    })
                except:
                    logger.info("Related Topics field might already exist in Topics table")
                
                try:
                    documents_table.create_field({
                        "name": "Topics", 
                        "type": "multipleRecordLinks",
                        "options": {"linkedTableName": "Topics"}
                    })
                except:
                    logger.info("Topics field might already exist in Documents table")
                
            except Exception as e:
                logger.warning(f"Error adding additional fields: {str(e)}")
                logger.warning("Some fields may not have been created, but tables should still be usable")
    
    except Exception as e:
        logger.error(f"Error checking or creating tables: {str(e)}")
        logger.error("Unable to create necessary tables. Please check your Airtable permissions.")
    
    # Final check
    if not topics_table or not documents_table:
        raise ValueError("Failed to create or access the required tables. Please check your Airtable permissions and API key.")
    
    return topics_table, documents_table

def get_topic_summary(topic: str, vector_store, namespace: Optional[str] = None, num_docs: int = 5) -> TopicSummary:
    """
    Generate a comprehensive topic summary by querying the vector store and analyzing the results
    """
    logger.info(f"Generating topic summary for: '{topic}'")
    
    # Search for relevant documents
    search_filter = {"namespace": namespace} if namespace else None
    results = vector_store.similarity_search_with_score(
        query=topic,
        k=num_docs,
        filter=search_filter
    )
    
    # Format documents for context
    formatted_docs = []
    for i, (doc, score) in enumerate(results):
        formatted_docs.append(
            f"DOCUMENT {i+1}:\n"
            f"Title: {doc.metadata.get('title', 'Unknown')}\n"
            f"Source: {doc.metadata.get('source', 'Unknown')}\n"
            f"Content: {doc.page_content[:1500]}...\n" # Truncate for token limit
        )
    
    context = "\n\n".join(formatted_docs)
    
    # Initialize the output parser
    parser = PydanticOutputParser(pydantic_object=TopicSummary)
    
    # Create the LLM chain
    llm = ChatOpenAI(temperature=0, model="gpt-4-turbo")
    
    prompt_template = """
    You are a knowledgeable assistant analyzing information about the AMO events platform.
    
    TOPIC TO ANALYZE: {topic}
    
    CONTEXT DOCUMENTS:
    {context}
    
    Please create a comprehensive summary of the topic based on the provided documents.
    Focus on practical implementation details, integration aspects, best practices, and common
    challenges related to the AMO events platform.
    
    {format_instructions}
    """
    
    prompt = ChatPromptTemplate.from_template(prompt_template)
    
    # Format the prompt with our query and context
    formatted_prompt = prompt.format(
        topic=topic,
        context=context,
        format_instructions=parser.get_format_instructions()
    )
    
    # Process with the LLM
    try:
        llm_output = llm.invoke(formatted_prompt)
        result = parser.parse(llm_output.content)
        logger.info(f"Successfully generated summary for topic: '{topic}'")
        return result
    except Exception as e:
        logger.error(f"Error generating topic summary: {str(e)}")
        raise

def sync_topic_to_airtable(topic_summary: TopicSummary, topics_table, documents_table):
    """
    Sync a topic summary to Airtable, creating or updating records as needed
    """
    logger.info(f"Syncing topic to Airtable: '{topic_summary.topic}'")
    
    # Check if topic already exists
    existing_topics = topics_table.all(formula=f"{{Name}}='{topic_summary.topic}'")
    
    topic_data = {
        "Name": topic_summary.topic,
        "Description": topic_summary.description,
        "Key Attributes": topic_summary.key_attributes,
        "Best Practices": "\n\n".join(topic_summary.best_practices),
        "Common Challenges": "\n\n".join(topic_summary.common_challenges),
        "Last Updated": datetime.now().isoformat()
    }
    
    if not existing_topics:
        # Create new topic
        logger.info(f"Creating new topic: '{topic_summary.topic}'")
        topic_record = topics_table.create(topic_data)
        topic_id = topic_record["id"]
    else:
        # Update existing topic
        topic_id = existing_topics[0]["id"]
        logger.info(f"Updating existing topic: '{topic_summary.topic}' (ID: {topic_id})")
        topics_table.update(topic_id, topic_data)
    
    # Process documents
    for doc_info in topic_summary.documents:
        # Check if document already exists
        existing_docs = documents_table.all(
            formula=f"{{Title}}='{doc_info.title}' AND {{Source}}='{doc_info.source}'"
        )
        
        doc_data = {
            "Title": doc_info.title,
            "Source": doc_info.source,
            "Key Points": "\n\n".join(doc_info.key_points),
            "Topics": [topic_id],  # Link to the topic
            "Relevance Score": doc_info.relevance,
            "Last Indexed": datetime.now().isoformat()
        }
        
        if not existing_docs:
            # Create new document record
            logger.info(f"Creating new document record: '{doc_info.title}'")
            documents_table.create(doc_data)
        else:
            # Update existing document record
            doc_id = existing_docs[0]["id"]
            logger.info(f"Updating existing document: '{doc_info.title}' (ID: {doc_id})")
            
            # Get current topics to avoid overwriting
            current_doc = documents_table.get(doc_id)
            current_topics = current_doc.get("fields", {}).get("Topics", [])
            
            # Only add the topic if it's not already linked
            if topic_id not in current_topics:
                current_topics.append(topic_id)
                doc_data["Topics"] = current_topics
            
            documents_table.update(doc_id, doc_data)
    
    logger.info(f"Successfully synced topic '{topic_summary.topic}' with {len(topic_summary.documents)} related documents")
    return topic_id

def discover_topics(vector_store, namespace: Optional[str] = None, limit: int = 10):
    """
    Discover important topics in the knowledge base using cluster analysis
    """
    logger.info("Discovering important topics in the knowledge base")
    
    # Use an LLM to help discover topics
    llm = ChatOpenAI(temperature=0, model="gpt-4-turbo")
    
    # Search for a broad sample of documents
    search_terms = ["event management", "airtable", "webflow", "xano", "n8n", "whatsapp"]
    all_docs = []
    
    for term in search_terms:
        search_filter = {"namespace": namespace} if namespace else None
        results = vector_store.similarity_search_with_score(
            query=term,
            k=5,  # Get 5 docs per term
            filter=search_filter
        )
        all_docs.extend([doc for doc, _ in results])
    
    # Deduplicate documents
    unique_docs = []
    seen_sources = set()
    for doc in all_docs:
        source = doc.metadata.get('source', 'unknown')
        if source not in seen_sources:
            seen_sources.add(source)
            unique_docs.append(doc)
    
    # Limit to specified number
    unique_docs = unique_docs[:limit]
    
    # Format documents for LLM
    formatted_docs = []
    for i, doc in enumerate(unique_docs):
        formatted_docs.append(
            f"DOCUMENT {i+1}:\n"
            f"Title: {doc.metadata.get('title', 'Unknown')}\n"
            f"Source: {doc.metadata.get('source', 'Unknown')}\n"
            f"Content Preview: {doc.page_content[:500]}...\n"
        )
    
    context = "\n\n".join(formatted_docs)
    
    # Create a prompt for topic discovery
    prompt = f"""
    You are analyzing a sample of documents from an AMO Events knowledge base.
    These documents relate to event management, Webflow, Airtable, Xano, n8n, and WhatsApp integration.
    
    Based on the following document samples, identify the 10 most important and distinct topics
    that should be tracked in a knowledge management system.
    
    DOCUMENT SAMPLES:
    {context}
    
    For each topic, provide:
    1. Topic name (concise, 1-4 words)
    2. Brief description (1-2 sentences)
    
    Format your response as a JSON array of objects with "topic" and "description" fields.
    """
    
    try:
        response = llm.invoke(prompt)
        # Extract JSON from response
        content = response.content
        json_start = content.find("[")
        json_end = content.rfind("]") + 1
        
        if json_start >= 0 and json_end > json_start:
            json_str = content[json_start:json_end]
            topics = json.loads(json_str)
            logger.info(f"Discovered {len(topics)} potential topics")
            return topics
        else:
            logger.error("Failed to extract JSON from LLM response")
            return []
    except Exception as e:
        logger.error(f"Error discovering topics: {str(e)}")
        return []

def sync_all_topics_to_airtable(topics, vector_store, base):
    """
    Sync all discovered topics to Airtable
    """
    topics_table, documents_table = ensure_tables_exist(base)
    
    for topic_info in topics:
        try:
            # Generate comprehensive topic summary
            topic_summary = get_topic_summary(topic_info["topic"], vector_store)
            
            # Sync to Airtable
            topic_id = sync_topic_to_airtable(topic_summary, topics_table, documents_table)
            logger.info(f"Synced topic '{topic_info['topic']}' to Airtable (ID: {topic_id})")
        except Exception as e:
            logger.error(f"Error processing topic '{topic_info['topic']}': {str(e)}")
    
    logger.info(f"Completed syncing {len(topics)} topics to Airtable")

def get_airtable_topics(topics_table):
    """Get all topics from Airtable"""
    try:
        records = topics_table.all()
        return [record["fields"]["Name"] for record in records if "Name" in record["fields"]]
    except Exception as e:
        logger.error(f"Error retrieving topics from Airtable: {str(e)}")
        # Return empty list instead of failing
        return []

def export_airtable_to_json(base, output_file):
    """Export all Airtable data to a JSON file"""
    logger.info(f"Exporting Airtable data to {output_file}")
    
    topics_table, documents_table = ensure_tables_exist(base)
    
    # Get all topics
    topics = topics_table.all()
    # Get all documents
    documents = documents_table.all()
    
    data = {
        "topics": topics,
        "documents": documents,
        "export_date": datetime.now().isoformat()
    }
    
    with open(output_file, "w") as f:
        json.dump(data, f, indent=2)
    
    logger.info(f"Successfully exported {len(topics)} topics and {len(documents)} documents to {output_file}")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Sync the AMO knowledge base with Airtable for topic tracking"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Discover topics command
    discover_parser = subparsers.add_parser("discover", help="Discover important topics in the knowledge base")
    discover_parser.add_argument("--namespace", "-n", default=None, help="Namespace to search in")
    discover_parser.add_argument("--limit", "-l", type=int, default=10, help="Maximum number of topics to discover")
    
    # Sync topic command
    sync_parser = subparsers.add_parser("sync-topic", help="Sync a specific topic to Airtable")
    sync_parser.add_argument("topic", help="Topic to sync")
    sync_parser.add_argument("--namespace", "-n", default=None, help="Namespace to search in")
    
    # Sync all topics command
    sync_all_parser = subparsers.add_parser("sync-all", help="Sync all discovered topics to Airtable")
    sync_all_parser.add_argument("--namespace", "-n", default=None, help="Namespace to search in")
    sync_all_parser.add_argument("--limit", "-l", type=int, default=10, help="Maximum number of topics to discover")
    
    # List Airtable topics command
    list_parser = subparsers.add_parser("list", help="List all topics in Airtable")
    
    # Export Airtable data command
    export_parser = subparsers.add_parser("export", help="Export Airtable data to a JSON file")
    export_parser.add_argument("--output", "-o", default="airtable_export.json", help="Output file path")
    
    args = parser.parse_args()
    
    # Initialize Airtable
    try:
        base = initialize_airtable()
    except ValueError as e:
        logger.error(f"Airtable initialization failed: {str(e)}")
        return 1
    
    # Process commands
    if args.command == "discover":
        # Initialize vector store
        vector_store = initialize_vector_store()
        
        # Discover topics
        topics = discover_topics(vector_store, args.namespace, args.limit)
        
        # Print discovered topics
        print("\nDISCOVERED TOPICS:")
        print("=" * 50)
        for i, topic in enumerate(topics):
            print(f"{i+1}. {topic['topic']}: {topic['description']}")
            print("-" * 50)
    
    elif args.command == "sync-topic":
        # Initialize vector store
        vector_store = initialize_vector_store()
        
        # Get topic tables
        topics_table, documents_table = ensure_tables_exist(base)
        
        try:
            # Generate topic summary
            topic_summary = get_topic_summary(args.topic, vector_store, args.namespace)
            
            # Sync to Airtable
            topic_id = sync_topic_to_airtable(topic_summary, topics_table, documents_table)
            
            print(f"\nSuccessfully synced topic '{args.topic}' to Airtable (ID: {topic_id})")
            print(f"Linked {len(topic_summary.documents)} related documents")
        except Exception as e:
            logger.error(f"Failed to sync topic '{args.topic}': {str(e)}")
            return 1
    
    elif args.command == "sync-all":
        # Initialize vector store
        vector_store = initialize_vector_store()
        
        # Discover topics
        topics = discover_topics(vector_store, args.namespace, args.limit)
        
        # Sync all topics
        sync_all_topics_to_airtable(topics, vector_store, base)
        
        print(f"\nSuccessfully synced {len(topics)} topics to Airtable")
    
    elif args.command == "list":
        # Get topic tables
        topics_table, documents_table = ensure_tables_exist(base)
        
        # Get topics from Airtable
        topics = get_airtable_topics(topics_table)
        
        # Print topics
        print("\nAIRTABLE TOPICS:")
        print("=" * 50)
        for i, topic in enumerate(topics):
            print(f"{i+1}. {topic}")
        print(f"\nTotal: {len(topics)} topics")
    
    elif args.command == "export":
        # Export Airtable data
        export_airtable_to_json(base, args.output)
        print(f"\nSuccessfully exported Airtable data to {args.output}")
    
    else:
        parser.print_help()
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 