#!/usr/bin/env python3
"""
Topic Explorer - A tool to explore related topics in the AMO knowledge base
"""
import os
import sys
import argparse
from dotenv import load_dotenv
import logging
from langchain.output_parsers import PydanticOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field, validator
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from typing import List, Dict, Optional
import textwrap

# Add parent directory to path to import project modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.vector_store import initialize_vector_store

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("topic_explorer")

# Load environment variables
load_dotenv()

# Define output models
class DocumentSummary(BaseModel):
    title: str = Field(description="The title of the document")
    summary: str = Field(description="A brief summary of the document content")
    key_points: List[str] = Field(description="Key points extracted from the document")
    relevance: int = Field(description="Relevance score from 1-10, with 10 being most relevant")

class TopicAnalysis(BaseModel):
    topic: str = Field(description="The main topic being analyzed")
    description: str = Field(description="A comprehensive description of the topic")
    subtopics: List[str] = Field(description="Related subtopics identified")
    document_summaries: List[DocumentSummary] = Field(description="Summaries of relevant documents")
    next_questions: List[str] = Field(description="Suggested follow-up questions about this topic")

def process_topic(query: str, vector_store, namespace: Optional[str] = None, num_docs: int = 8):
    """
    Process a topic query using LangChain and the vector store
    """
    # Search for relevant documents
    search_filter = {"namespace": namespace} if namespace else None
    results = vector_store.similarity_search_with_score(
        query=query,
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
            f"Content: {doc.page_content[:2000]}...\n" # Truncate for token limit
        )
    
    context = "\n\n".join(formatted_docs)
    
    # Initialize the output parser
    parser = PydanticOutputParser(pydantic_object=TopicAnalysis)
    
    # Create the LLM chain
    llm = ChatOpenAI(temperature=0, model="gpt-4-turbo")
    
    prompt_template = """
    You are a knowledgeable assistant analyzing information about the AMO events platform.
    
    TOPIC TO ANALYZE: {query}
    
    CONTEXT DOCUMENTS:
    {context}
    
    Please analyze the provided documents and create a comprehensive profile of the topic.
    Extract key information, identify patterns and relationships between concepts,
    and synthesize the information into a useful overview.
    
    {format_instructions}
    """
    
    prompt = ChatPromptTemplate.from_template(prompt_template)
    
    # Format the prompt with our query and context
    formatted_prompt = prompt.format(
        query=query,
        context=context,
        format_instructions=parser.get_format_instructions()
    )
    
    # Process with the LLM
    llm_output = llm.invoke(formatted_prompt)
    
    # Parse the output
    try:
        result = parser.parse(llm_output.content)
        return result
    except Exception as e:
        logger.error(f"Failed to parse LLM output: {str(e)}")
        # Return raw output if parsing fails
        return llm_output.content

def display_topic_analysis(analysis):
    """Format and display the topic analysis in a readable way"""
    if isinstance(analysis, str):
        # Handle case where parsing failed
        print("\n=== TOPIC ANALYSIS (RAW OUTPUT) ===")
        print(analysis)
        return
    
    # Print the main topic information
    print("\n" + "=" * 80)
    print(f"TOPIC ANALYSIS: {analysis.topic}")
    print("=" * 80)
    
    # Description
    print("\nDESCRIPTION:")
    print(textwrap.fill(analysis.description, width=80))
    
    # Subtopics
    print("\nRELATED SUBTOPICS:")
    for i, subtopic in enumerate(analysis.subtopics):
        print(f"  {i+1}. {subtopic}")
    
    # Document summaries
    print("\nKEY DOCUMENTS:")
    for i, doc in enumerate(analysis.document_summaries):
        print(f"\n{i+1}. {doc.title} (Relevance: {doc.relevance}/10)")
        print("   " + textwrap.fill(doc.summary, width=75, initial_indent="   ", subsequent_indent="   "))
        print("\n   Key points:")
        for point in doc.key_points:
            print(f"   • {point}")
    
    # Next questions
    print("\nSUGGESTED FOLLOW-UP QUESTIONS:")
    for i, question in enumerate(analysis.next_questions):
        print(f"  {i+1}. {question}")
    
    print("\n" + "=" * 80)

def main():
    """Main function to explore a topic in the knowledge base"""
    parser = argparse.ArgumentParser(description="Explore topics in the AMO knowledge base")
    parser.add_argument("topic", help="The topic to explore")
    parser.add_argument("--namespace", "-n", default=None, help="Namespace to search in (leave empty for all)")
    parser.add_argument("--num-docs", "-d", type=int, default=8, help="Number of documents to analyze")
    args = parser.parse_args()
    
    # Initialize vector store
    logger.info("Initializing vector store...")
    try:
        vector_store = initialize_vector_store()
        logger.info("Vector store initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize vector store: {str(e)}")
        return
    
    # Process the topic
    logger.info(f"Analyzing topic: '{args.topic}'")
    try:
        analysis = process_topic(
            query=args.topic,
            vector_store=vector_store,
            namespace=args.namespace,
            num_docs=args.num_docs
        )
        
        # Display the analysis
        display_topic_analysis(analysis)
        
    except Exception as e:
        logger.error(f"Topic analysis failed: {str(e)}")
        return
    
    print("\nTopic exploration complete!")

if __name__ == "__main__":
    main() 