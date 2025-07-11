# Enode POC App

## 🐳 Run with Docker Compose

1. Clone the repo or create `.env` using this template:

```dotenv
# Copy from .env.example
MYSQL_HOST=db
MYSQL_PORT=3306
MYSQL_USER=your_user
MYSQL_PASSWORD=your_pass
MYSQL_DATABASE=enode

ENODE_CLIENT_ID=your_client_id
ENODE_CLIENT_SECRET=your_client_secret
WEBHOOK_SECRET=your_webhook_secret
```

2. Run the app:

```bash
docker-compose up
```

3. App runs at: [http://localhost:5000](http://localhost:5000)
