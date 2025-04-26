#!/usr/bin/env python3
"""
Demo script showing integration between Pinecone and LangChain
for the AMO events knowledge base.
"""

import os
from dotenv import load_dotenv
from pinecone import Pinecone
from langchain_openai import OpenAIEmbeddings, OpenAI
from langchain_pinecone import PineconeVectorStore
from langchain.prompts import PromptTemplate
from langchain.chains import RetrievalQA

def main():
    """Initialize and demonstrate Pinecone with LangChain for retrieval-based QA."""
    # Load environment variables
    load_dotenv()
    
    # Get API keys
    pinecone_api_key = os.getenv("PINECONE_API_KEY")
    pinecone_index_name = os.getenv("PINECONE_INDEX")
    
    if not pinecone_api_key or not pinecone_index_name:
        print("Missing API keys in .env file")
        return
    
    # Initialize Pinecone
    pc = Pinecone(api_key=pinecone_api_key)
    index = pc.Index(pinecone_index_name)
    
    try:
        # Initialize OpenAI embeddings
        embeddings = OpenAIEmbeddings()
        
        # Create vector store
        vector_store = PineconeVectorStore(
            index=index,
            embedding=embeddings,
            text_key="text"
        )
        
        # Create retriever
        retriever = vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 3}
        )
        
        # Create LLM
        llm = OpenAI(temperature=0)
        
        # Create prompt template
        template = """
        You are an AI assistant for the AMO events platform.
        Use the following pieces of retrieved context to answer the question.
        If you don't know the answer, just say you don't know.
        
        Context: {context}
        
        Question: {question}
        
        Answer:
        """
        
        prompt = PromptTemplate(
            template=template,
            input_variables=["context", "question"]
        )
        
        # Create QA chain
        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=retriever,
            return_source_documents=True,
            chain_type_kwargs={"prompt": prompt}
        )
        
        # Example query
        example_question = "How do I set up event registration in Webflow?"
        print(f"\nQuestion: {example_question}")
        
        result = qa_chain({"query": example_question})
        print(f"\nAnswer: {result['result']}")
        
        # Show sources
        print("\nSources:")
        for doc in result["source_documents"]:
            print(f"- {doc.metadata.get('source', 'Unknown')}")
        
        return True
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

if __name__ == "__main__":
    main() 