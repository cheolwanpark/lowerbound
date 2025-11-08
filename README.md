# Crypto Portfolio - OHLCV Data Service

A production-ready microservice for fetching, storing, and serving cryptocurrency OHLCV (Open, High, Low, Close, Volume) data from Binance SPOT markets.

## Features

- **Automated Data Fetching**: Scheduled fetches every 12 hours with intelligent catch-up logic
- **Idempotent Backfill**: Safe initial data population (2 years or 90 days minimum)
- **Gap Detection & Filling**: Automatically identifies and fills missing data points
- **Rate Limiting**: Respects Binance API limits with token bucket rate limiting
- **Query-Time Forward Fill**: Optional forward-filling without corrupting source data
- **REST API**: FastAPI-based endpoints for querying historical data
- **PostgreSQL Storage**: High-precision NUMERIC types for financial data
- **Docker Compose**: Easy deployment with isolated scheduler and API services

## Architecture

```
┌─────────────────┐
│   Binance API   │
└────────┬────────┘
         │
         │ HTTPS (rate-limited)
         │
    ┌────┴─────────────────────────────┐
    │                                  │
┌───▼──────────┐            ┌──────────▼──┐
│  Scheduler   │            │  API Server │
│  (separate   │            │  (FastAPI)  │
│  container)  │            └──────┬──────┘
└───┬──────────┘                   │
    │                              │
    │        ┌─────────────────────┘
    │        │
    │   ┌────▼────────┐
    └───► PostgreSQL  │
        │  Database   │
        └─────────────┘
```

### Components

1. **API Service** (`src/server.py`): FastAPI server for querying OHLCV data
2. **Scheduler Service** (`src/scheduler.py`): Separate container running AsyncIOScheduler
3. **Database** (`src/database.py`): PostgreSQL with asyncpg for async operations
4. **Binance Client** (`src/fetch/binance_client.py`): Rate-limited HTTP client
5. **SPOT Fetcher** (`src/fetch/spot.py`): OHLCV fetching with gap detection
6. **Backfill Manager** (`src/fetch/backfill.py`): Idempotent historical data population

## Quick Start

### Prerequisites

- Docker & Docker Compose
- (Optional) Python 3.11+ with `uv` for local development

### 1. Clone and Configure

```bash
git clone <repository-url>
cd crypto-portfolio

# Copy environment template
cp .env.example .env

# Edit configuration (optional)
nano .env
```

### 2. Start Services

```bash
# Start all services (PostgreSQL, API, Scheduler)
docker-compose up -d

# View logs
docker-compose logs -f

# Check service status
docker-compose ps
```

### 3. Access API

- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/v1/health
- **Root Info**: http://localhost:8000/

## Configuration

Edit `.env` to customize settings:

```bash
# Database
DATABASE_URL=postgresql://crypto:password@postgres:5432/portfolio

# Binance API
BINANCE_API_BASE_URL=https://api.binance.com
BINANCE_RATE_LIMIT_REQUESTS_PER_MINUTE=5000
BINANCE_REQUEST_DELAY_MS=100

# Scheduler
FETCH_INTERVAL_HOURS=12          # Fetch interval (default: 12h)
INITIAL_BACKFILL_DAYS=730        # Target backfill period (2 years)
MIN_BACKFILL_DAYS=90             # Minimum backfill if 2 years unavailable

# Security
API_KEY=your-secret-key-here     # For protected endpoints

# Logging
LOG_LEVEL=INFO

# Assets (comma-separated)
TRACKED_ASSETS=BTC,ETH,SOL,BNB,XRP,ADA,LINK
```

## API Endpoints

### Public Endpoints

#### `GET /api/v1/health`

Health check with database status.

**Response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "timestamp": "2024-11-08T12:00:00Z"
}
```

#### `GET /api/v1/assets`

Get data coverage for all tracked assets.

**Response:**
```json
{
  "assets": [
    {
      "asset": "BTC",
      "earliest_timestamp": "2022-11-08T00:00:00Z",
      "latest_timestamp": "2024-11-08T12:00:00Z",
      "total_candles": 1460,
      "backfill_completed": true
    }
  ]
}
```

#### `GET /api/v1/ohlcv/{asset}`

Query OHLCV data for an asset.

**Parameters:**
- `asset` (path): Asset symbol (e.g., `BTC`)
- `start` (query): Start timestamp (ISO 8601)
- `end` (query): End timestamp (ISO 8601)
- `limit` (query): Max candles (1-10000)
- `fill` (query): Forward-fill missing candles (default: `false`)

**Example:**
```bash
curl "http://localhost:8000/api/v1/ohlcv/BTC?start=2024-11-01T00:00:00Z&end=2024-11-08T00:00:00Z&fill=false"
```

**Response:**
```json
{
  "asset": "BTC",
  "interval": "12h",
  "data": [
    {
      "timestamp": "2024-11-01T00:00:00Z",
      "open": "68500.50",
      "high": "69200.00",
      "low": "68100.25",
      "close": "68900.75",
      "volume": "1234.5678",
      "filled": false
    }
  ],
  "count": 14
}
```

### Protected Endpoints

Require `X-API-KEY` header.

#### `POST /api/v1/fetch/trigger`

Manually trigger a fetch job.

**Headers:**
```
X-API-KEY: your-secret-key-here
```

**Request Body:**
```json
{
  "assets": ["BTC", "ETH"],
  "start_date": "2024-11-01T00:00:00Z",
  "end_date": "2024-11-08T00:00:00Z"
}
```

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Fetch job queued for 2 asset(s)",
  "assets": ["BTC", "ETH"]
}
```

## Database Schema

### `spot_ohlcv` Table

Stores OHLCV candlestick data.

```sql
CREATE TABLE spot_ohlcv (
    id SERIAL PRIMARY KEY,
    asset VARCHAR(20) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    open NUMERIC(20, 8) NOT NULL,
    high NUMERIC(20, 8) NOT NULL,
    low NUMERIC(20, 8) NOT NULL,
    close NUMERIC(20, 8) NOT NULL,
    volume NUMERIC(30, 8) NOT NULL,
    UNIQUE(asset, timestamp)
);

CREATE INDEX idx_asset_timestamp ON spot_ohlcv(asset, timestamp DESC);
```

### `backfill_state` Table

Tracks backfill progress per asset.

```sql
CREATE TABLE backfill_state (
    asset VARCHAR(20) PRIMARY KEY,
    completed BOOLEAN DEFAULT FALSE,
    last_fetched_timestamp TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

## Development

### Local Setup (without Docker)

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv pip install -e .

# Start PostgreSQL (or use existing instance)
docker run -d \
  --name postgres \
  -e POSTGRES_USER=crypto \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=portfolio \
  -p 5432:5432 \
  postgres:16-alpine

# Run backfill (one-time)
python -m src.fetch.backfill

# Run API server
uvicorn src.server:app --reload

# Run scheduler (in separate terminal)
python -m src.scheduler
```

### Running Manual Backfill

```bash
# Inside Docker
docker-compose exec scheduler python -m src.fetch.backfill

# Force re-backfill (even if completed)
docker-compose exec scheduler python -m src.fetch.backfill --force
```

## Operational Considerations

### Rate Limiting

- Default limit: 5000 requests/min (safety margin below Binance's 6000/min)
- Minimum delay: 100ms between requests
- Automatic retry with exponential backoff on rate limit errors
- Semaphore limiting: Max 10 concurrent requests

### Gap Detection

The service automatically detects missing candles by:

1. Generating expected 12h timestamp series
2. Comparing with actual stored timestamps
3. Identifying missing ranges
4. Fetching only missing data

### Forward-Fill Strategy

**Query-time only** (never stored):

- When `?fill=true`: Missing candles filled with last known close price
- Filled candles marked with `"filled": true`
- Zero volume for filled candles
- Preserves data integrity

### Backfill Behavior

- **Idempotent**: Can be run multiple times safely
- **Resumable**: Tracks completion per asset
- **Graceful**: Failed assets don't block others
- **Range**: Fetches 2 years (730 days) or 90 days minimum

### Scheduler Logic

**Not periodic, but catch-up based:**

- Every 12 hours, checks latest timestamp per asset
- Calculates missing range: `(latest + 12h) to now`
- Fetches only new data
- Fills any detected gaps

## Monitoring

### Health Checks

```bash
# API health
curl http://localhost:8000/api/v1/health

# Database connection test
docker-compose exec postgres pg_isready -U crypto -d portfolio

# Scheduler logs
docker-compose logs -f scheduler
```

### Common Issues

**Scheduler running multiple times:**
- ✓ Fixed: Scheduler runs in separate container
- Each container has its own AsyncIOScheduler instance

**Rate limit exceeded:**
- Check `BINANCE_RATE_LIMIT_REQUESTS_PER_MINUTE` setting
- Increase `BINANCE_REQUEST_DELAY_MS`
- Review logs for concurrent fetch jobs

**Database connection errors:**
- Ensure PostgreSQL is healthy: `docker-compose ps`
- Check `DATABASE_URL` in `.env`
- Wait for database to be ready (healthcheck in docker-compose)

## Production Deployment

### Recommendations

1. **Remove development volumes** from `docker-compose.yml`:
   ```yaml
   # Remove this line:
   volumes:
     - ./src:/app/src
   ```

2. **Use secrets management**:
   - Store `API_KEY` in Docker secrets or vault
   - Use environment-specific `.env` files

3. **CORS configuration**:
   - Update `allow_origins` in `src/server.py` to specific domains

4. **Monitoring & Alerting**:
   - Add Prometheus metrics export
   - Set up alerts for fetch failures
   - Monitor database growth

5. **Scaling**:
   - API can scale horizontally (stateless)
   - Scheduler should run as **single instance**
   - Use managed PostgreSQL for production

## License

[Your License Here]

## Contributing

[Contributing Guidelines]
