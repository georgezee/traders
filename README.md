# Traders App

## Local environment setup

### Requirements
- Python (tested with 3.13.3)
- pip
- Docker and docker-compose

### Setup steps
1. Clone the repository
2. Copy the .env.example file to .env and populate.
3. Run `docker-compose build`
4. Run `docker-compose up` to start the containers
5. Access the application at `http://localhost:8000`

### Background workers (Celery + Redis)
- Redis and a Celery worker container are defined in `docker-compose.yml`. Ensure your `.env` file contains `CELERY_BROKER_URL=redis://redis:6379/0` and `CELERY_RESULT_BACKEND=redis://redis:6379/1` (matching `.env.example`).
- Start every service locally with `docker-compose up web celery redis db` (or simply `docker-compose up` to run all services). The worker shares the same code volume, so hot reloads apply automatically.
- If you need to verify the worker manually you can exec into the `traders-celery` container and run `celery -A config inspect ping`.
- For Dokku: install the Redis plugin (`dokku plugin:install https://github.com/dokku/dokku-redis.git`), create and link an instance (`dokku redis:create traders-redis` then `dokku redis:link traders-redis traders-app-name`). Dokku will expose `REDIS_URL`; set both `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` to that value (`dokku config:set traders-app-name CELERY_BROKER_URL=$REDIS_URL CELERY_RESULT_BACKEND=$REDIS_URL`).
- Scale up the new worker process on Dokku with `dokku ps:scale traders-app-name web=1 worker=1` so Celery tasks run outside the web dyno. The release phase in the `Procfile` remains unchanged.

### Debugging
1. Install the `debugpy` package ...
From the container

```bash
docker exec -it traders-web sh
pip install debugpy
```

2. Switch the lines for `debugpy` in `docker-compose.yml` (both for command and port).

3. Setup your local IDE to listen on port `5678`.
**Notes:**
- For debugging of pytest, instead of setting in docker-compose, run:
```python -m debugpy --listen 0.0.0.0:5678 --wait-for-client -m pytest```

### Frontend build steps

Tested with Node.js v22.

First time setup:
```bash
npm install
```

To build the CSS, or watch for changes:
```bash
npm run build:css
  or
npm run watch:css
```

To build the Svelte app, or watch for changes:
(from the /webapps folder)
```bash
npm run build
  or
npm run watch:build
```

Adding icons to the project
1. Go to fontello.com
2. Choose the spanner icon to import the list of existing icons (found in /static/font/fontello-config.json)
3. Select any new icons to download.
4. Download and extract the resulting file.
5. Copy the resulting font files into `/static/font/`.
6. Copy and rename config.json to `/static/font/fontello-config.json`.
6. Copy the resulting traders-icons.css into `/static/css`.
