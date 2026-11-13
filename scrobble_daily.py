import os
import time

import pylast
import ytmusicapi


API_KEY = os.getenv("LASTFM_API_KEY")
API_SECRET = os.getenv("LASTFM_API_SECRET")
username = os.getenv("LASTFM_USERNAME")
password_hash = pylast.md5(os.getenv("LASTFM_PASSWORD"))


def to_scrobble(entry: dict) -> dict:
    artists = ", ".join(a["name"] for a in entry.get("artists") if a.get("id") or [])
    primary_artist = entry["artists"][0]["name"] if entry.get("artists") else artists
    album = (entry.get("album") or {}).get("name", "")
    duration_seconds = entry.get("duration_seconds", 180)
    return {
        "artist": artists,
        "title": entry["title"],
        "timestamp": int(time.time()),
        "album": album,
        "duration": duration_seconds,
        "album_artist": primary_artist,
    }


def scrobble_tracks(network: pylast.LastFMNetwork, tracks: list):
    try:
        network.scrobble_many(tracks)
    except pylast.WSError as e:
        print(f"Error scrobbling tracks: {e}")
        raise
    print(f"Scrobbled {len(tracks)} tracks to Last.fm")


def write_secret_file(secret_name: str, path: str):
    raw_value = os.getenv(secret_name)
    if not raw_value:
        return False

    with open(path, "w", encoding="utf-8") as f:
        f.write(raw_value)
    return True


def get_ytmusic():
    browser_json_path = "browser.json"
    oauth_credentials_path = "oauth_credentials.json"

    browser_written = write_secret_file("BROWSER_JSON", browser_json_path)
    oauth_written = write_secret_file("YTMUSIC_OAUTH_CREDENTIALS", oauth_credentials_path)
    oauth_written = oauth_written or write_secret_file("OAUTH_CREDENTIALS", oauth_credentials_path)

    if oauth_written and os.path.exists(oauth_credentials_path):
        return ytmusicapi.YTMusic(auth=browser_json_path, oauth_credentials=oauth_credentials_path)

    if browser_written and os.path.exists(browser_json_path):
        return ytmusicapi.YTMusic(auth=browser_json_path)

    raise RuntimeError(
        "Missing YT Music authentication. Add BROWSER_JSON and YTMUSIC_OAUTH_CREDENTIALS "
        "(or OAUTH_CREDENTIALS) secrets to the GitHub Actions environment."
    )


def main():
    ytmusic = get_ytmusic()

    lastfm = pylast.LastFMNetwork(
        api_key=API_KEY,
        api_secret=API_SECRET,
        username=username,
        password_hash=password_hash,
    )

    history = ytmusic.get_history()
    history = [entry for entry in history if entry.get("played") == "Yesterday"]

    scrobbles = [to_scrobble(entry) for entry in history]

    print(f"{len(scrobbles)} tracks to scrobble")
    scrobble_tracks(lastfm, scrobbles)


if __name__ == "__main__":
    main()
