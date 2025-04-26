#!/usr/bin/env python3
"""
Test script for multi-turn conversations with the AMO Events knowledge base.
This script simulates a user having a conversation with follow-up questions
to verify that context is maintained properly.
"""

import os
import sys
import time
import logging
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

# Add the parent directory to the path to import from scripts/
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from scripts.chat import (
    load_environment_variables,
    initialize_pinecone,
    create_conversational_chain
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/multi_turn_test.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("multi_turn_test")

# Create logs directory if it doesn't exist
os.makedirs("logs", exist_ok=True)

def run_chat_simulation(
    conversational_chain: Any,
    conversation: List[str],
    delay: int = 1
) -> List[Dict[str, str]]:
    """
    Run a simulated chat conversation and record the results.
    
    Args:
        conversational_chain: The initialized conversational chain
        conversation: List of user queries in sequence
        delay: Time in seconds to wait between queries (to simulate real conversation)
        
    Returns:
        List of conversation exchanges with user queries and AI responses
    """
    results = []
    
    for i, query in enumerate(conversation):
        logger.info(f"Query {i+1}: {query}")
        
        try:
            # Process the query through the chain
            response = conversational_chain({"question": query})
            answer = response.get('answer', 'No answer received')
            
            # Log and store the result
            logger.info(f"Response {i+1}: {answer[:100]}...")
            
            # Store the exchange
            results.append({
                "query": query,
                "response": answer,
                "has_context": i > 0  # First question has no context
            })
            
            # Delay between queries to simulate real conversation
            time.sleep(delay)
            
        except Exception as e:
            error_msg = f"Error processing query {i+1}: {str(e)}"
            logger.error(error_msg)
            results.append({
                "query": query,
                "response": f"ERROR: {str(e)}",
                "has_context": i > 0,
                "error": True
            })
    
    return results

def evaluate_conversation(results: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Evaluate the conversation results for context maintenance.
    
    Args:
        results: List of conversation exchanges
        
    Returns:
        Evaluation metrics
    """
    # Initialize metrics
    metrics = {
        "total_exchanges": len(results),
        "successful_exchanges": 0,
        "errors": 0,
        "context_maintenance": 0,
        "pronoun_references": 0
    }
    
    # Count successful exchanges and errors
    for result in results:
        if result.get("error", False):
            metrics["errors"] += 1
        else:
            metrics["successful_exchanges"] += 1
    
    # Look for signs of context maintenance in follow-up questions (excluding first question)
    for i, result in enumerate(results):
        if i == 0 or result.get("error", False):
            continue
            
        response = result["response"].lower()
        query = result["query"].lower()
        
        # Check for pronouns that might indicate context maintenance
        pronoun_list = ["it", "this", "that", "these", "those", "they", "them"]
        if any(pronoun in query for pronoun in pronoun_list):
            metrics["pronoun_references"] += 1
            
        # Look for references to previous exchanges
        if "previous" in response or "earlier" in response or "mentioned" in response:
            metrics["context_maintenance"] += 1
            
    return metrics

def display_results(results: List[Dict[str, str]], metrics: Dict[str, Any]) -> None:
    """
    Display the conversation results and evaluation metrics.
    
    Args:
        results: List of conversation exchanges
        metrics: Evaluation metrics
    """
    print("\n" + "=" * 80)
    print("MULTI-TURN CONVERSATION TEST RESULTS")
    print("=" * 80)
    
    # Display the conversation
    print("\n--- CONVERSATION ---\n")
    for i, result in enumerate(results):
        print(f"User ({i+1}): {result['query']}")
        print(f"AI   ({i+1}): {result['response'][:200]}...")
        print()
    
    # Display metrics
    print("\n--- METRICS ---\n")
    print(f"Total exchanges: {metrics['total_exchanges']}")
    print(f"Successful exchanges: {metrics['successful_exchanges']}")
    print(f"Errors: {metrics['errors']}")
    print(f"Pronoun references in queries: {metrics['pronoun_references']}")
    print(f"Detected context maintenance: {metrics['context_maintenance']}")
    
    # Overall assessment
    success_rate = metrics['successful_exchanges'] / metrics['total_exchanges'] * 100
    print(f"\nSuccess rate: {success_rate:.1f}%")
    
    if metrics['context_maintenance'] > 0:
        print("✅ Context maintenance detected in responses")
    else:
        print("❌ No context maintenance detected in responses")
        
    print("=" * 80 + "\n")

def main():
    """Run the multi-turn conversation test."""
    try:
        # Load environment variables
        env_vars = load_environment_variables()
        
        # Initialize Pinecone
        pc_client = initialize_pinecone(env_vars['PINECONE_API_KEY'])
        logger.info(f"Connecting to Pinecone index '{env_vars['PINECONE_INDEX']}'...")
        
        # Create conversational chain
        conversational_chain = create_conversational_chain(pc_client, env_vars['PINECONE_INDEX'])
        if not conversational_chain:
            logger.error("Failed to create conversational chain")
            return 1
        
        # Define a test conversation with follow-up questions
        test_conversation = [
            "What are the key features of Airtable?",
            "How can I integrate it with Webflow?",
            "What are the limitations of this integration?",
            "Can you explain how to overcome those limitations?",
            "Are there any security considerations I should be aware of?"
        ]
        
        # Run the simulation
        logger.info("Starting multi-turn conversation test...")
        results = run_chat_simulation(conversational_chain, test_conversation)
        
        # Evaluate the results
        metrics = evaluate_conversation(results)
        
        # Display the results
        display_results(results, metrics)
        
        # Log completion
        logger.info("Multi-turn conversation test completed")
        return 0
        
    except Exception as e:
        logger.error(f"Error during multi-turn conversation test: {str(e)}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 