import json
import os
import time

LEADERBOARD_FILE = "leaderboard.json"

class Leaderboard:
    """
    Persists win counts between server restarts.
    Stored as a simple JSON file — no database needed.
    """
    def __init__(self):
        self.data = self._load()

    def _load(self) -> dict:
        if os.path.exists(LEADERBOARD_FILE):
            try:
                with open(LEADERBOARD_FILE, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save(self):
        with open(LEADERBOARD_FILE, "w") as f:
            json.dump(self.data, f, indent=2)

    def record_win(self, username: str):
        key = username.lower()
        if key not in self.data:
            self.data[key] = {"username": username, "wins": 0, "last_win": 0}
        self.data[key]["wins"]     += 1
        self.data[key]["last_win"]  = int(time.time() * 1000)
        self._save()

    def get_top(self, n: int = 10) -> list:
        sorted_entries = sorted(
            self.data.values(),
            key=lambda x: x["wins"],
            reverse=True
        )
        return sorted_entries[:n]

    def get_wins(self, username: str) -> int:
        return self.data.get(username.lower(), {}).get("wins", 0)
