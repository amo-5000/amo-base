# AMO-Base: Events Platform Knowledge Assistant

> AI assistant that answers questions about AMO events platform development using Webflow, Airtable, Xano, n8n and WhatsApp API.

## 📚 Overview

This project creates an AI-powered knowledge base that answers questions about AMO events platform development best practices using:

- **LangChain** for AI logic and retrieval
- **Pinecone** for document storage (pre-populated with your docs)
- **OpenAI** for natural language processing
- **Streamlit** for the user interface

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- API keys for OpenAI and Pinecone
- Existing Pinecone index with your documentation

### Setup

1. **Clone and navigate to the project**

```bash
git clone https://github.com/your-org/amo-base.git
cd amo-base
```

2. **Create virtual environment**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**

```bash
pip install langchain openai pinecone-client python-dotenv streamlit
pip freeze > requirements.txt
```

4. **Set up environment variables**

Create a `.env` file:

```
OPENAI_API_KEY=your-openai-key
PINECONE_API_KEY=your-pinecone-key
PINECONE_ENV=your-environment
PINECONE_INDEX=your-index-name
```

## 🧠 Usage

**Simple query:**
```bash
python scripts/query.py "How do I connect Webflow forms to Airtable?"
```

**Interactive chat:**
```bash
python scripts/chat.py
```

**Web interface:**
```bash
streamlit run app.py
```

## 📂 Project Structure

```
amo-base/
├── README.md        # This file
├── .env             # Environment variables (not in git)
├── requirements.txt # Dependencies
├── app.py           # Streamlit web interface
├── scripts/
│   ├── query.py     # Basic query functionality
│   └── chat.py      # Interactive chat interface
└── utils/
    └── prompts.py   # Custom prompt templates
```

## 🎯 Example Queries

- "What's the best way to integrate Webflow forms with Airtable?"
- "How can I use n8n to send WhatsApp notifications for event reminders?"
- "What's the recommended workflow for event check-ins using Xano?"
- "How do I implement dynamic ticket availability based on Airtable inventory?"
- "What's the process for setting up event registration with payment processing?"

## 📚 Resources

- [LangChain Documentation](https://python.langchain.com/docs/get_started)
- [Webflow Documentation](https://developers.webflow.com/)
- [Airtable API Documentation](https://airtable.com/developers/web/api)
- [n8n Documentation](https://docs.n8n.io/)
- [WhatsApp API Documentation](https://developers.facebook.com/docs/whatsapp)
- [Xano Documentation](https://docs.xano.com/)

