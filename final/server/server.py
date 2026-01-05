import os
import time
from fastmcp import FastMCP
import httpx
mcp = FastMCP("spotify-mcp")

CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
REFRESH_TOKEN = os.environ.get("REFRESH_TOKEN")
API_URL = "https://api.spotify.com/v1"

LASTFM_API_KEY = os.environ.get("LASTFM_API_KEY")
LASTFM_API_URL = "http://ws.audioscrobbler.com/2.0/"

access_token = None
expires_at = 0

# ------------------------------------
# ACCESS TOKEN (REFRESH TOKEN + CLIENT CREDENTIALS)
# ------------------------------------
async def get_access_token():
    """Return a valid Spotify access token, refreshing it if expired."""
    global access_token, expires_at

    # Return cached token if still valid
    if access_token and time.time() < expires_at:
        return access_token

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://accounts.spotify.com/api/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": REFRESH_TOKEN,
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
            },
        )

    resp.raise_for_status()
    data = resp.json()
    
    access_token = data["access_token"]
    expires_at = time.time() + data["expires_in"]
    
    return access_token

# ------------------------------------
# LASTFM GET REQUEST WRAPPER
# ------------------------------------
async def lastfm_get(method, params):
    q = {
        "method": method,
        "api_key": LASTFM_API_KEY,
        "format": "json",
        "autocorrect": "1",
    }
    q.update(params)

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            LASTFM_API_URL,
            params=q,
        )

    resp.raise_for_status()
    return resp.json()

# ------------------------------------
# Spotify GET REQUEST WRAPPER
# ------------------------------------
async def spotify_get(path, params=None):
    """Send a GET request to the Spotify Web API using a valid access token."""
    token = await get_access_token()

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{API_URL}{path}",
            params=params,
            headers={"Authorization": f"Bearer {token}"},
        )

    resp.raise_for_status()
    return resp.json()

# ------------------------------------
# Spotify POST REQUEST WRAPPER
# ------------------------------------
async def spotify_post(path, params=None):
    """Send a POST request to the Spotify Web API using a valid access token."""
    token = await get_access_token()

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{API_URL}{path}",
            json=params,
            headers={"Authorization": f"Bearer {token}"},
        )

    resp.raise_for_status()
    return resp.json()

# ------------------------------------
# Spotify PUT REQUEST WRAPPER
# ------------------------------------
async def spotify_put(path, params=None):
    """Send a PUT request to the Spotify Web API using a valid access token."""
    token = await get_access_token()

    async with httpx.AsyncClient() as client:
        resp = await client.put(
            f"{API_URL}{path}",
            json=params,
            headers={"Authorization": f"Bearer {token}"},
        )

    # start/resume playback returns 204 No Content on success
    if resp.status_code == 204 or resp.status_code == 200 or not resp.content:
        return {"status": "ok"}

    resp.raise_for_status()
    return resp.json()

# ------------------------------------
# MCP TOOLS
# ------------------------------------
@mcp.tool()
async def search_spotify(query: str, search_type: str = "track", limit: int = 5):
    """
    Search for Tracks, artists, albums, playlists, shows, episodes, audiobooks on Spotify.

    Parameters:
        query (str): The search term.
        search_type (str): The type of item to search for. 
                           Valid values are: "track", "artist", "album", "playlist", "show", "episode", "audiobook". 
                           Defaults to "track".
        limit (int): Maximum number of results to return (IF correct search term isnt found, expand limit)).

    Returns:
        list: A list of the search results.
        Key fields for items include 'name', 'uri' (needed for queuing), 'id', and 'artists'.
    """
    raw = await spotify_get("/search", {"q": query, "type": search_type, "limit": limit})

    container = f"{search_type}s"
    try:
        items = raw[container]["items"]
    except Exception:
        items = []


    cleaned = []
    # Clean up the items
    for item in items:
        cleaned.append({
            "id": item.get("id"),
            "name": item.get("name"),
            "uri": item.get("uri"),
            # Optional fields depending on item type:
            "artists": [a.get("name") for a in item.get("artists", [])] if item.get("artists") else None,
            "album": item.get("album", {}).get("name") if item.get("album") else None,
        })

    return {"type": search_type,"items": cleaned}

@mcp.tool()
async def artist_top_tracks(artist_id: str, market: str = "US"):
    """
    Retrieve an artist's top tracks. You must first know the artist's ID to use this tool.

    Parameters:
        artist_id (str): The Spotify Artist ID (e.g., '4Z8W4fKeB5YxbusRsdQVPb').
        market (str): Market territory code (default: 'US'). 

    Returns:
        dict: A JSON object containing the artist's top tracks.
        Key fields for items include 'name', 'uri' (needed for queuing), 'id', and 'artists'.
    """
    raw = await spotify_get(f"/artists/{artist_id}/top-tracks", {"market": market})

    cleaned = []
    # Cleaning returned tracks
    for t in raw.get("tracks", []):
        cleaned.append({
            "id": t.get("id"),
            "name": t.get("name"),
            "uri": t.get("uri"),
            "artists": [a.get("name") for a in t.get("artists", [])],
            "album": t.get("album", {}).get("name"),
            "popularity": t.get("popularity"),
        })

    return {"tracks": cleaned}

@mcp.tool()
async def current_user_profile():
    """
    Get the current user's profile information such as user_id as id.

    Returns:
        dict: A JSON object containing the current user's profile. 
              Key fields for items include 'name', 'uri' (needed for queuing), 'user_id' as id, and 'artists'.
    """
    return await spotify_get(f"/me")

@mcp.tool()
async def current_user_top_tracks(time_range: str = "short_term", limit: int = 10):
    """
    Get the current user's top tracks. If Time range is specificed, use closest time range.
    for example: 2 months will return short_term and notify user.

    Parameters:
        time_range (str): Time window for top tracks. One of:
                         "short_term" (last 4 weeks),
                          "medium_term" (last 6 months),
                          "long_term" (several years).
                          Defaults to "short_term".
        limit (int): Number of tracks to return (1–50). Defaults to 10.

    Returns:
        list: A list of the user's top tracks.
        Key fields for items include 'rank', 'id', 'name', 'uri', 'artists', and 'album'.
    """
    raw = await spotify_get("/me/top/tracks",{"time_range": time_range,"limit": limit,},)

    items = raw.get("items", []) or []

    cleaned_top_tracks = []
    for idx, t in enumerate(items, start=1):
        cleaned_top_tracks.append({
            "rank": idx,
            "id": t.get("id"),
            "name": t.get("name"),
            "uri": t.get("uri"),
            "artists": [a.get("name") for a in t.get("artists", [])],
            "album": t.get("album", {}).get("name"),
        })

    return cleaned_top_tracks

@mcp.tool()
async def get_current_user_playlists(limit: int = 10, offset: int = 0):
    """
    Get a list of my playlists (limit size at a time).
    Increase limit and offset to paginate and find more playlists.
    When searching for all playlists expand limit until all playlists are found.

    Parameters:
        limit (int): Maximum number of results to return (IF correct search term isnt found, expand limit)).
        offset (int): 'The index of the first playlist to return. Default: 0 (the first object). Maximum offset: 100.000. Use with limit to get the next set of playlists.'

    Returns:
        list: A list of the playlists owned by the current Spotify user.
    """
    raw = await spotify_get("/me/playlists", {"limit": limit, "offset": offset})

    items = raw["items"]
    total = raw["total"]
    # iterate through the playlists and create a list of dictionaries
    playlists = [
        {
            "id": p["id"],
            "name": p["name"],
            "uri": p["uri"],
            "description": p["description"],
            "owner": p["owner"]["display_name"],
            "tracks_total": p["tracks"]["total"],
        }
        for p in items
    ]

    return {"total_playlists": total,"returned": len(playlists),"limit": limit,"offset": offset,"playlists": playlists,}

@mcp.tool()
async def get_playlist_items(playlist_id: str, limit: int = 10, offset: int = 0):
    """
    Get full details of the items/tracks of a playlist with the playlist id.
    for 'my' playlists use get_current_user_playlists first to find playlist id.
    Adjust limit and offset to paginate through playlist items.

    Parameters:
        playlist_id (str): The id of the playlist.
        limit (int): Maximum number of results to return (IF correct search term isnt found, expand limit)).
        offset (int): The index of the first item to return. Default: 0 (the first item). Use with limit to get the next set of items.

    Returns:
        list: A list of the playlist items for the specified playlist.
    """

    raw = await spotify_get(f"/playlists/{playlist_id}/tracks", {"limit": limit, "offset": offset})

    items = raw["items"]  # list of playlist entries
    total = raw["total"]  # total tracks in the playlist

    cleaned = []
    # iterate through the playlist entries
    for entry in items:
        track = entry["track"]

        cleaned.append({
            "id": track["id"],
            "name": track["name"],
            "uri": track["uri"],
            "artists": [a["name"] for a in track["artists"]],
            "album": track["album"]["name"],
            "explicit": track["explicit"],
        })

    return {"total_tracks": total,"returned": len(cleaned),"limit": limit,"offset": offset,"items": cleaned,}

@mcp.tool()
async def create_playlist(user_id: str, name: str, description: str = "", public: bool = True):
    """
    Create a new playlist for the current Spotify user. user_id is the current user's id.

    Parameters:
        name (str): The name of the playlist.
        description (str): A description of the playlist.
        public (bool): Whether the playlist is public or not. (default to True)

    Returns:
        dict: A JSON object containing the playlists owned or followed by the current Spotify user. 
              Key fields for items include 'name', 'uri' (needed for queuing), 'id', and 'artists'.
    """
    return await spotify_post(f"/users/{user_id}/playlists", {"name": name, "description": description, "public": public})

@mcp.tool()
async def add_to_playlist(playlist_id: str, track_uri: str):
    """
    Add tracks to a playlist. Try to batch as many tracks as possible into one request.

    Parameters:
        playlist_id (str): The id of the playlist.
        track_uri (str): A comma-separated list of Spotify URIs to add, can be track or episode URIs.

    Returns:
        dict: A JSON object containing the playlists owned or followed by the current Spotify user. 
              Key fields for items include 'name', 'uri' (needed for queuing), 'id', and 'artists'.
    """
    uri_list = [uri.strip() for uri in track_uri.split(',')]
    return await spotify_post(f"/playlists/{playlist_id}/tracks", {"uris": uri_list})

@mcp.tool()
async def get_similar_tracks(artist_name: str, track_name: str, limit: int = 5):
    """
    Get similar tracks to the specified song from Last.fm.

    Parameters:
        artist_name (str): The name of the artist.
        track_name (str): The name of the song.
        limit (int): Maximum number of similar tracks to return (expand limit if you want more similar tracks).

    Returns:
        list: A list of similar tracks with their artist names.
    """
    raw = await lastfm_get("track.getSimilar", {"artist": artist_name, "track": track_name, "limit": limit})
    tracks = raw["similartracks"]["track"]
    results = [{"track": t["name"],"artist": t["artist"]["name"]} for t in tracks]

    return {"similar_tracks": results}

@mcp.tool()
async def get_similar_artists(artist_name: str, limit: int = 5):
    """
    Get similar artists to the specified artist name from Last.fm.

    Parameters:
        artist_name (str): The name of the artist.
        limit (int): Maximum number of similar artists to return (expand limit if you want more similar artists).

    Returns:
        list: A list of similar artist names.
    """
    raw = await lastfm_get("artist.getSimilar", {"artist": artist_name, "limit": limit})

    artists = raw["similarartists"]["artist"]
    names = [a["name"] for a in artists]

    return {"similar_artists": names}

@mcp.tool()
async def start_playback(context_uri: str = None, track_uris: str = None, position_ms: int = None):
    """
    Start or resume playback on the user's active device.

    Parameters:
        context_uri (str, optional): Spotify context URI (e.g. album or playlist URI).
        track_uris (str, optional): Comma-separated list of track URIs to play.
        position_ms (int, optional): Milliseconds to start playback from.

    Notes:
        - If both context_uri and track_uris are omitted, playback will resume the current context.
    """
    # Turn "uri1,uri2,uri3" into ["uri1","uri2","uri3"]
    uris = [u.strip() for u in track_uris.split(",")] if track_uris else None

    return await spotify_put("/me/player/play",{"context_uri": context_uri,"uris": uris,"position_ms": position_ms})

@mcp.tool()
async def pause_playback():
    """
    Pause/Stop playback on the user's active device.
    """
    return await spotify_put("/me/player/pause")

# ------------------------------------

if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8080)