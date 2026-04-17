# Day 12 Lab - Mission Answers

> **Student Name:** Trần Nhật Hoàng  
> **Student ID:** 2A202600431  
> **Date:** 17/04/2026

---

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found

Phân tích file `01-localhost-vs-production/develop/app.py`, tìm được **5 anti-patterns** sau:

1. **API key hardcode trong code** (dòng 17-18): `OPENAI_API_KEY = "sk-hardcoded-fake-key-never-do-this"` và `DATABASE_URL = "postgresql://admin:password123@localhost:5432/mydb"`. Nếu push lên GitHub, secret bị lộ ngay lập tức. Attacker có thể dùng key để gọi API tốn tiền hoặc truy cập database.

2. **Không có config management** (dòng 21-22): `DEBUG = True` và `MAX_TOKENS = 500` được hardcode. Không thể thay đổi giữa các môi trường (dev/staging/production) mà không sửa code. Giải pháp: dùng environment variables hoặc config file.

3. **Dùng print() thay vì proper logging** (dòng 33-38): `print(f"[DEBUG] Got question: {question}")` và đặc biệt nguy hiểm là `print(f"[DEBUG] Using key: {OPENAI_API_KEY}")` — log ra secret! Trong production cần structured logging (JSON format) để dễ parse trong log aggregator (Datadog, Loki, CloudWatch).

4. **Không có health check endpoint**: Nếu agent crash hoặc bị treo, cloud platform (Railway, Render, K8s) không biết để restart container. Cần endpoint `GET /health` trả về status để platform monitoring.

5. **Port cố định và binding localhost** (dòng 49-53): `host="localhost"` chỉ chạy được trên local, không nhận connection từ bên ngoài container. `port=8000` cứng, trong khi Railway/Render inject PORT qua env var. `reload=True` chạy debug mode trong production gây security risk.

### Exercise 1.3: Comparison table

| Feature | Develop (Basic) | Production (Advanced) | Tại sao quan trọng? |
|---------|----------------|----------------------|---------------------|
| Config | Hardcode trong code | Environment variables (`os.getenv`) | Config tách khỏi code, dễ thay đổi giữa các môi trường, không lộ secrets |
| Health check | Không có | `GET /health` + `GET /ready` | Platform cần biết container còn sống không để restart khi cần |
| Logging | `print()` — log cả secrets | Structured JSON logging, KHÔNG log secrets | Dễ parse trong log aggregator, an toàn, tìm bug nhanh hơn |
| Shutdown | Đột ngột — request đang xử lý bị mất | Graceful — SIGTERM handler, chờ request hoàn thành | Tránh mất data, user không bị lỗi giữa chừng |
| Host binding | `localhost` (chỉ local) | `0.0.0.0` (nhận connection từ bên ngoài) | Container/cloud cần kết nối từ bên ngoài vào |
| Port | Cứng `8000` | Đọc từ `PORT` env var | Railway/Render inject PORT tự động, cứng sẽ bị conflict |
| CORS | Không có | Middleware với allowed_origins | Kiểm soát ai có thể gọi API từ browser |
| Reload | `reload=True` luôn bật | Chỉ bật khi `DEBUG=true` | Hot reload trong production gây security risk và performance issues |

---

## Part 2: Docker

### Exercise 2.1: Dockerfile questions

Phân tích file `02-docker/develop/Dockerfile`:

1. **Base image:** `python:3.11` — full Python distribution, khoảng ~1 GB. Đây là image đầy đủ, bao gồm cả build tools, nhưng nặng không cần thiết cho production.

2. **Working directory:** `/app` — đặt bởi lệnh `WORKDIR /app`. Tất cả lệnh sau (COPY, RUN, CMD) sẽ chạy trong thư mục này.

3. **Tại sao COPY requirements.txt trước?** Docker sử dụng **layer caching**. Khi file requirements.txt không đổi, Docker dùng lại cache cho layer `RUN pip install`. Chỉ khi code thay đổi (COPY app.py), Docker mới rebuild từ layer đó trở đi. Nếu COPY tất cả cùng lúc, mỗi lần sửa code đều phải cài lại dependencies → chậm.

4. **CMD vs ENTRYPOINT:**
   - `CMD`: Command mặc định khi container start, có thể override bằng `docker run <image> <new-command>`
   - `ENTRYPOINT`: Command cố định, không dễ override. Arguments truyền vào sẽ append vào ENTRYPOINT
   - Thường dùng `ENTRYPOINT` cho executable chính và `CMD` cho default arguments

### Exercise 2.3: Image size comparison

So sánh image size giữa develop (single-stage) và production (multi-stage):

- **Develop** (python:3.11 full): ~1000 MB — bao gồm gcc, build tools, docs
- **Production** (python:3.11-slim multi-stage): ~200-300 MB — chỉ có runtime Python + installed packages
- **Difference:** ~60-70% nhỏ hơn

**Tại sao multi-stage nhỏ hơn?**
- Stage 1 (builder): Cài gcc, libpq-dev, compile dependencies → image nặng nhưng KHÔNG deploy
- Stage 2 (runtime): Chỉ COPY compiled packages từ builder + source code → nhẹ, sạch
- Kết quả: Image final chỉ chứa những gì CẦN để CHẠY, không chứa build tools

**Docker Compose Architecture** (`02-docker/production/docker-compose.yml`):
```
Client → Nginx (port 80/443) → Agent (port 8000) → Redis (cache/session)
                                                  → Qdrant (vector DB)
```
- **4 services**: agent, redis, qdrant, nginx
- **Nginx**: Reverse proxy + load balancer, expose port 80/443
- **Agent**: FastAPI app, không expose port trực tiếp (qua Nginx)
- **Redis**: Session cache + rate limiting, healthcheck `redis-cli ping`
- **Qdrant**: Vector database cho RAG
- **Network**: `internal` bridge — isolate traffic giữa các services

---

## Part 3: Cloud Deployment

### Exercise 3.1: Railway deployment

- **URL:** _(Deployed via Railway CLI — URL generated after `railway up`)_
- **Platform:** Railway
- **Config file:** `railway.toml` với settings:
  - Builder: DOCKERFILE (dùng multi-stage Dockerfile)
  - Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2`
  - Health check path: `/health`
  - Restart policy: ON_FAILURE (max 3 retries)

**Deployment steps:**
```bash
# 1. Install Railway CLI
npm i -g @railway/cli

# 2. Login
railway login

# 3. Initialize project
railway init

# 4. Set environment variables
railway variables set PORT=8000
railway variables set AGENT_API_KEY=my-secret-key

# 5. Deploy
railway up

# 6. Get public URL
railway domain
```

### Exercise 3.2: So sánh render.yaml vs railway.toml

| Feature | railway.toml | render.yaml |
|---------|-------------|-------------|
| Format | TOML | YAML |
| Builder | `builder = "DOCKERFILE"` | `runtime: docker` |
| Health check | `healthcheckPath = "/health"` | `healthCheckPath: /health` |
| Env vars | Qua CLI `railway variables set` | Inline trong YAML + `generateValue: true` |
| Auto deploy | Mặc định khi push | `autoDeploy: true` |
| Region | Auto | `region: singapore` |
| Restart | `restartPolicyType = "ON_FAILURE"` | Tự động |
| Secrets | CLI-based | `sync: false` (manual set trong dashboard) |

---

## Part 4: API Security

### Exercise 4.1-4.3: Test results

#### API Key Authentication (`04-api-gateway/develop/app.py`)

- **API key check location:** Trong hàm `verify_api_key()` (dòng 39-54), dùng FastAPI dependency injection với `APIKeyHeader(name="X-API-Key")`
- **Sai key:** Trả về HTTP 403 "Invalid API key." nếu key sai, HTTP 401 "Missing API key" nếu không có key
- **Rotate key:** Thay đổi env var `AGENT_API_KEY` và restart server. Tất cả client phải cập nhật key mới.

**Test results:**
```bash
# ❌ Không có key → 401
$ curl http://localhost:8000/ask -X POST \
  -H "Content-Type: application/json" \
  -d '{"question": "Hello"}'
# Response: {"detail": "Missing API key. Include header: X-API-Key: <your-key>"}

# ✅ Có key → 200
$ curl http://localhost:8000/ask -X POST \
  -H "X-API-Key: dev-key-change-me" \
  -H "Content-Type: application/json" \
  -d '{"question": "Hello"}'
# Response: {"question": "Hello", "answer": "...", "model": "gpt-4o-mini", ...}
```

#### JWT Authentication (`04-api-gateway/production/auth.py`)

JWT flow:
1. Client gửi `POST /auth/token` với username/password
2. Server verify credentials, tạo JWT token (chứa sub, role, iat, exp)
3. Client gửi requests tiếp theo với header `Authorization: Bearer <token>`
4. Server verify token signature → extract user info → process request
5. Token hết hạn sau 60 phút

#### Rate Limiting (`04-api-gateway/production/rate_limiter.py`)

- **Algorithm:** Sliding Window Counter
- **Mechanism:** Mỗi user có 1 deque lưu timestamps. Xóa timestamps ngoài window (60s), đếm số request còn lại.
- **Limit:** 10 requests/minute cho user, 100 req/min cho admin
- **Bypass cho admin:** Dùng instance `rate_limiter_admin` với limit 100 thay vì `rate_limiter_user` limit 10
- **Response khi hit limit:** HTTP 429 với headers `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `Retry-After`

### Exercise 4.4: Cost guard implementation

**Approach:** Dùng class `CostGuard` với 2 level budget protection:

1. **Per-user daily budget** ($1/ngày): Track input/output tokens của mỗi user. Khi vượt → HTTP 402 "Payment Required"
2. **Global daily budget** ($10/ngày): Tổng chi phí tất cả users. Khi vượt → HTTP 503 "Service temporarily unavailable"
3. **Warning at 80%:** Log warning khi user dùng ≥ 80% budget

**Token cost calculation:**
```python
cost = (input_tokens / 1000) * 0.00015 + (output_tokens / 1000) * 0.0006
```

**Implementation (simplified):**
```python
def check_budget(user_id: str) -> None:
    record = self._get_record(user_id)
    if self._global_cost >= self.global_daily_budget_usd:
        raise HTTPException(503, "Budget exceeded")
    if record.total_cost_usd >= self.daily_budget_usd:
        raise HTTPException(402, "Daily budget exceeded")

def record_usage(user_id, input_tokens, output_tokens) -> UsageRecord:
    record = self._get_record(user_id)
    record.input_tokens += input_tokens
    record.output_tokens += output_tokens
    record.request_count += 1
    self._global_cost += calculated_cost
    return record
```

---

## Part 5: Scaling & Reliability

### Exercise 5.1-5.5: Implementation notes

#### 5.1: Health Checks

Implemented 2 endpoints:

```python
@app.get("/health")
def health():
    """Liveness probe — container còn sống không?"""
    return {
        "status": "ok",
        "version": settings.app_version,
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

@app.get("/ready")
def ready():
    """Readiness probe — sẵn sàng nhận traffic không?"""
    if not _is_ready:
        raise HTTPException(503, "Not ready")
    return {"ready": True}
```

- **Health (Liveness):** Trả về 200 nếu process OK. Platform restart container nếu endpoint fail.
- **Ready (Readiness):** Trả về 200 nếu sẵn sàng, 503 nếu đang startup/shutdown. Load balancer dùng để quyết định route traffic.

#### 5.2: Graceful Shutdown

```python
signal.signal(signal.SIGTERM, _handle_signal)

# uvicorn với timeout_graceful_shutdown=30
uvicorn.run(
    "app.main:app",
    timeout_graceful_shutdown=30,  # chờ max 30s cho request hoàn thành
)
```

- Khi nhận SIGTERM: Log signal, uvicorn tự handle graceful shutdown
- Lifespan: set `_is_ready = False` → readiness probe trả 503 → LB ngừng route traffic
- Chờ request đang xử lý hoàn thành (max 30s) → đóng connections → exit

#### 5.3: Stateless Design

**Anti-pattern (Stateful):**
```python
# ❌ State trong memory — mất khi restart, không chia sẻ giữa instances
conversation_history = {}
```

**Correct (Stateless):**
```python
# ✅ State trong Redis — bất kỳ instance nào cũng đọc được
def save_session(session_id, data):
    redis.setex(f"session:{session_id}", ttl, json.dumps(data))

def load_session(session_id):
    data = redis.get(f"session:{session_id}")
    return json.loads(data) if data else {}
```

**Tại sao?** Khi scale ra 3 instances:
- Instance 1 nhận request 1 của User A → lưu history trong memory
- Instance 2 nhận request 2 của User A → KHÔNG có history! Bug!
- Với Redis: bất kỳ instance nào cũng đọc/ghi cùng 1 Redis → nhất quán

#### 5.4: Load Balancing

Dùng Nginx làm reverse proxy:
```
docker compose up --scale agent=3
```

- Nginx phân tán requests theo round-robin tới 3 agent instances
- Nếu 1 instance die, Nginx tự route tới instances còn lại
- Agent không expose port trực tiếp, chỉ qua Nginx

#### 5.5: Stateless Test

`test_stateless.py` kiểm tra:
1. Gọi API tạo conversation → lưu session_id
2. Gọi tiếp với session_id → conversation history còn nguyên
3. Bất kỳ instance nào serve đều có cùng data (vì lưu Redis)

Kết quả: Conversation history persistent across instances, không phụ thuộc vào instance cụ thể.

---

## Part 6: Final Project — 06-lab-complete

### Architecture

```
Client
  │
  ▼
Nginx (Load Balancer) — port 80
  │
  ├──→ Agent Instance 1 ─┐
  ├──→ Agent Instance 2 ─┤──→ Redis (session/cache)
  └──→ Agent Instance 3 ─┘
```

### Features Implemented

| Feature | Status | File |
|---------|--------|------|
| REST API (`POST /ask`) | ✅ | `app/main.py` |
| Config from env vars | ✅ | `app/config.py` |
| API Key auth | ✅ | `app/auth.py` |
| Rate limiting (20 req/min) | ✅ | `app/rate_limiter.py` |
| Cost guard ($5/day) | ✅ | `app/cost_guard.py` |
| Health check | ✅ | `app/main.py` → `/health` |
| Readiness check | ✅ | `app/main.py` → `/ready` |
| Graceful shutdown | ✅ | `app/main.py` → SIGTERM handler |
| Multi-stage Dockerfile | ✅ | `Dockerfile` |
| Docker Compose | ✅ | `docker-compose.yml` |
| Structured JSON logging | ✅ | `app/main.py` |
| Security headers | ✅ | `app/main.py` → middleware |
| Railway config | ✅ | `railway.toml` |
| Render config | ✅ | `render.yaml` |
| Input validation | ✅ | Pydantic `AskRequest` model |
| CORS | ✅ | FastAPI CORS middleware |
