from typing import Any, Dict, List, Optional, Tuple

Song = Dict[str, Any]
PlaylistMap = Dict[str, List[Song]]

DEFAULT_PROFILE = {
    "name": "Default",
    "hype_min_energy": 7,
    "chill_max_energy": 3,
    "favorite_genre": "rock",
    "include_mixed": True,
}


def normalize_title(title: str) -> str:
    """Normalize a song title for comparisons."""
    if not isinstance(title, str):
        return ""
    return title.strip()


def normalize_artist(artist: str) -> str:
    """Normalize an artist name for comparisons."""
    if not artist:
        return ""
    return artist.strip().lower()


def normalize_genre(genre: str) -> str:
    """Normalize a genre name for comparisons."""
    return genre.lower().strip()


def normalize_song(raw: Song) -> Song:
    """Return a normalized song dict with expected keys."""
    title = normalize_title(str(raw.get("title", "")))
    artist = normalize_artist(str(raw.get("artist", "")))
    genre = normalize_genre(str(raw.get("genre", "")))
    energy = raw.get("energy", 0)

    if isinstance(energy, str):
        try:
            energy = int(energy)
        except ValueError:
            energy = 0

    tags = raw.get("tags", [])
    if isinstance(tags, str):
        tags = [tags]

    return {
        "title": title,
        "artist": artist,
        "genre": genre,
        "energy": energy,
        "tags": tags,
    }


# Which playlist each genre belongs to. "other" has no mood, so it goes to Mixed.
GENRE_GROUPS = {
    "rock": "Hype",
    "pop": "Hype",
    "electronic": "Hype",
    "ambient": "Chill",
    "jazz": "Chill",
    "lofi": "Chill",
    "other": "Mixed",
}


def energy_band(energy: int, profile: Dict[str, Any]) -> str:
    """Return Hype / Chill / Mixed based on energy and the profile thresholds."""
    hype_min_energy = int(profile.get("hype_min_energy", 7))
    chill_max_energy = int(profile.get("chill_max_energy", 3))
    if energy >= hype_min_energy:
        return "Hype"
    if energy <= chill_max_energy:
        return "Chill"
    return "Mixed"


def validate_thresholds(hype_min_energy: int, chill_max_energy: int) -> Optional[str]:
    """Return an error message if the thresholds overlap, else None."""
    if hype_min_energy <= chill_max_energy:
        return (
            f"Hype min energy ({hype_min_energy}) must be higher than "
            f"Chill max energy ({chill_max_energy})."
        )
    return None


def check_song_conflict(song: Song, profile: Dict[str, object]) -> Optional[str]:
    """Return an error message if genre and energy point to opposite playlists."""
    genre_group = GENRE_GROUPS.get(str(song.get("genre", "")), "Mixed")
    band = energy_band(int(song.get("energy", 0)), profile)
    if {genre_group, band} == {"Hype", "Chill"}:
        return (
            f"'{song.get('genre')}' is a {genre_group} genre, but energy "
            f"{song.get('energy')} is in the {band} range. Change the genre or energy."
        )
    return None


def classify_song(song: Song, profile: Dict[str, object]) -> str:
    """Return a mood label. Genre and energy must agree (AND logic).

    - Genre "other" -> Mixed.
    - Genre group and energy band agree -> that playlist.
    - One of them is Mixed (e.g. pop at energy 5) -> Mixed.
    - They conflict (e.g. pop at energy 2) -> Mixed. Adding such a song is
      blocked in the UI; this only happens when thresholds change later.
    Favorite genre is a preference only and does not affect placement.
    """
    genre_group = GENRE_GROUPS.get(str(song.get("genre", "")), "Mixed")
    band = energy_band(int(song.get("energy", 0)), profile)
    if genre_group == band:
        return genre_group
    return "Mixed"


def build_playlists(songs: List[Song], profile: Dict[str, object]) -> PlaylistMap:
    """Group songs into playlists based on mood and profile."""
    playlists: PlaylistMap = {
        "Hype": [],
        "Chill": [],
        "Mixed": [],
    }

    for song in songs:
        normalized = normalize_song(song)
        mood = classify_song(normalized, profile)
        normalized["mood"] = mood
        playlists[mood].append(normalized)

    return playlists


def merge_playlists(a: PlaylistMap, b: PlaylistMap) -> PlaylistMap:
    """Merge two playlist maps into a new map."""
    merged: PlaylistMap = {}
    for key in set(list(a.keys()) + list(b.keys())):
        merged[key] = a.get(key, [])
        merged[key].extend(b.get(key, []))
    return merged


def compute_playlist_stats(playlists: PlaylistMap) -> Dict[str, object]:
    """Compute statistics across all playlists."""
    all_songs: List[Song] = []
    for songs in playlists.values():
        all_songs.extend(songs)

    hype = playlists.get("Hype", [])
    chill = playlists.get("Chill", [])
    mixed = playlists.get("Mixed", [])

    total = len(all_songs)
    hype_ratio = len(hype) / total if total > 0 else 0.0

    avg_energy = 0.0
    if all_songs:
        total_energy = sum(song.get("energy", 0) for song in all_songs)
        avg_energy = total_energy / len(all_songs)

    top_artist, top_count = most_common_artist(all_songs)

    return {
        "total_songs": len(all_songs),
        "hype_count": len(hype),
        "chill_count": len(chill),
        "mixed_count": len(mixed),
        "hype_ratio": hype_ratio,
        "avg_energy": avg_energy,
        "top_artist": top_artist,
        "top_artist_count": top_count,
    }


def most_common_artist(songs: List[Song]) -> Tuple[str, int]:
    """Return the most common artist and count."""
    counts: Dict[str, int] = {}
    for song in songs:
        artist = str(song.get("artist", ""))
        if not artist:
            continue
        counts[artist] = counts.get(artist, 0) + 1

    if not counts:
        return "", 0

    items = sorted(counts.items(), key=lambda item: item[1], reverse=True)
    return items[0]


def search_songs(
    songs: List[Song],
    query: str,
    field: str = "artist",
) -> List[Song]:
    """Return songs matching the query on a given field."""
    if not query:
        return songs

    q = query.lower().strip()
    filtered: List[Song] = []

    for song in songs:
        value = str(song.get(field, "")).lower()
        if q in value:
            filtered.append(song)

    return filtered


def lucky_pick(
    playlists: PlaylistMap,
    mode: str = "any",
) -> Optional[Song]:
    """Pick a song from the playlists according to mode."""
    if mode == "hype":
        songs = playlists.get("Hype", [])
    elif mode == "chill":
        songs = playlists.get("Chill", [])
    else:
        songs = playlists.get("Hype", []) + playlists.get("Chill", [])

    return random_choice_or_none(songs)


def random_choice_or_none(songs: List[Song]) -> Optional[Song]:
    """Return a random song or None."""
    import random

    return random.choice(songs)


def history_summary(history: List[Song]) -> Dict[str, int]:
    """Return a summary of moods seen in the history."""
    counts = {"Hype": 0, "Chill": 0, "Mixed": 0}
    for song in history:
        mood = song.get("mood", "Mixed")
        if mood not in counts:
            counts["Mixed"] += 1
        else:
            counts[mood] += 1
    return counts
