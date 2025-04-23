# 🧠 Bittensor Sentiment API

An asynchronous FastAPI backend service to query Tao dividends from the
Bittensor blockchain, perform sentiment analysis on Twitter activity, and
automatically trigger stake/unstake operations based on sentiment scores.

## Features

- Query Tao dividends from the Bittensor chain
- Redis caching (2-minute TTL) for repeated requests
- Sentiment analysis pipeline:
  - [Datura.ai](https://docs.datura.ai/guides/capabilities/twitter-search)
  - [Chutes.ai](https://chutes.ai/)
- Automatic staking/unstaking via
  [`AsyncSubtensor`](https://github.com/opentensor/bittensor)
- Fully asynchronous stack with FastAPI, Celery, Redis, PostgreSQL
- Comprehensive test suite using `pytest`, `respx`, and `httpx`

## Architecture

```text
              +---------------------+
              |   FastAPI Server    |
              +---------------------+
                  |           |
                  | Redis     | PostgreSQL (SQLModel)
                  ↓           ↓
          [Caching Layer]   [Stake History]
                  |
              Celery Broker
                  ↓
     +------------------------+
     |  Celery Worker (async) |
     +------------------------+
       |     |           |
   Datura  Chutes    AsyncSubtensor
```

## Installation

### Requirements

- Docker + Docker Compose
- Python 3.10+ (only if running locally without Docker)

### Environment Variables

Create a `.env` file or copy from the provided `.env.example`:

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/main
REDIS_URL=redis://redis:6379/0
AUTH_TOKEN=your_auth_token
DATURA_API_KEY=dt_$your_datura_key
CHUTES_API_KEY=cpk_$your_chutes_key
```

## Run with Docker

```bash
make run
```

This will start:

- API: [http://localhost:8000](http://localhost:8000)
- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- Redis: port 6379
- PostgreSQL: port 5432

## Run Tests

```bash
make check
```

Test coverage includes:

- Unit tests for `chutes_service`, `datura_service`, `substrate_service`, etc.
- Functional test for `/api/v1/tao_dividends`
- Concurrency test using `asyncio.gather`

## Authentication

All endpoints are protected via an `Authorization` header.

```bash
curl -X GET "http://localhost:8000/api/v1/tao_dividends?netuid=18&hotkey=5FFApaS75bv5pJHfAp2FVLBj9ZaXuFDjEypsaBNc1wCfe52v&trade=true" -q -H \"Authorization: supersecret123\"
```

## API Reference

### `GET /api/v1/tao_dividends`

Queries blockchain for Tao dividends and (optionally) triggers stake/unstake
logic based on Twitter sentiment.

#### Parameters

| Name     | Type    | Optional | Description                                                 |
| -------- | ------- | -------- | ----------------------------------------------------------- |
| `netuid` | int     | Yes      | Subnet ID (default = 18)                                    |
| `hotkey` | string  | Yes      | Hotkey SS58 account (default = demo account)                |
| `trade`  | boolean | Yes      | If `true`, triggers sentiment-based stake/unstake operation |

#### Example

```bash
curl -X GET "http://localhost:8000/api/v1/tao_dividends?netuid=18&trade=true" \
  -H "Authorization: your_auth_token"
```

#### Response

```json
{
  "netuid": 18,
  "hotkey": "5F...",
  "dividend": 123456,
  "cached": false,
  "stake_tx_triggered": true
}
```

## Project Structure

```
 app
├──  api                  # FastAPI routes
├──  cache                # Redis async cache
├──  core                 # Config & auth
├──  db                   # DB session & startup
├──  main.py              # FastAPI app entrypoint
├──  models               # SQLModel schemas
├──  services             # Bittensor, Chutes, Datura APIs
└──  tasks.py             # Celery tasks
 tests                    # Unit and functional tests
```

## Notes

- Sentiment is parsed from LLM output using a regex to extract float from
  Chutes.ai.
- Stake/Unstake logic is based on `0.01 * abs(sentiment)`, limited for safety.
- Concurrent requests are supported and tested with mocked Redis and blockchain
  layers.
