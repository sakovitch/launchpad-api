# Launchpad API - v2.0

REST API server pre Launchpad Dashboard a Wear OS aplikáciu.

## Funkcie

- ✅ JWT-based authentication
- ✅ Multi-warehouse support
- ✅ Time tracking (start/stop/cancel)
- ✅ Client and task management
- ✅ Environment-based configuration
- ✅ CORS enabled

## Setup

### 1. Inštalácia dependencies

```bash
pip install -r requirements.txt
```

### 2. Environment Variables Setup

Vytvor `.env` súbor na základe `.env.example`:

```bash
cp .env.example .env
```

Vyplň všetky potrebné environment variables:

```
DB_HOST=sql20.hostcreators.sk
DB_NAME=d57154_launchpadgroup
DB_PASSWORD=...
DB_PORT=3325
DB_USER=d57154_launchpad
SECRET_KEY=...
DEBUG=False
ENVIRONMENT=production
```

### 3. Spustenie servera (Local Development)

```bash
python flask_app.py
```

Server pobeží na `http://localhost:5000`

### 4. Deployment na Render

1. Push súbory na GitHub
2. Vytvor novú Web Service na Render.com
3. Pridaj všetky environment variables v Render dashboarde
4. Render automaticky deploying

## API Endpoints

### Authentication

**POST /api/login**
```json
{
  "username": "admin",
  "password": "admin123"
}
```

Response:
```json
{
  "token": "eyJhbGc...",
  "user": {
    "username": "admin",
    "full_name": "Admin User",
    "warehouse": "WH1",
    "role": "admin"
  }
}
```

### Clients

**GET /api/clients**
```
Headers: Authorization: Bearer <token>
```

Response:
```json
{
  "clients": [
    {"id": 1, "name": "Client A", "warehouse": "WH1"},
    {"id": 2, "name": "Client B", "warehouse": "WH1"}
  ]
}
```

### Tasks

**GET /api/tasks**
```
Headers: Authorization: Bearer <token>
```

Response:
```json
{
  "tasks": [
    {"id": 1, "name": "Task A", "warehouse": "WH1"},
    {"id": 2, "name": "Task B", "warehouse": "WH1"}
  ]
}
```

### Timer

**POST /api/timer/start**
```json
{
  "client_id": 1
}
```

Response:
```json
{
  "success": true,
  "record_id": 123,
  "message": "Časovač spustený"
}
```

**POST /api/timer/stop**
```json
{
  "record_id": 123,
  "task_id": 1
}
```

**POST /api/timer/cancel**
```json
{
  "record_id": 123
}
```

**GET /api/timer/active**
```
Headers: Authorization: Bearer <token>
```

Response:
```json
{
  "active": true,
  "record": {
    "record_id": 123,
    "client_name": "Client A",
    "start_time": "2025-10-29T10:30:00",
    "elapsed_seconds": 300
  }
}
```

## Bezpečnosť

- Všetky passwords sa hashujú SHA256
- JWT tokens platné 30 dní
- Všetky citlivé údaje v environment variables
- CORS povolený len pre potrebné sources
- Password change možný len adminom

## Database Schema

Vyžaduje existujúce tabuľky v MySQL:

- `users` - informácie o užívateľoch
- `clients` - zoznam klientov
- `tasks` - zoznam úkonov
- `time_records` - záznamy času

## Technológie

- Flask 3.0.0
- PyJWT 2.8.1
- MySQL Connector 8.2.0
- Python 3.10+

## Author

Developed for Launchpad Group Dashboard
