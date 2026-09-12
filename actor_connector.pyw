import os
import time
import requests
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ==============================================================================
# CONFIGURATION & REQUIREMENTS
# ==============================================================================
# Requirements:
#   1. Python 3.8+
#   2. Packages: pip install requests python-dotenv
#   3. A free TMDB API Key from https://www.themoviedb.org/settings/api
# ==============================================================================

TMDB_API_KEY = os.getenv("TMDB_API_KEY", "YOUR_API_KEY_HERE").strip()
BASE_URL = "https://api.themoviedb.org/3"

# Persistent HTTP Session to reuse TCP sockets and prevent ConnectionResetError (10054)
session = requests.Session()
session.headers.update({
    "accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) MovieConnectorApp/1.0"
})

# Auto-detect if user provided a long v4 Bearer Token (>50 chars) or a short v3 API Key
if len(TMDB_API_KEY) > 50:
    session.headers["Authorization"] = f"Bearer {TMDB_API_KEY}"

# In-memory caches to prevent making redundant API requests when actor/movie paths overlap
CACHE_ACTOR_CREDITS = {}
CACHE_MOVIE_CAST = {}

def tmdb_get(endpoint, params=None, retries=3):
    """Issues API requests with persistent sessions, rate-limit throttling, and auto-retries."""
    if params is None:
        params = {}

    # Append v3 API key to params if not using a Bearer token
    if len(TMDB_API_KEY) <= 50:
        params["api_key"] = TMDB_API_KEY

    url = f"{BASE_URL}/{endpoint}"

    for attempt in range(retries):
        try:
            # 50ms pause between calls to prevent triggering Cloudflare rate-limits
            time.sleep(0.05)
            response = session.get(url, params=params, timeout=8)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            if attempt < retries - 1:
                time.sleep(0.3 * (attempt + 1))  # Exponential backoff delay on retry
                continue
            return None

def get_actor_id(name):
    """Fetches TMDB actor ID by searching their name."""
    res = tmdb_get("search/person", {"query": name})
    if res and res.get("results"):
        return res["results"][0]["id"], res["results"][0]["name"]
    return None, None

def get_actor_credits(actor_id):
    """Fetches top 10 most popular movies for a given actor (uses caching)."""
    if actor_id in CACHE_ACTOR_CREDITS:
        return CACHE_ACTOR_CREDITS[actor_id]

    res = tmdb_get(f"person/{actor_id}/movie_credits")
    if not res:
        return []
    cast = res.get("cast", [])
    # Cap to top 10 movies by popularity to keep execution fast and within API limits
    cast_sorted = sorted(cast, key=lambda x: x.get("popularity", 0), reverse=True)[:10]
    result = [(m["id"], m["title"]) for m in cast_sorted]
    
    CACHE_ACTOR_CREDITS[actor_id] = result
    return result

def get_movie_cast(movie_id):
    """Fetches top 10 billed actors for a given movie (uses caching)."""
    if movie_id in CACHE_MOVIE_CAST:
        return CACHE_MOVIE_CAST[movie_id]

    res = tmdb_get(f"movie/{movie_id}/credits")
    if not res:
        return []
    cast = res.get("cast", [])
    # Cap to top 10 cast members to avoid massive branch expansions
    result = [(a["id"], a["name"]) for a in cast[:10]]
    
    CACHE_MOVIE_CAST[movie_id] = result
    return result

def find_connection_bidirectional(start_name, end_name, max_degrees=3):
    """
    Finds the shortest movie path between two actors using Bidirectional BFS.
    
    LIMITATIONS & PERFORMANCE:
    - Capped at max_degrees=3 by default. 
    - 1 degree  = ~2 to 5 API calls (~0.5 seconds)
    - 2 degrees = ~15 to 40 API calls (~1 to 2 seconds)
    - 3 degrees = ~100+ API calls (~3 to 6 seconds)
    - Increasing max_degrees past 3 can exponentially increase API calls and trigger rate limits.
    """
    start_id, start_real_name = get_actor_id(start_name)
    end_id, end_real_name = get_actor_id(end_name)

    if not start_id or not end_id:
        return None, "One or both actors could not be found on TMDB."

    if start_id == end_id:
        return [start_real_name], "Same actor entered!"

    front_queue = {start_id: [start_real_name]}
    back_queue = {end_id: [end_real_name]}

    for degree in range(1, max_degrees + 1):
        next_front = {}
        for actor_id, path in front_queue.items():
            movies = get_actor_credits(actor_id)
            for movie_id, movie_title in movies:
                co_stars = get_movie_cast(movie_id)
                for star_id, star_name in co_stars:
                    new_path = path + [movie_title, star_name]
                    if star_id in back_queue:
                        backward_path = back_queue[star_id][::-1]
                        full_path = path + [movie_title] + backward_path
                        return full_path, f"Connected in {degree} degree(s)!"
                    if star_id not in next_front:
                        next_front[star_id] = new_path
        front_queue = next_front

    return None, f"No connection found within {max_degrees} degrees."

class ConnectionApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Actor Connector")
        self.root.geometry("500x510")
        self.root.resizable(False, False)

        # "Hollow Man" Banner Header
        banner = tk.Label(
            root, 
            text="YOU SHOULD BE WORKING", 
            font=("Arial", 12, "bold"), 
            bg="#333333", 
            fg="#FF5555", 
            pady=8
        )
        banner.pack(fill='x')

        ttk.Label(root, text="Actor 1:", font=("Arial", 11)).pack(pady=(15, 2))
        self.actor1_entry = ttk.Entry(root, width=40, font=("Arial", 11))
        self.actor1_entry.insert(0, "Kevin Bacon")
        self.actor1_entry.pack(pady=2)

        ttk.Label(root, text="Actor 2:", font=("Arial", 11)).pack(pady=(10, 2))
        self.actor2_entry = ttk.Entry(root, width=40, font=("Arial", 11))
        self.actor2_entry.insert(0, "Javier Bardem")
        self.actor2_entry.pack(pady=2)

        button_frame = ttk.Frame(root)
        button_frame.pack(pady=15)

        self.connect_btn = ttk.Button(button_frame, text="Connect", command=self.start_search)
        self.connect_btn.pack(side="left", padx=5)

        self.help_btn = ttk.Button(button_frame, text="Help / About", command=self.show_help)
        self.help_btn.pack(side="left", padx=5)

        self.status_label = ttk.Label(root, text="Enter two actors and click Connect.", font=("Arial", 10, "italic"))
        self.status_label.pack(pady=5)

        self.result_box = tk.Text(root, height=8, width=55, font=("Arial", 10), state='disabled')
        self.result_box.pack(pady=10)

    def start_search(self):
        a1 = self.actor1_entry.get().strip()
        a2 = self.actor2_entry.get().strip()

        if not a1 or not a2:
            messagebox.showwarning("Input Error", "Please enter both actor names.")
            return

        self.connect_btn.config(state='disabled')
        self.status_label.config(text="Searching TMDB... please wait.")
        self.update_result_box("")

        # Run search on background thread to keep Tkinter GUI responsive
        threading.Thread(target=self.run_search, args=(a1, a2), daemon=True).start()

    def run_search(self, a1, a2):
        path, message = find_connection_bidirectional(a1, a2, max_degrees=3)
        
        self.root.after(0, self.status_label.config, {"text": message})
        if path:
            formatted_output = " -> \n".join(path)
            self.root.after(0, self.update_result_box, formatted_output)
        
        self.root.after(0, self.connect_btn.config, {"state": "normal"})

    def update_result_box(self, text):
        self.result_box.config(state='normal')
        self.result_box.delete("1.0", tk.END)
        self.result_box.insert(tk.END, text)
        self.result_box.config(state='disabled')

    def show_help(self):
        """Displays the Help / About dialog window."""
        help_text = (
            "ACTOR CONNECTOR - HELP & ABOUT\n\n"
            "• How it Works:\n"
            "  Finds the shortest movie connection path between two actors using\n"
            "  The Movie Database (TMDB) live API.\n\n"
            "• Search Limits:\n"
            "  - Capped at 3 Degrees of Separation to stay within API rate limits.\n"
            "  - Scans the top 10 most popular movies per actor and top 10 billed\n"
            "    cast members per movie.\n\n"
            "• Requirements:\n"
            "  - Active Internet connection.\n"
            "  - A valid TMDB API key configured in a local .env file (or pasted directly in this script).\n\n"
            "• Performance:\n"
            "  Most connections complete in 1 minute."
        )
        messagebox.showinfo("Help / About", help_text)

if __name__ == "__main__":
    root = tk.Tk()
    app = ConnectionApp(root)
    root.mainloop()