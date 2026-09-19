# Tinker: Playlist Chaos — Prasidh Shetty

AI110 | Module 1 | Week 1

## Bug 1 — Search (Part 1)

**What I saw:** Searching `AC` in the artist field returned nothing, even though "AC/DC" was in the Hype playlist. Searching the full `AC/DC` worked.

**Where I looked:** `search_songs()` in `playlist_logic.py`.

**What was wrong:** The match condition was written as a chained comparison:

```python
if value in q in value:
```

Python reads `a in b in c` as `(a in b) and (b in c)`, so this was really:

```python
if (value in q) and (q in value):
```

The first half asks whether the whole artist name fits inside the short search text, which is backwards. Both halves can only be true when the two strings are identical, so the search behaved like an exact-match check instead of a partial one. That also explains why `AC/DC` matched and `AC` didn't.

**Fix:**

```python
if q in value:
```

**Verified:** Searching `AC` now returns "Thunderstruck by AC/DC".

## Bug 2 — Stats

**What I saw:** Hype Ratio stayed at 1.00 no matter how many Chill songs existed, and Average Energy read lower than it should.

**Where I looked:** `compute_playlist_stats()` in `playlist_logic.py`.

**What was wrong:** The function used the Hype list in two places where the spec calls for all songs.

```python
total = len(hype)                                                  # ratio divides by itself
total_energy = sum(song.get("energy", 0) for song in hype)         # only Hype energy counted
avg_energy = total_energy / len(all_songs)                         # but divided by every song
```

Dividing the Hype count by itself always gives 1.00. The average summed only Hype songs while dividing by the full count, so every Chill and Mixed song was effectively counted as energy 0.

**Fix:** Both now use `all_songs`.

```python
total = len(all_songs)
total_energy = sum(song.get("energy", 0) for song in all_songs)
```

**Verified:** With 2 Hype songs (energy 8, 10) and 2 Chill songs (energy 2, 2), the average now reads 5.5 instead of 4.5, and the ratio drops below 1.00 as Chill songs are added.

## Bug 3 — Lucky Pick

**What I saw:** Setting Lucky Pick to a playlist with no songs and clicking **Feeling lucky** crashed the app with `IndexError: Cannot choose from an empty sequence`.

**Where I looked:** the traceback pointed to `random_choice_or_none()` in `playlist_logic.py`.

**What was wrong:** The function called `random.choice()` unconditionally, and `random.choice` raises on an empty list rather than returning nothing. The function's own name promised a `None` fallback it never delivered, and `app.py` was already written to handle `None`:

```python
if pick is None:
    st.warning("No songs available for this mode.")
```

The warning could never fire because the crash happened first.

**Fix:**

```python
if not songs:
    return None
return random.choice(songs)
```

**Verified:** An empty playlist now shows "No songs available for this mode." Adding one song to that playlist makes the button pick it.

## Design change — Classification (deviates from the spec)

The spec defines Hype as `energy >= hype_min_energy` **OR** `genre == favorite_genre` **OR** a hype keyword in the genre. I changed this so genre and energy must **agree** before a song lands in Hype or Chill:

- Genre groups: rock / pop / electronic are Hype genres; ambient / jazz / lofi are Chill genres; "other" always goes to Mixed.
- A song joins Hype or Chill only when its genre group and its energy band match.
- When the two disagree (for example pop at energy 2), adding the song is rejected with an explanatory message.
- Overlapping thresholds (Hype min ≤ Chill max) are rejected in the sidebar, and the last valid values stay in use.
- Favorite genre is now a stored preference only; it no longer affects placement.

**This is a deliberate design change, not a bug fix.** My reasoning is that the profile's favorite genre is a statement of taste, not a property of the song being added, so it shouldn't override the energy rules. I'd welcome feedback on whether that's the right call for this assignment.

## Refactor

I rewrote `lucky_pick()`. The original repeated `playlists.get(...)` across three branches:

```python
if mode == "hype":
    songs = playlists.get("Hype", [])
elif mode == "chill":
    songs = playlists.get("Chill", [])
else:
    songs = playlists.get("Hype", []) + playlists.get("Chill", [])
```

The new version separates *which* playlists to read from *gathering* the songs:

```python
sources = {"hype": ["Hype"], "chill": ["Chill"]}.get(mode, ["Hype", "Chill"])

songs: List[Song] = []
for name in sources:
    songs.extend(playlists.get(name, []))
```

**How I confirmed it was safe:** I ran the old and new versions side by side, 300 picks each, across a populated playlist map, an empty one, and one with missing keys, in all four modes (`hype`, `chill`, `any`, and an unrecognized value). The sets of possible results were identical every time. Behavior including the `None` fallback is unchanged, and `any` still excludes Mixed exactly as before.

## Reflection — working with the AI assistant

**Did it understand the context?** Only once I gave it specific evidence. Vague questions produced vague guesses. Pasting the actual function, what I searched, what I expected, and what the app did produced an explanation I could check.

**Was it ever confidently wrong?** Twice.

1. When an ambient, energy-2 song landed in Hype, the assistant was ready to call `classify_song()` broken. Reading the code line by line showed the function was correct for the default profile. The real cause was the sidebar's "Favorite genre" being set to `ambient`, which short-circuited the Hype check. Editing the function would have broken working logic.
2. A suggested fix for a type-checker warning addressed only half the cause. Running a type checker revealed the remaining errors came from a different line entirely.

**When did I decide not to trust it?** Whenever a suggestion arrived without a way to check it. My rule by the end: reproduce the behavior in the running app first, then read the code, and only then accept a fix — and re-test in the app afterward.

**Group insight:** verify before you fix. A behavior that looks like a bug can be a settings or state issue, and AI will happily write a confident patch for a problem that doesn't exist.

**A practical gotcha worth sharing:** after editing `playlist_logic.py`, Streamlit sometimes keeps running the old version. The traceback pointed at a line that couldn't possibly crash, which was the giveaway. Restarting Streamlit fixed it. Without noticing that, I'd have spent the time debugging code that was already correct.
