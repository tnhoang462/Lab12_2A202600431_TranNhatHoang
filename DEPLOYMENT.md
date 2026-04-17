# Deployment Information

> **Student Name:** Trần Nhật Hoàng  
> **Student ID:** 2A202600431  
> **Date:** 17/04/2026

---

## Public URL

> **Note:** URL sẽ được cập nhật sau khi deploy lên Railway/Render.
> Hiện tại project đã được cấu hình sẵn để deploy.

```
https://lab122a202600431trannhathoang-production.up.railway.app
```

## Platform

**Railway** (primary) / **Render** (alternative)

- Railway config: `06-lab-complete/railway.toml`
- Render config: `06-lab-complete/render.yaml`

---

## Test Commands

### Health Check
```bash
curl https://lab122a202600431trannhathoang-production.up.railway.app/health
# Expected: {"status": "ok", "version": "1.0.0", ...}
```

### Readiness Check
```bash
curl https://lab122a202600431trannhathoang-production.up.railway.app/ready
# Expected: {"ready": true}
```

### API Test (with authentication)
```bash
curl -X POST https://lab122a202600431trannhathoang-production.up.railway.app/ask \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is deployment?"}'
# Expected: {"question": "...", "answer": "...", "model": "gpt-4o-mini", "timestamp": "..."}
```

### Test without API key (should fail)
```bash
curl -X POST https://lab122a202600431trannhathoang-production.up.railway.app/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Hello"}'
# Expected: 401 {"detail": "Missing API key..."}
```

### Rate Limiting Test
```bash
for i in {1..25}; do
  echo "Request $i:"
  curl -s -X POST https://lab122a202600431trannhathoang-production.up.railway.app/ask \
    -H "X-API-Key: YOUR_KEY" \
    -H "Content-Type: application/json" \
    -d "{\"question\": \"test $i\"}"
  echo ""
done
# After 20 requests: 429 {"detail": {"error": "Rate limit exceeded", ...}}
```

---

## Local Testing

### Run with Docker Compose
```bash
cd 06-lab-complete
cp .env.example .env.local
docker compose up
```

### Test locally
```bash
# Health check
curl http://localhost:8000/health

# API test
curl -X POST http://localhost:8000/ask \
  -H "X-API-Key: dev-key-change-me" \
  -H "Content-Type: application/json" \
  -d '{"question": "Hello"}'
```

### Run without Docker
```bash
cd 06-lab-complete
pip install -r requirements.txt
python -m app.main
```

---

## Deploy to Railway

```bash
# 1. Install Railway CLI
npm i -g @railway/cli

# 2. Login
railway login

# 3. Initialize project
railway init

# 4. Set environment variables
railway variables set PORT=8000
railway variables set AGENT_API_KEY=your-secret-key-here
railway variables set ENVIRONMENT=production
railway variables set JWT_SECRET=your-jwt-secret-here

# 5. Deploy
railway up

# 6. Get public URL
railway domain
```

## Deploy to Render

1. Push repo to GitHub
2. Go to [render.com](https://render.com) → Sign up
3. New → Blueprint
4. Connect GitHub repo
5. Render reads `render.yaml` automatically
6. Set secrets in dashboard: `OPENAI_API_KEY`, `AGENT_API_KEY`
7. Deploy!

---

## Environment Variables Set

| Variable | Description | Required |
|----------|-------------|----------|
| `PORT` | Server port (default: 8000) | ✅ |
| `AGENT_API_KEY` | API key for authentication | ✅ |
| `ENVIRONMENT` | development / staging / production | ✅ |
| `JWT_SECRET` | Secret for JWT token signing | ✅ (production) |
| `REDIS_URL` | Redis connection URL | Optional |
| `OPENAI_API_KEY` | OpenAI API key (mock if not set) | Optional |
| `LOG_LEVEL` | Logging level | Optional |
| `DAILY_BUDGET_USD` | Daily budget limit (default: 5.0) | Optional |
| `RATE_LIMIT_PER_MINUTE` | Rate limit (default: 20) | Optional |

---

## Project Structure

```
06-lab-complete/
├── app/
│   ├── __init__.py        # Package init
│   ├── main.py            # Main application entry point
│   ├── config.py          # 12-factor configuration
│   ├── auth.py            # API Key + JWT authentication
│   ├── rate_limiter.py    # Sliding window rate limiting
│   └── cost_guard.py      # Budget protection
├── utils/
│   └── mock_llm.py        # Mock LLM (no API key needed)
├── Dockerfile             # Multi-stage build (< 500 MB)
├── docker-compose.yml     # Full stack (agent + redis)
├── requirements.txt       # Python dependencies
├── .env.example           # Environment template
├── .dockerignore          # Docker ignore rules
├── railway.toml           # Railway deployment config
├── render.yaml            # Render deployment config
├── check_production_ready.py  # Production readiness checker
└── README.md              # Setup instructions
```

---

## Production Readiness Checklist

- [x] Multi-stage Dockerfile (image < 500 MB)
- [x] Docker Compose with Redis
- [x] API Key authentication
- [x] Rate limiting (20 req/min)
- [x] Cost guard ($5/day per user)
- [x] Health check endpoint (`GET /health`)
- [x] Readiness endpoint (`GET /ready`)
- [x] Graceful shutdown (SIGTERM handler)
- [x] Structured JSON logging
- [x] Config from environment variables
- [x] No hardcoded secrets
- [x] .dockerignore configured
- [x] Security headers (X-Content-Type-Options, X-Frame-Options)
- [x] CORS middleware
- [x] Input validation (Pydantic models)
