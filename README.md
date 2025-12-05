# Rewrapped API

Dockerized FastAPI service that assembles a Spotify Wrapped-style report using the Spotify Web API.

## Setup (Client ID, Secret, Refresh Token)

1) Create a Spotify app in the Dashboard. Add a redirect URI (e.g., `http://localhost:8080/callback`). Note the Client ID and Client Secret.
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
4) Populate `.env` (see `.env.example`):
   ```
   SPOTIFY_CLIENT_ID=...
   SPOTIFY_CLIENT_SECRET=...
   SPOTIFY_REFRESH_TOKEN=...
   ```
5) Run locally:
   ```bash
   python -m venv .venv && source .venv/bin/activate  # or .venv\Scripts\activate on Windows
   pip install -r requirements.txt
   uvicorn app.main:app --reload
   ```

## Docker

```bash
docker build -t rewrapped .
docker run --env-file .env -p 8000:8000 rewrapped
```

## API

- `GET /wrapped/short?top_limit=50&recent_limit=50`  
  Short-term (~4 weeks) top tracks/artists plus the small recent playback window Spotify exposes (about the last 50 plays).
- `GET /wrapped/medium?top_limit=50`  
  Medium-term (~6 months) top tracks and artists.
- `GET /wrapped/long?top_limit=50`  
  Long-term (multi-year) top tracks and artists.
- `GET /card`  
  Simple HTML card that visualizes top tracks and artists side by side. Uses `/wrapped/{short|medium|long}` under the hood; adjust range and limit via the UI controls.
- `GET /card/extended`  
  Themed version of the card with selectable styles plus range and limit controls.

> Note: Spotify only provides recent playback history (~50 items per request, paged via `before/after`) so exact play stats are ignored for now.
