# AMO Events Knowledge Base - Deployment Guide

This guide outlines the deployment options and steps for the AMO Events Knowledge Base application.

## Deployment Options

### 1. Docker and Self-Hosting

The application is containerized using Docker, making it easy to deploy on any server that supports Docker.

**Requirements:**
- Docker and Docker Compose
- 2GB+ RAM
- Valid API keys for OpenAI and Pinecone

**Advantages:**
- Complete control over the environment
- No third-party service fees (beyond API usage)
- Data privacy and security

**Disadvantages:**
- Requires server maintenance
- No built-in scaling

### 2. Streamlit Cloud

Streamlit provides a cloud hosting service specifically designed for Streamlit applications.

**Requirements:**
- GitHub repository with the application code
- Streamlit Cloud account
- Environment secrets for API keys

**Advantages:**
- Simple deployment process
- Managed service with automatic updates
- Free tier available for small applications

**Disadvantages:**
- Limited customization
- Public repositories by default on free tier
- May have bandwidth limitations

### 3. Vercel

Vercel is a cloud platform for frontend and serverless deployments.

**Requirements:**
- GitHub repository with the application code
- Vercel account
- Environment variables for API keys

**Advantages:**
- Global CDN for fast access
- Automatic deployments from Git
- Free tier available

**Disadvantages:**
- Not specifically designed for Streamlit
- May require additional configuration

## Self-Hosting Deployment Steps

### Prerequisites

1. Install Docker and Docker Compose on your server
2. Clone the repository
3. Set up the required environment variables

### Environment Setup

Create a `.env` file in the root directory with the following variables:

```
OPENAI_API_KEY=your_openai_api_key
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_INDEX_NAME=your_pinecone_index_name
```

### Deployment

1. Build and start the containers:

```bash
docker-compose up -d
```

2. Check that the application is running:

```bash
docker-compose ps
```

3. Access the application at `http://your-server-ip:8501`

### Updating

To update the application:

```bash
git pull
docker-compose down
docker-compose up -d --build
```

## Streamlit Cloud Deployment

1. Push your code to a GitHub repository
2. Sign up for [Streamlit Cloud](https://streamlit.io/cloud)
3. Click "New app" and select your repository
4. Add the required secrets in the app settings
5. Deploy the application

## CI/CD Pipeline

A GitHub Actions workflow is included in this repository to automate the deployment process:

1. When code is pushed to the main branch, tests are run
2. If tests pass, a Docker image is built and pushed to Docker Hub
3. The image is then deployed to your server via SSH

To use this pipeline, add the following secrets to your GitHub repository:

- `OPENAI_API_KEY`: Your OpenAI API key
- `PINECONE_API_KEY`: Your Pinecone API key
- `PINECONE_INDEX_NAME`: Your Pinecone index name
- `DOCKERHUB_USERNAME`: Your Docker Hub username
- `DOCKERHUB_TOKEN`: Your Docker Hub token
- `SERVER_HOST`: Your server's hostname or IP
- `SERVER_USERNAME`: SSH username for your server
- `SERVER_SSH_KEY`: SSH private key for your server
- `SERVER_PORT`: SSH port for your server (usually 22)

## Monitoring and Maintenance

### Logs

Container logs can be viewed with:

```bash
docker-compose logs -f
```

Application logs are stored in the `logs` directory and mounted to the container.

### Backups

Automated backups of the conversation logs and knowledge base should be set up:

```bash
# Example backup script for logs
tar -czf amo-kb-logs-$(date +%Y%m%d).tar.gz logs/
# Transfer to backup storage
```

### Health Checks

The application includes a healthcheck endpoint at `/_stcore/health` which can be monitored with services like Uptime Robot or Prometheus.

## Security Considerations

1. API keys should never be committed to the repository
2. Use HTTPS with a valid SSL certificate in production
3. Consider adding authentication to the application
4. Regularly update dependencies and the Docker image
5. Implement proper API key rotation

## Comparison of Hosting Options

| Feature | Self-Hosted | Streamlit Cloud | Vercel |
|---------|-------------|-----------------|--------|
| Cost | Server costs only | Free tier available | Free tier available |
| Ease of setup | Moderate | Easy | Moderate |
| Customization | High | Limited | Moderate |
| Scaling | Manual | Automatic | Automatic |
| Privacy | High | Moderate | Moderate |
| Maintenance | Required | Minimal | Minimal |

Choose the option that best fits your team's requirements and technical capabilities. 