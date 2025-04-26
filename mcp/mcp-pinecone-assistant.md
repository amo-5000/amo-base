# Pinecone Assistant MCP Server Setup Guide

## Overview

The Pinecone Assistant Model Context Protocol (MCP) server enables AI agents like Claude to directly access knowledge stored in your Pinecone Assistants. This integration allows your agents to retrieve contextually relevant information from your knowledge base while maintaining conversation flow.

This guide covers both remote and local MCP server setup options, along with integration examples for different AI platforms.

## Remote MCP Server

Every Pinecone Assistant has a dedicated MCP endpoint that you can connect directly to your AI applications without running any infrastructure.

### Endpoint Format

```
https://<YOUR_PINECONE_ASSISTANT_HOST>/mcp/assistants/<YOUR_ASSISTANT_NAME>/sse
```

### Prerequisites

- A Pinecone API key from the Pinecone console
- Your assistant's MCP endpoint (found in your assistant's sidebar in the Pinecone console)

### Integration with LangChain

```python
# Example code for integrating with LangChain
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langchain_anthropic import ChatAnthropic

model = ChatAnthropic(model_name="claude-3-7-sonnet-latest", api_key="<YOUR_ANTHROPIC_API_KEY>")
pinecone_api_key = "<YOUR_PINECONE_API_KEY>"

async with MultiServerMCPClient(
    {
        "assistant_amo_events": {
            "url": "https://<YOUR_PINECONE_ASSISTANT_HOST>/mcp/assistants/amo-events/sse",
            "transport": "sse",
            "headers": {
                "Authorization": f"Bearer {pinecone_api_key}"
            }
        }
    }
) as client:
    agent = create_react_agent(model, client.get_tools())

    response = await agent.ainvoke({
        "messages": "What are the best practices for integrating Webflow forms with Airtable for event registration?"
    })
    print(response["messages"][-1].content)
```

### Integration with Claude Desktop

Claude Desktop doesn't directly support remote MCP server URLs yet. A workaround is to use the `supergateway` proxy:

1. Open Claude Desktop and go to **Settings**
2. On the **Developer** tab, click **Edit Config**
3. Add the following configuration:

```json
{
  "mcpServers": {
    "AMO Events Assistant": {
      "command": "npx",
      "args": [
        "-y",
        "supergateway",
        "--sse",
        "https://<YOUR_PINECONE_ASSISTANT_HOST>/mcp/assistants/<YOUR_ASSISTANT_ID>/sse",
        "--header",
        "Authorization: Bearer <YOUR_PINECONE_API_KEY>"
      ]
    }
  }
}
```

4. Save the configuration file and restart Claude Desktop
5. The AMO Events Assistant should appear as an available MCP server (hammer icon)

## Local MCP Server

The local server option runs a Docker container that connects to your Pinecone Assistant. This is useful for development, testing, or when you want to run the MCP server within your own infrastructure.

### Prerequisites

- Docker installed and running
- Pinecone API key
- Your Pinecone Assistant host

### Setup Steps

1. Pull the Docker image:

```bash
docker pull ghcr.io/pinecone-io/assistant-mcp
```

2. Start the MCP server:

```bash
docker run -i --rm \
  -e PINECONE_API_KEY=<PINECONE_API_KEY> \
  -e PINECONE_ASSISTANT_HOST=<PINECONE_ASSISTANT_HOST> \
  pinecone/assistant-mcp
```

### Integration with Claude Desktop

1. Open Claude Desktop and go to **Settings**
2. On the **Developer** tab, click **Edit Config**
3. Add the following configuration:

```json
{
  "mcpServers": {
    "amo-events-assistant": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-e",
        "PINECONE_API_KEY",
        "-e",
        "PINECONE_ASSISTANT_HOST",
        "pinecone/assistant-mcp"
      ],
      "env": {
        "PINECONE_API_KEY": "<YOUR_PINECONE_API_KEY>",
        "PINECONE_ASSISTANT_HOST": "<YOUR_PINECONE_ASSISTANT_HOST>"
      }
    }
  }
}
```

4. Save and restart Claude Desktop
5. The AMO Events Assistant should appear as an available MCP server

### Integration with Cursor

1. Create a `.cursor` directory in your project root if it doesn't exist
2. Create a `.cursor/mcp.json` file with the following configuration:

```json
{
  "mcpServers": {
    "amo-events-assistant": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-e",
        "PINECONE_API_KEY",
        "-e",
        "PINECONE_ASSISTANT_HOST",
        "pinecone/assistant-mcp"
      ],
      "env": {
        "PINECONE_API_KEY": "<YOUR_PINECONE_API_KEY>",
        "PINECONE_ASSISTANT_HOST": "<YOUR_PINECONE_ASSISTANT_HOST>"
      }
    }
  }
}
```

3. Save the configuration file

## Features and Capabilities

The Pinecone Assistant MCP server currently supports:

- **Context Retrieval**: AI agents can retrieve relevant context snippets from your assistant's knowledge base
- **Seamless Integration**: Works within the conversation flow without requiring separate API calls
- **Multiple Assistant Support**: Connect to multiple specialized assistants in the same agent workflow
- **Cross-Platform**: Works with Claude Desktop, Cursor, LangChain, and other MCP-compatible platforms

## Upcoming Features

Future releases will include:
- File access capabilities
- Enhanced query capabilities
- Multi-modal support
- User permission management

## Troubleshooting

- **Connection Issues**: Verify your API key and Assistant host are correct
- **Docker Problems**: Ensure Docker is running and you have pulled the latest image
- **Claude Desktop**: Make sure to restart after config changes
- **Authentication Errors**: Check that your API key has the necessary permissions

## Resources

- [Pinecone Assistant MCP Server Repository](https://github.com/pinecone-io/assistant-mcp)
- [Model Context Protocol Documentation](https://docs.anthropic.com/claude/docs/model-context-protocol-mcp)
- [Pinecone Context Snippets API](https://docs.pinecone.io/guides/assistant/retrieve-context) 