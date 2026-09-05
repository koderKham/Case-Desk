# Heroku Deployment Guide for Case-Desk

## Prerequisites
- Heroku CLI installed
- PostgreSQL add-on provisioned (Heroku Postgres)
- Environment variables configured

## Environment Variables Required

Set these on Heroku:

```bash
heroku config:set CASE_MANAGER_SECRET_KEY="your-secure-random-key"
heroku config:set FLASK_ENV="production"
```

Heroku automatically sets `DATABASE_URL` when you add PostgreSQL.

## Deploy Steps

1. **Login to Heroku**
   ```bash
   heroku login
   ```

2. **Create Heroku app** (if new)
   ```bash
   heroku create case-desk
   ```

3. **Add PostgreSQL**
   ```bash
   heroku addons:create heroku-postgresql:hobby-dev
   ```

4. **Set environment variables**
   ```bash
   heroku config:set CASE_MANAGER_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
   heroku config:set FLASK_ENV="production"
   ```

5. **Deploy**
   ```bash
   git push heroku main
   ```

6. **Check logs**
   ```bash
   heroku logs --tail
   ```

7. **View app**
   ```bash
   heroku open
   ```

## Local Development

To use SQLite locally:
```bash
python app.py init-db
python app.py seed-db
python app.py run
```

No `DATABASE_URL` env var needed — it defaults to SQLite.

## Database Initialization

The Heroku `release` phase in `Procfile` automatically runs `init-db` before the app starts, so schema and seed data are created on first deploy.

## File Uploads

⚠️ **Important**: Files uploaded to the `uploads/` directory will be **deleted when the dyno restarts** (Heroku's ephemeral filesystem). For production, migrate uploads to:
- AWS S3
- Cloudinary
- Azure Blob Storage

Or disable the upload feature for now.

## Troubleshooting

### Database Connection Error
- Ensure `DATABASE_URL` is set: `heroku config | grep DATABASE_URL`
- Restart: `heroku restart`

### "relation does not exist" errors
- Database may not be initialized: `heroku run python app.py init-db`

### Port binding error
- The `Procfile` automatically binds to `$PORT` — no manual configuration needed.
