# Deployment Guide

This guide covers deploying the Workflow Service to production environments.

## Render.com Deployment (Recommended for Quick Demo)

Render offers a free tier perfect for portfolio projects with automatic deployments from GitHub.

### Prerequisites
- GitHub account with this repository
- Render account (free): https://render.com

### Quick Deploy Steps

1. **Push your code to GitHub** (if not already done)
   ```bash
   git push origin main
   ```

2. **Create New Web Service on Render**
   - Go to https://dashboard.render.com
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Render will auto-detect `render.yaml` configuration

3. **Or Manual Setup:**
   - **Name**: workflow-service
   - **Environment**: Python
   - **Build Command**: `pip install -r workflow_service/requirements.txt`
   - **Start Command**: `gunicorn workflow_service.app.main:app --workers 2 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT`
   - **Environment Variables**:
     ```
     PYTHONPATH=/opt/render/project/src
     DATABASE_URL=sqlite:///./workflow.db
     LOG_LEVEL=INFO
     APP_ENV=production
     ```

4. **Deploy**
   - Click "Create Web Service"
   - Wait 2-5 minutes for initial deployment
   - Get your live URL: `https://workflow-service-XXXX.onrender.com`

5. **Update README**
   - Replace `XXXX` in README.md with your actual Render URL
   - Commit and push the update

### Verify Deployment

```bash
# Replace with your actual URL
export API_URL="https://your-service.onrender.com"

# Check health endpoint
curl $API_URL/health

# View API docs
open $API_URL/docs  # Or visit in browser

# Create a test record
curl -X POST $API_URL/records \
  -H "Content-Type: application/json" \
  -d '{"source":"demo","category":"test","payload":{"hello":"world"}}'
```

## Alternative Deployment Options

### Fly.io

1. Install flyctl: https://fly.io/docs/hands-on/install-flyctl/
2. Login: `fly auth login`
3. Create app: `fly launch`
4. Deploy: `fly deploy`

Configuration in `fly.toml`:
```toml
app = "workflow-service"

[build]
  builder = "paketobuildpacks/builder:base"

[env]
  PORT = "8000"
  PYTHONPATH = "/workspace"

[[services]]
  http_checks = []
  internal_port = 8000
  protocol = "tcp"

  [[services.ports]]
    handlers = ["http"]
    port = 80

  [[services.ports]]
    handlers = ["tls", "http"]
    port = 443
```

### Railway

1. Visit https://railway.app
2. Click "New Project" → "Deploy from GitHub"
3. Select your repository
4. Railway auto-detects Python and deploys
5. Add environment variables in dashboard

### Docker Deployment (Any Platform)

Build and push to container registry:
```bash
docker build -t workflow-service .
docker tag workflow-service:latest your-registry/workflow-service:latest
docker push your-registry/workflow-service:latest
```

Run on any Docker host:
```bash
docker run -d \
  -p 8000:8000 \
  -e DATABASE_URL=sqlite:///./workflow.db \
  -e LOG_LEVEL=INFO \
  -e APP_ENV=production \
  your-registry/workflow-service:latest
```

## Production Considerations

### Database
- **Current**: SQLite (suitable for demo/low traffic)
- **Recommended for production**: PostgreSQL
- Set `DATABASE_URL` to Postgres connection string
- No code changes required (SQLAlchemy handles both)

### CORS
Update `ALLOWED_ORIGINS` environment variable:
```bash
ALLOWED_ORIGINS=https://your-frontend.com,https://app.example.com
```

### Monitoring
- Health endpoint: `GET /health` (returns 503 if unhealthy)
- Check logs in your hosting platform's dashboard
- All requests logged with unique `request_id`

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | No | `sqlite:///./workflow.db` | Database connection string |
| `LOG_LEVEL` | No | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `APP_ENV` | No | `dev` | Environment (dev, staging, production) |
| `ALLOWED_ORIGINS` | No | `http://localhost:3000,http://localhost:8000` | CORS allowed origins (comma-separated) |
| `PYTHONPATH` | Platform-specific | - | Python module path (usually auto-configured) |

### Security Checklist
- ✅ CORS restricted to known origins
- ✅ No debug mode in production
- ✅ Environment variables for sensitive config
- ✅ Health checks enabled
- ✅ Request ID logging for traceability
- ⚠️ Consider adding API authentication (future enhancement)

## Troubleshooting

### Service won't start
- Check logs for import errors
- Verify `PYTHONPATH` is set correctly
- Ensure all dependencies in requirements.txt

### Database errors
- SQLite file permissions (if using SQLite)
- Connection string format for Postgres
- Check health endpoint for DB status

### CORS errors
- Verify `ALLOWED_ORIGINS` includes your frontend domain
- Check browser console for specific CORS error
- Ensure protocol matches (http vs https)

### Free tier sleep (Render)
- Free tier sleeps after 15 minutes of inactivity
- First request may take 30-60 seconds to wake up
- Consider upgrading to paid tier for always-on service

## Next Steps

After deployment:
1. Update README.md with your live URL
2. Test all endpoints via `/docs` interface
3. Share the link in your portfolio/resume
4. Consider adding:
   - Database migrations (Alembic)
   - PostgreSQL for production
   - API authentication
   - Rate limiting
   - Caching layer
