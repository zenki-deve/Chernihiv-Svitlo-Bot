# Chernihiv Svitlo Bot

An asynchronous Telegram bot written in aiogram 3, which checks the outage schedules through the personal account and sends notifications when changes occur. Storage is PostgreSQL.

## Stack 
- Python 3.12+ (Docker base image: `python:3.12-slim`).
- aiogram 3, aiohttp, asyncpg, python-dotenv, colorama (see `requirements.txt`).
- DB: PostgreSQL (managed via Docker Compose).

## Run with Docker (Recommended)
The project is configured to run with Docker and Docker Compose, which is the easiest and recommended way to get started.

1.  **Clone the repository:**
    ```powershell
    git clone https://github.com/zenki-deve/Chernihiv-Svitlo-Bot.git
    cd Chernihiv-Svitlo-Bot
    ```

2.  **Create Environment File:**
    Create a file named `.env` in the root of the project and add your configuration.
    ```env
    # Telegram Bot Token
    API_TOKEN=your_bot_token

    # PostgreSQL Connection Settings
    DB_USER=your_db_user
    DB_PASSWORD=your_db_password
    DB_NAME=your_db_name
    ```

3.  **Build and Run the Containers:**
    Use Docker Compose to build the images and run the services in the background.
    ```powershell
    docker compose up --build -d
    ```

4.  **Check Logs:**
    To see the bot's logs, run:
    ```powershell
    docker compose logs -f cernihiv-svitlo-bot
    ```

5.  **Stop the Services:**
    To stop the bot and the database, run:
    ```powershell
    docker compose down
    ```
    The PostgreSQL data is stored in a Docker volume (`postgres_data`) and will be persisted across restarts.

## Environment Variables
- `API_TOKEN` — **(Required)** Your Telegram bot token from @BotFather.
- `DB_USER` — **(Required)** Username for the PostgreSQL database.
- `DB_PASSWORD` — **(Required)** Password for the PostgreSQL database.
- `DB_NAME` — **(Required)** Name of the PostgreSQL database.
- `DB_HOST` - (For bot service) The hostname of the database. Set to `db` in `docker-compose.yml`.
- `DB_PORT` - (For bot service) The port of the database. Set to `5432` in `docker-compose.yml`.
- `CACHE_SEC` - (Optional) Cache TTL in seconds for provider responses and update checks; helps rate-limit requests; default is 600.

## Files/directories that matter
- `bot.py` — Entry point; starts the dispatcher and background polling loop.
- `config.py` — Loads `.env` and provides configuration.
- `database/` — Contains all `asyncpg` logic for interacting with the PostgreSQL database.
- `utils/request.py` — Handles POST requests to the energy provider's API.
- `utils/updates.py` — Manages rate limits, caching, background polling, and notifications.
- `callback/`, `command/`, `states/`, `keyboards/` — Standard aiogram handlers and UI components.
- `docker-compose.yml` — Defines the bot and database services.
- `Dockerfile` — Defines the Python environment for the bot.
