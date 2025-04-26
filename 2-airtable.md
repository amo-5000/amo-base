# Setting Up Airtable for AMO Knowledge Management

This guide provides step-by-step instructions for setting up an Airtable base to manage knowledge topics and documents from the AMO Events Platform knowledge base.

## Prerequisites

- An Airtable account (free tier will work, but Professional plan recommended for API usage)
- API key from your Airtable account
- The AMO knowledge base must be properly set up with documents indexed in Pinecone

## Step 1: Create a New Airtable Base

1. Log in to your Airtable account at [airtable.com](https://airtable.com)
2. Click on "Add a base" button (+ icon)
3. Select "Start from scratch"
4. Name your base "AMO Knowledge Base"
5. Click "Create base"

## Step 2: Set Up Environment Variables

1. Locate your Airtable API key:
   - Go to your [Airtable account page](https://airtable.com/account)
   - Under the API section, find your API key (or generate a new one)
   - Copy this key

2. Find your base ID:
   - Open your newly created base
   - Look at the URL in your browser
   - The base ID is the part after `airtable.com/` and before any additional slashes
   - Example: If the URL is `https://airtable.com/appR8m6uNHOh1Lw6q/tblabcdef`, then `appR8m6uNHOh1Lw6q` is your base ID

3. Add these to your `.env` file:
   ```
   AIRTABLE_API_KEY=your_api_key_here
   AIRTABLE_BASE_ID=your_base_id_here
   ```

## Step 3: Create Tables Automatically

Instead of manually creating tables, you can use our script to automatically set up the required tables with proper fields and relationships:

1. Navigate to your AMO project directory
2. Run the kb_airtable_sync.py script with any command (it will create the tables on first run):
   ```bash
   cd amo-base
   python tools/kb_airtable_sync.py list
   ```

This will create two tables with the following structure:

### Topics Table
- **Name**: The topic name
- **Description**: Detailed description of the topic
- **Key Attributes**: Multi-select field with options like Webflow, Airtable, Xano, etc.
- **Related Topics**: Links to other topics in the Topics table
- **Best Practices**: Text field containing best practices for this topic
- **Common Challenges**: Text field containing common challenges with this topic
- **Last Updated**: Date and time when the topic was last updated
- **Confidence Score**: Numeric score representing confidence in the topic summary

### Documents Table
- **Title**: Document title
- **Source**: Source of the document
- **Topics**: Links to related topics in the Topics table
- **Key Points**: Text field containing key points extracted from the document
- **Content Preview**: Preview of the document content
- **Namespace**: The namespace in Pinecone where this document is stored
- **Vector IDs**: IDs of the vector chunks in Pinecone
- **Last Indexed**: Date and time when the document was last indexed
- **Relevance Score**: Numeric score representing document relevance to linked topics

## Step 4: Populate Your Airtable with Knowledge Base Topics

You have several options to populate your Airtable:

### Option 1: Discover and Sync All Topics
This will automatically discover topics in your knowledge base and sync them to Airtable:

```bash
python tools/kb_airtable_sync.py sync-all
```

### Option 2: Sync Specific Topics
Sync specific topics that you're interested in:

```bash
python tools/kb_airtable_sync.py sync-topic "Event Registration"
```

### Option 3: Discover Topics First, Then Sync
See what topics exist before syncing:

```bash
python tools/kb_airtable_sync.py discover
python tools/kb_airtable_sync.py sync-topic "Topic Name"
```

## Step 5: View Your Airtable Data

1. Go to your Airtable base
2. You should now see:
   - The Topics table populated with topic summaries
   - The Documents table with document information
   - Linked records between topics and documents

## Step 6: Customize Your Airtable Views (Optional)

Consider creating these views for better organization:

1. In the Topics table:
   - Create a view filtered by specific Key Attributes
   - Create a view sorted by Last Updated date
   - Create a Gallery view for a more visual representation

2. In the Documents table:
   - Create a view grouped by Topics
   - Create a view filtered by Relevance Score above 7

## Step 7: Regular Maintenance

To keep your knowledge base and Airtable in sync:

1. Run periodic syncs:
   ```bash
   python tools/kb_airtable_sync.py sync-all
   ```

2. Export your data for backups:
   ```bash
   python tools/kb_airtable_sync.py export --output airtable_backup.json
   ```

## Troubleshooting

If you encounter errors:

1. **API Key Invalid**: Double-check your AIRTABLE_API_KEY in the .env file
2. **Base ID Not Found**: Verify your AIRTABLE_BASE_ID in the .env file
3. **Permission Errors**: Ensure your API key has write access to the base
4. **Rate Limiting**: Airtable has rate limits; add delays if making many requests

## Next Steps

- Explore creating custom Airtable automations to notify when topics are updated
- Consider integrating Airtable with your other workflow tools using n8n
- Set up automated backups of your Airtable data
