# Spotify MCP Server

This repo contains a FastMCP-based server that exposes a set of Spotify + Last.fm tools to an MCP client.  
The **server** folder is a Dockerized MCP server that talks to the Spotify Web API and Last.fm.  
The **client** folder holds a simple Python MCP client you can run locally to test the tools.

```text
final/
  client/
    client.py
    requirements.txt
  server/
    server.py    # FastMCP Spotify/Last.fm tools
    requirements.txt
    Dockerfile
  screencast_url.txt
```
The server exposes the following MCP tools:
---
- **search_spotify**
- **artist_top_tracks**
- **current_user_profile**
- **current_user_top_tracks**
- **get_current_user_playlists**
- **get_playlist_items**
- **create_playlist**
- **add_to_playlist**
- **get_similar_tracks** (Last.fm)
- **get_similar_artists** (Last.fm)
- **start_playback**
- **pause_playback**

Environment Variables / API Keys
---
These environment variables *must be set during Cloud Run deployment*:

| Variable          | Description |
|------------------|-------------|
| `CLIENT_ID`       | Spotify Client ID |
| `CLIENT_SECRET`   | Spotify Client Secret |
| `REFRESH_TOKEN`   | Spotify Refresh Token |
| `LASTFM_API_KEY`  | Last.fm API Key |

- `Spotify Client ID & Client Secret are in the developer dashboard`
- `Refresh token can be obtained through cloning this repo:` https://github.com/limhenry/spotify-refresh-token-generator
- `LastFM API Account page contains Key`

Required Spotify OAuth Scopes (for Refresh Token)
---
To support **all tools** in the Spotify MCP server, your refresh token must include the following scopes:
#### User Profile & Top Tracks
- `user-read-private`
- `user-read-email`
- `user-top-read`
#### Playlists (Read)
- `playlist-read-private`
- `playlist-read-collaborative`
#### Playlists (Write / Create / Modify)
- `playlist-modify-public`
- `playlist-modify-private`
#### Playback Control
- `user-modify-playback-state`
- `user-read-playback-state`
- `user-read-currently-playing`

Deploying to Cloud Run
---
Enable the following APIs before deploying:
- `artifactregistry.googleapis.com` — Docker image storage  
- `cloudbuild.googleapis.com` — Build and push images  
- `run.googleapis.com` — Deploy to Cloud Run  
- `logging.googleapis.com` — Enable Cloud Run logs

Deployment uses Artifact Registry + Cloud Run in `us-west1`.  
Run the following **from the `final/server/` directory**.

1. Create an Artifact Registry Docker repository
```bash
gcloud artifacts repositories create mcp-testing \
  --repository-format=docker \
  --location=us-west1
  ```
2. Build and Push docker image
  ```bash
gcloud builds submit --tag \
us-west1-docker.pkg.dev/${GOOGLE_CLOUD_PROJECT}/mcp-testing/mcp-tag
```
3. Deploy MCP server to Cloud Run
```bash
gcloud run deploy gcp-mcp \
  --image us-west1-docker.pkg.dev/${GOOGLE_CLOUD_PROJECT}/mcp-testing/mcp-tag \
  --region us-west1 \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars CLIENT_ID=$CLIENT_ID \
  --set-env-vars CLIENT_SECRET=$CLIENT_SECRET \
  --set-env-vars REFRESH_TOKEN=$REFRESH_TOKEN \
  --set-env-vars LASTFM_API_KEY=$LASTFM_API_KEY
```
Cloud Run will output a URL — this is your MCP server endpoint.

Running Client
---
1. Set `GOOGLE_API_KEY` and `MCP_URL` env variables
2. In **`/final/client`** directory run:
```bash
virtualenv -p python3 .venv
source .venv/bin/activate
pip install uv
uv init
uv add -r requirements.txt
uv run client.py
```
