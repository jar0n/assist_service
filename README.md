# Assist, a Government Communications initiative

Assist is a tool built by government communicators, for government communicators. Powered by generative AI, Assist is a secure and accessible bespoke conversational tool that empowers users to become even more efficient and effective in their roles through helping to brainstorm, create first drafts and review work. By using Assist, GCS members also benefit from the confidence that its outputs follow GCS policies and standards. 

In addition to being able to reference specific GCS documents, responsible use has been the guiding principle of Assist’s development, informed by the GCS Framework for Ethical Innovation and GCS Generative AI Policy. Before using the tool, all GCS members must complete a bespoke ‘AI for Communicators’ training course, designed to upskill and inform them of the safe use of Assist and AI in the workplace. Assist provides users with more than 50 communications-specific ‘pre-built prompts’, which reflect the typical tasks a government communicator might need to do on a daily basis. These prompts span across all seven GCS disciplines, ensuring the tool is tailored to every government communicator use case. 

[Read the full blog here.](https://gcs.civilservice.gov.uk/blog/introducing-assist-the-dynamic-ai-tool-rapidly-transforming-government-communications/)

![image](https://github.com/user-attachments/assets/04e93ecc-d537-47a0-975f-7c779e54b6f5)

## Assist API quickstart

### Requirements
- Install `make`
- Install `docker` and `docker-compose`
- **OpenAI API access**:
  - Create an OpenAI account at [https://platform.openai.com](https://platform.openai.com)
  - Generate an API key with access to GPT-4o models
  - Ensure you have sufficient API credits
- Procure an account for 'Insights manager' (previously bugsnag) for logging

### App startup

- Create a `.env` file from `.env.example`
  - Populate `OPENAI_API_KEY` with your OpenAI API key. This allows the application to access OpenAI's LLM services.
  - (Optional) Set `OPENAI_API_BASE` if using a custom OpenAI-compatible endpoint (default: `https://api.openai.com/v1`)
  - Set the variable `IS_DEV=True`
  - Populate `AUTH_SECRET_KEY` with a secure variable; you send this value with every request to the API for authentication
  - Populate both `OPENSEARCH_INITIAL_ADMIN_PASSWORD` and `OPENSEARCH_PASSWORD` with the same password
- Run `make start` from the root directory. This will cause the Docker images to build and launch
- Visit `localhost:5312/docs` from your browser to view the available endpoints

The API is designed to work with the Connect frontend (another service created by Government Communications) though it can be used with other clients.

### Generating a response
- Generate an `auth-session` token by sending a get request to the auth session endpoint with a UUID4 for the user in the header. You can use any valid UUID4 as the user UUID header
- Generate a new chat with a message by sending a get request to `/v1/chats/users/{user_uuid}`. The response will contain your completed message

## Deployment Options

### Local Development
Follow the quickstart instructions above to run the service locally with Docker.

### Cloudflare Container Deployment
Deploy Assist on Cloudflare's edge network for global distribution and scalability:

- **Requirements**: Cloudflare paid plan (Containers not available on free tier)
- **Setup Guide**: See [CLOUDFLARE_DEPLOYMENT.md](CLOUDFLARE_DEPLOYMENT.md) for complete instructions
- **Features**:
  - Automatic load balancing across multiple container instances
  - Global edge deployment
  - Built-in observability and monitoring
  - Configurable scaling (up to 10 concurrent instances)

Quick deployment:
```bash
cd js
npm install
npx wrangler login
npx wrangler secret put OPENAI_API_KEY
npm run deploy
```

For detailed Cloudflare deployment instructions, troubleshooting, and configuration options, refer to [CLOUDFLARE_DEPLOYMENT.md](CLOUDFLARE_DEPLOYMENT.md).

## Architecture

### LLM Integration
Assist uses **OpenAI's API** with the following models:
- **GPT-4o**: Main chat responses, query generation, and complex reasoning tasks
- **GPT-4o-mini**: Lightweight tasks like routing, relevance checks, and summaries

The service includes automatic message format conversion and tool calling support for enhanced functionality.

### Key Components
- **FastAPI**: Modern Python web framework for the REST API
- **PostgreSQL**: Primary database for user data, chats, and messages
- **OpenSearch**: Vector search for RAG (Retrieval Augmented Generation)
- **S3-compatible storage**: Document uploads and error logs
- **OpenAI API**: Large language model inference

### RAG System
The service implements a sophisticated RAG pipeline:
1. **Central Guidance**: GCS policy documents and internal knowledge base
2. **Personal Documents**: User-uploaded document processing and indexing
3. **Gov.UK Search**: Integration with UK government content
4. **Smart query routing**: Automatic selection of relevant knowledge sources
