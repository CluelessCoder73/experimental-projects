# Experimental Projects

A collection of lightweight Python scripts, utility tools, and API experiments.

---

## 📁 Projects Included

### 🎬 1. Three Degrees of Separation (`three_degrees_of_separation.pyw`)

A GUI-based Python application that calculates the shortest movie path connecting any two actors using **The Movie Database (TMDB) API**.

![image alt](https://github.com/CluelessCoder73/experimental-projects/blob/cd1b89294388fffaa9d2fd93b1a7d30d9c8519dd/three_degrees_of_separation.png)

#### Features
* **Bidirectional Search:** Fast graph traversal connecting actor credits to movie cast lists.
* **Tkinter GUI:** Runs windowed without a terminal/console window using `.pyw`.
* **API Protection:** Built-in TCP session pooling, request throttling, and caching to avoid hitting rate limits.
* **Completion Alert:** Plays a native Windows chime when a search finishes.

#### Prerequisites
* **Python 3.8+**
* Required packages:
  ```bash
  pip install requests python-dotenv

```

* A free **TMDB API Key** (v3 API key or v4 Read Access Token) from [TMDB Settings](https://www.google.com/search?q=https://www.themoviedb.org/settings/api).

#### Setup

1. Copy `.env.example` to `.env` in the project root:
```bash
cp .env.example .env

```


2. Open `.env` and add your TMDB API key:
```env
TMDB_API_KEY=your_tmdb_api_key_here

```


3. Run the application:
```bash
python three_degrees_of_separation.pyw

```



---

## ⚙️ Environment Configuration (`.env`)

This repository uses a single `.env` file to manage credentials across various experimental tools. Reference `.env.example` to see required key formats for individual projects before running them locally.

```

```