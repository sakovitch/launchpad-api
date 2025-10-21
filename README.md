# Launchpad API Server

REST API for Launchpad Dashboard - connects Wear OS watch app with the backend system.

## 🚀 Deployment (Render.com)

### Environment Variables Required

Set these in Render.com dashboard:

```
DB_HOST=your_mysql_host
DB_PORT=3325
DB_USER=your_username
DB_PASSWORD=your_password
DB_NAME=your_database
SECRET_KEY=your-jwt-secret-key
```

### Deploy Command

```bash
gunicorn api_server:app
```

## 🔧 Local Development

1. Clone the repository
2. Copy `config.example.py` to `config.py` and fill in your values
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the server:
   ```bash
   python api_server.py
   ```

## 📡 API Endpoints

### Authentication
- `POST /api/login` - User login, returns JWT token

### Clients
- `GET /api/clients` - Get list of clients for user's warehouse

### Tasks
- `GET /api/tasks` - Get list of available tasks/actions

### Timer
- `POST /api/timer/start` - Start timer for a client
- `POST /api/timer/stop` - Stop timer and save record with task
- `POST /api/timer/cancel` - Cancel timer (delete record without saving)
- `GET /api/timer/active` - Get active timer for user

## 🔒 Security

⚠️ **NEVER commit `config.py` to the repository!**

- `config.py` contains sensitive database credentials
- Use environment variables in production (Render.com)
- Use `config.example.py` as template for local development

## 📱 Connected Apps

- **Wear OS Watch App** - Android smartwatch timer application
- **Desktop Dashboard** - Python/CustomTkinter management application
