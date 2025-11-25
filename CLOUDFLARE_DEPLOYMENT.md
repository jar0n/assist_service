# Cloudflare Container Deployment Guide

This guide explains how to deploy the Assist Service to Cloudflare using Cloudflare Containers and Workers.

## Overview

The Assist Service can be deployed on Cloudflare's edge network using:
- **Cloudflare Containers**: Run the FastAPI application in Docker containers
- **Cloudflare Workers**: Handle routing and load balancing across container instances
- **Durable Objects**: Manage container lifecycle and state

## Prerequisites

### Required

1. **Cloudflare Account**
   - ⚠️ **IMPORTANT**: Cloudflare Containers requires a **paid plan**
   - Free tier accounts cannot deploy containers
   - Sign up at [https://cloudflare.com](https://cloudflare.com)

2. **Node.js and npm**
   - Node.js 18+ required
   - Install from [https://nodejs.org](https://nodejs.org)

3. **Wrangler CLI**
   ```bash
   npm install -g wrangler
   ```

4. **Environment Variables**
   - `OPENAI_API_KEY`: Your OpenAI API key
   - `DATABASE_URL`: PostgreSQL connection string (consider using Cloudflare D1 or external DB)
   - Other environment variables from `.env`

### Optional

- **Docker** (for local testing)
- **Cloudflare API Token** (for CI/CD)

## Project Structure

```
assist_service/
├── Dockerfile                    # Container image for FastAPI app
├── app/                          # FastAPI application code
├── requirements.txt              # Python dependencies
└── js/                          # Cloudflare Workers code
    ├── package.json             # Node.js dependencies
    ├── tsconfig.json            # TypeScript configuration
    ├── wrangler.jsonc           # Cloudflare deployment config
    └── src/
        └── index.ts             # Worker routing logic
```

## Setup Instructions

### 1. Install Dependencies

Navigate to the `js/` directory and install Node.js dependencies:

```bash
cd js
npm install
```

### 2. Authenticate with Cloudflare

Login to your Cloudflare account via Wrangler:

```bash
npx wrangler login
```

This will open a browser window for authentication.

### 3. Configure Environment Variables

Set up your environment variables in Cloudflare:

```bash
# Set OpenAI API key
npx wrangler secret put OPENAI_API_KEY

# Set database URL
npx wrangler secret put DATABASE_URL

# Add other secrets as needed
npx wrangler secret put S3_ERRORDOCS_BUCKET
```

You can also configure environment variables in the Cloudflare dashboard:
1. Go to Workers & Pages
2. Select your worker
3. Go to Settings > Variables
4. Add environment variables

### 4. Review Configuration

Edit `js/wrangler.jsonc` to customize:

- **Worker name**: Change `"name": "assist-service-worker"` to your preferred name
- **Container instances**: Adjust `"max_instances": 10` based on your needs
- **Compatibility date**: Update `"compatibility_date"` if needed

### 5. Deploy to Cloudflare

From the `js/` directory, deploy the application:

```bash
npm run deploy
```

This command will:
1. Build the Docker container from `../Dockerfile`
2. Push the container image to Cloudflare
3. Deploy the Worker with routing logic
4. Set up Durable Objects for container management

### 6. Verify Deployment

After deployment, Wrangler will output your worker URL:

```
Published assist-service-worker (X.XX sec)
  https://assist-service-worker.YOUR_SUBDOMAIN.workers.dev
```

Test the deployment:

```bash
curl https://assist-service-worker.YOUR_SUBDOMAIN.workers.dev/
```

## Local Development

### Run Locally with Wrangler

Start the local development server:

```bash
cd js
npm run dev
```

This starts a local server at `http://localhost:8787` that simulates the Cloudflare environment.

### Test Container Locally

Build and test the Docker container locally:

```bash
# Build the container
docker build -t assist-service .

# Run the container
docker run -p 8080:8080 --env-file .env assist-service
```

Test the local container:

```bash
curl http://localhost:8080/
```

## Configuration

### Load Balancing

The worker distributes requests across **3 container instances** by default. To adjust this:

Edit `js/src/index.ts`:

```typescript
// Change the number of instances (default: 3)
const container = await getRandom(c.env.ASSIST_CONTAINER, 5);  // Now uses 5 instances
```

Also update `js/wrangler.jsonc`:

```jsonc
"max_instances": 5  // Match the number in index.ts
```

### Container Resources

Cloudflare Containers have the following limits:
- **CPU**: Shared across instances
- **Memory**: Varies by plan
- **Disk**: Ephemeral storage only

For persistent storage, use:
- **Cloudflare D1**: SQLite database
- **Cloudflare R2**: Object storage (S3-compatible)
- **External database**: PostgreSQL, etc.

### Monitoring

Enable observability in `wrangler.jsonc`:

```jsonc
"observability": {
  "enabled": true
}
```

View logs in the Cloudflare dashboard:
1. Go to Workers & Pages
2. Select your worker
3. Click "Logs" tab

Or stream logs via CLI:

```bash
npx wrangler tail
```

## Database Considerations

### Option 1: Cloudflare D1 (Recommended)

Use Cloudflare's native SQLite database:

1. Create a D1 database:
   ```bash
   npx wrangler d1 create assist-service-db
   ```

2. Add binding to `wrangler.jsonc`:
   ```jsonc
   "d1_databases": [
     {
       "binding": "DB",
       "database_name": "assist-service-db",
       "database_id": "YOUR_DATABASE_ID"
     }
   ]
   ```

3. Update application code to use D1 binding

### Option 2: External PostgreSQL

Connect to an external PostgreSQL database:

1. Ensure database is publicly accessible or use Cloudflare Tunnel
2. Set `DATABASE_URL` secret (see step 3 in Setup)
3. Configure connection pooling for better performance

### Option 3: Hybrid Approach

- Use D1 for application data
- Use R2 for document storage (replacing S3)
- Use external PostgreSQL for analytics

## OpenSearch Integration

For OpenSearch functionality:

1. **Self-hosted OpenSearch**
   - Host OpenSearch on a server accessible from Cloudflare
   - Use Cloudflare Tunnel for secure connection
   - Set `OPENSEARCH_HOST` environment variable

2. **AWS OpenSearch Service**
   - Ensure proper IAM permissions
   - Configure network access from Cloudflare IPs
   - Set authentication credentials

3. **Disable OpenSearch** (if not needed)
   - Set `USE_RAG=false` in environment variables

## Troubleshooting

### Container Fails to Start

**Check logs:**
```bash
npx wrangler tail
```

**Common issues:**
- Missing environment variables
- Database connection failures
- Port conflicts (ensure app listens on 0.0.0.0:8080)

### "Plan Required" Error

Cloudflare Containers requires a paid plan. Upgrade your account at [https://dash.cloudflare.com](https://dash.cloudflare.com).

### High Latency

**Solutions:**
- Increase `max_instances` for better load distribution
- Use Cloudflare's regional data centers
- Optimize database queries
- Enable caching where appropriate

### Memory Limits

If containers are killed due to memory:
- Optimize Python code for lower memory usage
- Reduce `max_instances` to give each container more resources
- Consider upgrading Cloudflare plan for higher limits

## CI/CD Integration

### GitHub Actions Example

Create `.github/workflows/deploy-cloudflare.yml`:

```yaml
name: Deploy to Cloudflare

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      
      - name: Install dependencies
        run: cd js && npm install
      
      - name: Deploy to Cloudflare
        env:
          CLOUDFLARE_API_TOKEN: ${{ secrets.CLOUDFLARE_API_TOKEN }}
        run: cd js && npm run deploy
```

### Required Secrets

Add to GitHub repository secrets:
- `CLOUDFLARE_API_TOKEN`: Create at [https://dash.cloudflare.com/profile/api-tokens](https://dash.cloudflare.com/profile/api-tokens)
  - Template: "Edit Cloudflare Workers"
  - Permissions: Workers Scripts:Edit

## Cost Estimation

Cloudflare Containers pricing (as of 2025):
- **Workers Paid plan**: $5/month base
- **Container CPU time**: Varies by usage
- **Requests**: First 10M requests/month included

Example monthly costs:
- Small deployment (<1M requests): ~$10-20
- Medium deployment (1-5M requests): ~$20-50
- Large deployment (5M+ requests): ~$50-200+

Check current pricing: [https://developers.cloudflare.com/workers/platform/pricing/](https://developers.cloudflare.com/workers/platform/pricing/)

## Additional Resources

- **Cloudflare Containers Documentation**: [https://developers.cloudflare.com/workers/runtime-apis/containers/](https://developers.cloudflare.com/workers/runtime-apis/containers/)
- **Wrangler Documentation**: [https://developers.cloudflare.com/workers/wrangler/](https://developers.cloudflare.com/workers/wrangler/)
- **Cloudflare Workers**: [https://developers.cloudflare.com/workers/](https://developers.cloudflare.com/workers/)
- **Example Repository**: [https://github.com/abyesilyurt/fastapi-on-cloudflare-containers](https://github.com/abyesilyurt/fastapi-on-cloudflare-containers)

## Support

For issues specific to:
- **Assist Service**: Create an issue in the repository
- **Cloudflare Deployment**: Check Cloudflare's documentation or community forums
- **OpenAI Integration**: Ensure API key is valid and has sufficient credits

## License

This deployment configuration is part of the Assist Service project. Refer to the main LICENSE file for details.
