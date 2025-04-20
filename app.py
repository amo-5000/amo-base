"""
AMO Events Platform Knowledge Base - Streamlit Web Interface

This web application provides a user-friendly interface to interact with the 
AMO events platform knowledge base. It allows users to:
- Ask questions about AMO events platform development
- See the sources of information used to answer questions
- Choose from common question categories
- Maintain conversation history within a session

Built with:
- Streamlit for the web interface
- LangChain for AI functionality
- Pinecone for vector database
- OpenAI for embeddings and LLM
"""

import os
import streamlit as st
from dotenv import load_dotenv
from typing import List, Dict, Any

# Import LangChain components
from langchain.chains import ConversationalRetrievalChain
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.llms import OpenAI
from langchain.memory import ConversationBufferMemory
from langchain.vectorstores import Pinecone

# Import custom components
import pinecone
from utils.prompts import AMO_SYSTEM_PROMPT

# Initialize environment variables
load_dotenv()

# Set page configuration
st.set_page_config(
    page_title="AMO Events Platform Knowledge Base",
    page_icon="🎪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Common event platform questions
COMMON_QUESTIONS = {
    "Webflow Integration": [
        "How do I connect Webflow forms to Airtable?",
        "What's the best way to create event landing pages in Webflow?",
        "How can I implement ticket purchasing in Webflow?"
    ],
    "Airtable Usage": [
        "How should I structure my event data in Airtable?",
        "How do I track attendee RSVPs in Airtable?",
        "Can Airtable handle ticket inventory management?"
    ],
    "WhatsApp Notifications": [
        "How do I send event reminders via WhatsApp?",
        "Can I automate WhatsApp messages based on Airtable changes?",
        "What's the best way to handle WhatsApp opt-ins for events?"
    ],
    "n8n Automation": [
        "How can I use n8n to connect our event platforms?",
        "What are some common n8n workflows for events?",
        "How do I trigger actions when someone registers?"
    ],
    "Xano Backend": [
        "How can Xano be used for custom event logic?",
        "Can Xano handle event check-ins and validation?",
        "How do I connect Xano to our other event tools?"
    ]
}


@st.cache_resource
def initialize_pinecone() -> None:
    """Initialize Pinecone with credentials from environment variables."""
    api_key = os.getenv("PINECONE_API_KEY")
    
    if not api_key:
        st.error("Pinecone API key not found. Please check your .env file.")
        st.stop()
    
    # As of January 2024, Pinecone no longer requires environment parameter
    pinecone.init(api_key=api_key)


@st.cache_resource
def get_conversational_chain():
    """
    Create and return a conversational retrieval chain.
    
    Returns:
        ConversationalRetrievalChain: Chain for conversational question answering
    """
    # Initialize Pinecone
    initialize_pinecone()
    
    # Get index name from environment
    index_name = os.getenv("PINECONE_INDEX")
    if not index_name:
        st.error("Pinecone index name not found. Please check your .env file.")
        st.stop()
    
    # Check if index exists
    if index_name not in pinecone.list_indexes():
        st.error(f"Pinecone index '{index_name}' not found. Please check your configuration.")
        st.stop()
    
    # Initialize OpenAI
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        st.error("OpenAI API key not found. Please check your .env file.")
        st.stop()
    
    # Create embeddings
    embeddings = OpenAIEmbeddings()
    
    # Create vector store
    vectorstore = Pinecone.from_existing_index(
        index_name=index_name,
        embedding=embeddings
    )
    
    # Create memory
    memory = ConversationBufferMemory(
        memory_key="chat_history",
        return_messages=True
    )
    
    # Create LLM
    llm = OpenAI(temperature=0, model_name="gpt-4")
    
    # Create chain
    chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 5}
        ),
        memory=memory,
        condense_question_prompt=AMO_SYSTEM_PROMPT,
        return_source_documents=True
    )
    
    return chain


def initialize_session_state():
    """Initialize session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "conversation" not in st.session_state:
        st.session_state.conversation = get_conversational_chain()


def display_chat_history():
    """Display chat history from session state."""
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


def add_message(role, content):
    """Add a message to the chat history."""
    st.session_state.messages.append({"role": role, "content": content})


def clear_chat_history():
    """Clear the chat history and reset the conversation."""
    st.session_state.messages = []
    st.session_state.conversation = get_conversational_chain()
    st.success("Conversation has been reset!")


def display_source_documents(source_docs):
    """Display source documents used to answer the question."""
    if source_docs:
        with st.expander("Sources Used", expanded=False):
            for i, doc in enumerate(source_docs):
                st.markdown(f"**Source {i+1}**")
                st.text(doc.page_content[:300] + "..." if len(doc.page_content) > 300 else doc.page_content)
                st.markdown(f"*Source: {doc.metadata.get('source', 'Unknown')}*")
                st.divider()


def handle_user_input(user_input: str):
    """Process user input and generate a response."""
    # Add user message to chat history
    add_message("user", user_input)
    
    # Display thinking indicator
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown("Thinking...")
    
    # Get response from conversation chain
    try:
        response = st.session_state.conversation({"question": user_input})
        answer = response["answer"]
        source_documents = response.get("source_documents", [])
        
        # Update assistant message in chat
        message_placeholder.markdown(answer)
        
        # Add assistant message to chat history
        add_message("assistant", answer)
        
        # Display source documents
        display_source_documents(source_documents)
    
    except Exception as e:
        error_message = f"Error: {str(e)}"
        message_placeholder.markdown(error_message)
        add_message("assistant", error_message)


def main():
    """Main function to run the Streamlit app."""
    # Set up page header
    st.title("🎪 AMO Events Platform Knowledge Base")
    st.markdown("""
    Ask questions about building event platforms with Webflow, Airtable, Xano, n8n, and WhatsApp API integration.
    """)
    
    # Initialize session state
    initialize_session_state()
    
    # Sidebar with options
    with st.sidebar:
        st.title("Options")
        
        # Clear chat button
        if st.button("Clear Conversation"):
            clear_chat_history()
        
        st.divider()
        
        # Common questions categories
        st.subheader("Common Topics")
        
        for category, questions in COMMON_QUESTIONS.items():
            with st.expander(category):
                for question in questions:
                    if st.button(question, key=f"btn_{question}"):
                        handle_user_input(question)
        
        st.divider()
        
        # About section
        st.subheader("About")
        st.markdown("""
        This knowledge base helps answer questions about AMO events platform development using:
        
        - **Webflow** for event websites
        - **Airtable** for event data
        - **Xano** for backend logic
        - **n8n** for automation
        - **WhatsApp API** for notifications
        """)
    
    # Display chat history
    display_chat_history()
    
    # Chat input
    if user_input := st.chat_input("Ask a question about AMO events platform..."):
        handle_user_input(user_input)


if __name__ == "__main__":
    main()
