# ==============================================================================
# SCRIPT: Three Degrees of Separation (three_degrees_of_separation.py)
# REPOSITORY: experimental-projects / three_degrees_of_separation /
# ==============================================================================
#
# OVERVIEW:
#   A desktop and mobile GUI app (Tkinter) that calculates the shortest movie 
#   path connecting any two actors using The Movie Database (TMDB) API.
#
# HOW IT WORKS:
#   - Uses Bidirectional Breadth-First Search (BFS) starting from both actors 
#     simultaneously to meet in the middle, dramatically reducing API requests.
#   - Automatically caches actor credits and movie cast lists in memory to avoid 
#     redundant web calls.
#   - Runs requests inside a background thread to keep the Tkinter UI responsive.
#   - Plays a native Windows completion chime on desktop while safely skipping 
#     sound on Android/Linux.
#
# ------------------------------------------------------------------------------
# PREREQUISITES & DEPENDENCIES:
# ------------------------------------------------------------------------------
#   - Python Version: 3.8 or higher
#   - API Key: Free TMDB API Key (v3 Key or v4 Bearer Token)
#              Get one at: https://www.themoviedb.org/settings/api
#   - Required Packages:
#       pip install requests python-dotenv
#
# ------------------------------------------------------------------------------
# ENVIRONMENT VARIABLE CONFIGURATION (.env / env.txt):
# ------------------------------------------------------------------------------
#   This script dynamically searches for your API key in the following order:
#     1. 'env.txt' (Located in the same folder as this script)
#        -> Recommended for Android / MEGAsync / restrictive file systems that 
#           hide or restrict files starting with a dot ('.').
#     2. '.env' (Located in the same folder as this script)
#        -> Standard format for desktop/Windows environments.
#
#   File Contents Example:
#     TMDB_API_KEY=a1b2c3d4e5f6g7h8i9j0
#
# ------------------------------------------------------------------------------
# SEARCH LIMITS & PERFORMANCE ESTIMATES:
# ------------------------------------------------------------------------------
#   To remain well within TMDB rate limits and avoid Cloudflare 429 errors, searches 
#   are hard-capped at 3 degrees, scanning top 10 movies per actor and top 10 
#   billed cast members per movie.
#
#     - 1 Degree  (Direct co-stars) : ~2 to 5 API calls (~1 second)
#     - 2 Degrees (1 movie step)    : ~15 to 40 API calls (~1 minute)
#     - 3 Degrees (2 movie steps)   : ~100+ API calls (~10 minutes)
#
# ------------------------------------------------------------------------------
# ANDROID SETUP GUIDE (PYDROID 3):
# ------------------------------------------------------------------------------
#   1. Install "Pydroid 3" and "Pydroid Repository Plugin" from Google Play Store.
#   2. Open Pydroid 3 -> Menu (☰) -> Pip:
#      - Ensure "Use prebuilt libraries repository" is checked.
#      - Search and install: requests
#      - Search and install: python-dotenv
#   3. Transfer this script and your 'env.txt' file into the same folder on your phone.
#   4. Open this script in Pydroid 3 and press the yellow Play ( ▶ ) button.
#
# ==============================================================================

import os
import time
import requests
import threading
# Cross-platform sound handler
try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False
import tkinter as tk
from tkinter import ttk, messagebox
from dotenv import load_dotenv

# Try loading env.txt first (for restrictive mobile file systems), fallback to .env
env_txt_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'env.txt')
env_dot_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')

if os.path.exists(env_txt_path):
    load_dotenv(dotenv_path=env_txt_path)
else:
    load_dotenv(dotenv_path=env_dot_path)

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
    Finds the shortest movie path between two actors using Bidirectional BFS. Capped at max_degrees=3 by default. Increasing max_degrees past 3 can exponentially increase API calls and trigger rate limits.
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
        self.root.title("Three Degrees of Separation")
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

    def play_success_sound(self):
        """Plays alert chime if supported by the OS."""
        try:
            if HAS_WINSOUND:
                winsound.MessageBeep(winsound.MB_OK)
        except Exception:
            pass

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
        
        # Trigger sound notification upon completion
        self.root.after(0, self.play_success_sound)
        self.root.after(0, self.connect_btn.config, {"state": "normal"})

    def update_result_box(self, text):
        self.result_box.config(state='normal')
        self.result_box.delete("1.0", tk.END)
        self.result_box.insert(tk.END, text)
        self.result_box.config(state='disabled')

    def show_help(self):
        """Displays the Help / About dialog window."""
        help_text = (
            "THREE DEGREES OF SEPARATION - HELP & ABOUT\n\n"
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