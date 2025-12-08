# Rewrapped

- Dockerized FastAPI service that assembles a Spotify Wrapped-style report using the Spotify Web API.
- Simple card UI at `/card/rewrapped` showing number of plays, number of unique tracks, top artists, top tracks, top albums and so on. This is available on a month and year level.
- Even simpler card UI art `/card/extended` showing top artists and top tracks over a short, medium and long time bucket as defined by spotify. Also includes basic theme color switching because why not?

## Setup (Client ID, Secret, Refresh Token)

1) Create a Spotify app in the [Dashboard](https://developer.spotify.com/dashboard). Add a redirect URI (e.g., `http://localhost:8080/callback`). Note the Client ID and Client Secret.
2) Build the authorize URL and open it in your browser (replace `CLIENT_ID` and `REDIRECT_URI`; required scopes: `user-top-read user-read-recently-played user-read-private`):
   ```
   https://accounts.spotify.com/authorize?client_id=CLIENT_ID
     &response_type=code
     &redirect_uri=REDIRECT_URI
     &scope=user-top-read%20user-read-recently-played%20user-read-private
   ```
   After you accept, Spotify redirects to `REDIRECT_URI?code=...`. Copy the `code`.
3) In a shell (WSL/Linux/macOS), generate the Basic header and exchange the code for tokens:
   ```bash
   CLIENT_ID="your_client_id"
   CLIENT_SECRET="your_client_secret"
   CODE="the_code_from_redirect"
   REDIRECT_URI="http://localhost:8080/callback"  # must match what you used above

   BASIC=$(printf "%s:%s" "$CLIENT_ID" "$CLIENT_SECRET" | base64)

   curl --http1.1 -v -X POST "https://accounts.spotify.com/api/token" \
     -H "Authorization: Basic $BASIC" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     --data-urlencode "grant_type=authorization_code" \
     --data-urlencode "code=$CODE" \
     --data-urlencode "redirect_uri=$REDIRECT_URI"
   ```
   The response JSON includes `refresh_token`. Keep it safe.

From here you can either run locally or deploy on Render.

### MongoDB (for stored plays)

- Provision a MongoDB database (Atlas or self-hosted).
- Add these env vars alongside the Spotify vars:
  - `MONGODB_URI` (SRV or standard connection string)
  - `MONGODB_DB` (default: `rewrapped`)
  - `MONGODB_COLLECTION` (default: `plays`)
- Plays are keyed by `played_at` and upserted, so the collection will not contain overlapping/duplicate items.

## Run locally

1) Populate `.env` (see `.env.example`) and either

    i) Start the API in Terminal:
      ```bash
      python -m venv .venv && source .venv/bin/activate  # or .venv\Scripts\activate on Windows
      pip install -r requirements.txt
      uvicorn app.main:app --reload
      ```
    ii) Use Docker:
      ```bash
      docker build -t rewrapped .
      docker run --env-file .env -p 8000:8000 rewrapped
      ```

## Deploy on Render

1) Clone this repo or push a local version of it to GitHub (do not commit your `.env`; keep it local).
2) In Render, create a new Web Service from the repo, choose Docker as the runtime.
3) Set environment variables in the Render dashboard: `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, `SPOTIFY_REFRESH_TOKEN` (optionally `SPOTIFY_API_BASE`, `SPOTIFY_AUTH_BASE`, `REQUEST_TIMEOUT`).
4) Deploy. Use the public URL Render gives you (e.g., `https://your-app.onrender.com/card/rewrapped`, `/card/extended`).


## Data Ingestion
### Scheduled ingestion (GitHub Actions)

This implements continuous syncing. A workflow at `.github/workflows/ingest.yml` runs every 15 minutes (and can be triggered manually) to pull the most recent Spotify plays and store them in MongoDB without overlaps:

- Add repository secrets: `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, `SPOTIFY_REFRESH_TOKEN`, `MONGODB_URI`, and optionally `MONGODB_DB`, `MONGODB_COLLECTION`.
- The workflow executes `python -m app.ingest_recent`, which upserts plays by `played_at` and keeps indexes fresh.

### Data Dump
Optionally request your entire spotify listening history from Spotify via their [privacy page](https://www.spotify.com/us/account/privacy/). This can take a while. Once you have it:
- Run the command below. This may take a while; take a break.
  ```bash
  python -m app.ingest_dump "{path_to_dir}/Streaming_History_Audio*.json"
  ```
- Unfortunately, the Spotify dump does not include album cover images. To fix that, run the command below a number of times until you get an update saying "No tracks missing images." Be careful with the `batch_size` (default 500) as you do not want to exceed Spotify's rate limit.
  ```bash
  python -m app.backfill_images batch_size
  ```

> Note: Longer-term/power users should probably run the `backfill_images` command in a loop with some wait time between batches. I chose not to do that.

## API

- `GET /wrapped/short?top_limit=50&recent_limit=50`  
  Short-term (~4 weeks) top tracks/artists plus the small recent playback window Spotify exposes (about the last 50 plays).
- `GET /wrapped/medium?top_limit=50`  
  Medium-term (~6 months) top tracks and artists.
- `GET /wrapped/long?top_limit=50`  
  Long-term (multi-year) top tracks and artists.
- `GET /wrapped/yearly?year=2024&limit=20`  
  Wrapped view backed by stored plays in MongoDB for a full calendar year. Defaults to the previous calendar year if omitted.
- `GET /wrapped/monthly?month=11&year=2024&limit=20`  
  Wrapped view backed by stored plays in MongoDB for a specific month/year. Defaults to the previous calendar month if omitted. Returns play counts, minutes, and top tracks/artists/albums (albums are included when available).

### Basic UI
- `GET /card`  
  Simple HTML card that visualizes top tracks and artists side by side. Uses `/wrapped/{short|medium|long}` under the hood; adjust range and limit via the UI controls.
- `GET /card/extended`  
  Themed version of the card with selectable styles plus range and limit controls.
- `GET /card/rewrapped`  
  Card powered by stored MongoDB plays. Toggle month vs year view, choose period and limit; shows top tracks, artists, and albums with play counts and minutes listened.

## Low Hanging Fruits 🍎
- Multi-year stats endpoint and dashboard.
- A more interesting dashboard using the API