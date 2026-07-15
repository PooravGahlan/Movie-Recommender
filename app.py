"""
CineSense • AI Movie Recommender
100% Python — no manual HTML/CSS/JS.
"""

import io
import math
import random
import time
from datetime import datetime

import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image
from streamlit_option_menu import option_menu
from streamlit_lottie import st_lottie
from streamlit_extras.let_it_rain import rain
from streamlit_extras.metric_cards import style_metric_cards

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="CineSense • AI Movie Recommender",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# CONSTANTS
# ============================================================
GENRES = {
    "Action": 28, "Adventure": 12, "Animation": 16, "Comedy": 35, "Crime": 80,
    "Documentary": 99, "Drama": 18, "Family": 10751, "Fantasy": 14, "Horror": 27,
    "Mystery": 9648, "Romance": 10749, "Sci-Fi": 878, "Thriller": 53, "War": 10752,
}
MOODS = {
    "😊 Happy / Feel-good": ["Comedy", "Family", "Animation"],
    "😢 Emotional": ["Drama", "Romance"],
    "😱 Thrilled / Scared": ["Horror", "Thriller"],
    "🤯 Mind-bending": ["Sci-Fi", "Mystery"],
    "💥 Pumped up": ["Action", "Adventure"],
    "🕵️ Curious": ["Crime", "Documentary"],
}
IMG_BASE = "https://image.tmdb.org/t/p/w342"
BASE_URL = "https://api.themoviedb.org/3"

# 👇 Change this to your deployed Node.js app URL later
EMBED_BASE = "https://api.codespecters.com"


# ============================================================
# API KEYS (from secrets)
# ============================================================
api_key = st.secrets.get("TMDB_API_KEY", "")

if not api_key:
    st.title("🎬 CineSense — AI Movie Recommender")
    st.error("TMDB API key not configured. Add it to `.streamlit/secrets.toml`.")
    st.stop()

LOTTIE_URLS = {
    "hero": "https://assets9.lottiefiles.com/packages/lf20_1pxqjqps.json",
    "loading": "https://assets2.lottiefiles.com/packages/lf20_usmfx6bp.json",
    "empty": "https://assets3.lottiefiles.com/packages/lf20_qh5z2fdq.json",
    "success": "https://assets10.lottiefiles.com/packages/lf20_touohxv0.json",
}

# ============================================================
# SESSION STATE
# ============================================================
defaults = {
    "watchlist": {},
    "compare_list": [],
    "quiz_score": 0,
    "quiz_attempts": 0,
    "quiz_question": None,
    "similar_target": None,
    "theme_mood": "🌙 Cinema Dark",
    "current_playing": None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ============================================================
# LOTTIE HELPER
# ============================================================
@st.cache_data(ttl=86400, show_spinner=False)
def load_lottie(url):
    try:
        r = requests.get(url, timeout=6)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def reveal(*elements_fns, delay=0.12):
    for fn in elements_fns:
        fn()
        time.sleep(delay)


# ============================================================
# BOT MASCOT
# ============================================================
BOT_MOVIE_TEMPLATES = [
    "{title} is the latest release — check it out! 🎬",
    "{title} ({year}) has one of the best fan bases and ratings around ⭐ {rating}!",
    "Have you seen {title}? It's trending this week! 🔥",
    "{title} ({year}) — one of the best movies of {year}, in my opinion!",
    "Psst... {title} just dropped, and it's rated ⭐ {rating}/10!",
    "My pick for tonight: {title} ({year}). Add it to your watchlist!",
    "Fun fact: {title} scored ⭐ {rating} on TMDB. Worth a watch!",
    "If you liked {year} movies, don't miss {title}!",
]
BOT_GREETINGS = [
    "Hi there! 👋 I'm Reely, your movie buddy!",
    "Try the Surprise Me tab, it's fun!",
    "Got a favorite genre? Check out Mood Match!",
    "Looking for something to watch tonight?",
]


@st.cache_data(ttl=1800, show_spinner=False)
def get_bot_movie_pool():
    pool = []
    try:
        pool += get_trending()[:10]
    except Exception:
        pass
    try:
        pool += get_latest_releases()[:10]
    except Exception:
        pass
    return [m for m in pool if m.get("title") and m.get("release_date")]


def current_bot_message():
    pool = get_bot_movie_pool()
    tick = int(time.time() // 12)
    rng = random.Random(tick)
    if pool and rng.random() < 0.75:
        m = rng.choice(pool)
        title = m.get("title")
        year = (m.get("release_date") or "----")[:4]
        rating = round(m.get("vote_average", 0), 1)
        template = rng.choice(BOT_MOVIE_TEMPLATES)
        return template.format(title=title, year=year, rating=rating)
    return rng.choice(BOT_GREETINGS)


def render_bot():
    col_a, col_b = st.columns([1, 3])
    with col_a:
        lottie_bot = load_lottie(LOTTIE_URLS["hero"])
        if lottie_bot:
            st_lottie(lottie_bot, height=110, key="bot_lottie")
    with col_b:
        st.info(f"🤖 **Reely says:** {current_bot_message()}")


# ============================================================
# SIDEBAR NAVIGATION
# ============================================================
with st.sidebar:
    def _sidebar_lottie():
        lottie_side = load_lottie(LOTTIE_URLS["hero"])
        if lottie_side:
            st_lottie(lottie_side, height=140, key="sidebar_lottie", speed=1)

    reveal(_sidebar_lottie, lambda: st.title("🎬 CineSense"), delay=0.15)
    st.space(20)
    st.session_state.theme_mood = st.select_slider(
        "🎨 Vibe",
        options=["☀️ Popcorn Light", "🌆 Neon Dusk", "🌙 Cinema Dark"],
        value=st.session_state.theme_mood,
    )
    st.space(20)

    page = option_menu(
        menu_title="Explore",
        options=[
            "Trending & Latest", "By Genre", "Mood Match", "Search",
            "Surprise Me", "Top Rated", "Compare", "AI Recommends",
            "Trivia Quiz", "Watch Providers", "Stats Dashboard",
            "Poster Collage", "My Watchlist",
        ],
        icons=[
            "fire", "collection-play", "emoji-smile", "search",
            "shuffle", "trophy", "bar-chart", "stars",
            "question-circle", "tv", "graph-up",
            "grid-3x3", "bookmark-heart",
        ],
        default_index=0,
        styles={
            "container": {"padding": "4px"},
            "icon": {"font-size": "16px"},
            "nav-link": {"font-size": "14px", "text-align": "left", "margin": "2px"},
        },
    )

    st.space(20)

    target = len(st.session_state.watchlist)
    metric_slot = st.empty()
    if not st.session_state.get("_wl_metric_animated"):
        for n in range(0, target + 1):
            metric_slot.metric("📋 Watchlist size", n)
            time.sleep(0.03)
        st.session_state["_wl_metric_animated"] = True
    else:
        metric_slot.metric("📋 Watchlist size", target)
    style_metric_cards()


# ============================================================
# API HELPERS
# ============================================================
@st.cache_data(ttl=3600, show_spinner=False)
def tmdb_get(endpoint, params=None):
    params = params or {}
    params["api_key"] = api_key
    try:
        r = requests.get(f"{BASE_URL}{endpoint}", params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def get_trending():
    return tmdb_get("/trending/movie/week").get("results", [])


def get_latest_releases():
    today = datetime.now().strftime("%Y-%m-%d")
    return tmdb_get("/discover/movie", {
        "sort_by": "release_date.desc",
        "release_date.lte": today,
        "vote_count.gte": 50,
    }).get("results", [])


def get_by_genre(genre_id, sort="popularity.desc"):
    return tmdb_get("/discover/movie", {"with_genres": genre_id, "sort_by": sort}).get("results", [])


def get_top_rated():
    return tmdb_get("/movie/top_rated").get("results", [])


def search_movies(query):
    return tmdb_get("/search/movie", {"query": query}).get("results", [])


def search_person_credits(query):
    people = tmdb_get("/search/person", {"query": query}).get("results", [])
    if not people:
        return []
    pid = people[0]["id"]
    credits = tmdb_get(f"/person/{pid}/movie_credits")
    return credits.get("cast", []) + credits.get("crew", [])


def get_similar(movie_id):
    return tmdb_get(f"/movie/{movie_id}/similar").get("results", [])


def get_details(movie_id):
    return tmdb_get(f"/movie/{movie_id}")


def get_watch_providers(movie_id):
    return tmdb_get(f"/movie/{movie_id}/watch/providers").get("results", {})


def get_keywords(movie_id):
    return tmdb_get(f"/movie/{movie_id}/keywords").get("keywords", [])


def get_trailer_key(movie_id):
    results = tmdb_get(f"/movie/{movie_id}/videos").get("results", [])
    youtube_vids = [v for v in results if v.get("site") == "YouTube"]
    for v in youtube_vids:
        if v.get("type") == "Trailer" and v.get("official"):
            return v["key"]
    for v in youtube_vids:
        if v.get("type") == "Trailer":
            return v["key"]
    for v in youtube_vids:
        if v.get("type") == "Teaser":
            return v["key"]
    return youtube_vids[0]["key"] if youtube_vids else None


# ============================================================
# 🎥 MOVIE PLAYER — opens your Node.js app
# ============================================================
def render_movie_player(movie):
    if not movie:
        return
    movie_id = movie.get("id")  # <-- this comes from the movie they clicked
    title = movie.get("title") or "Untitled"
    embed_url = f"https://vidsrc.me/embed/movie/{movie_id}"

    st.markdown(f"### 🎥 Now Playing: {title}")
    st.markdown(
        f'<a href="{embed_url}" target="_blank" '
        f'style="display:inline-block;padding:14px 28px;background:#ff4b4b;'
        f'color:white;border-radius:8px;text-decoration:none;font-size:20px;'
        f'font-weight:bold;">▶ Open {title}</a>',
        unsafe_allow_html=True,
    )

    if st.button("✖ Close", key=f"close_{movie_id}"):
        st.session_state.current_playing = None
        st.rerun()


# ============================================================
# UI HELPERS
# ============================================================
def render_grid(movies, key_prefix, limit=10, show_add=True, columns=5, animate=True):
    movies = [m for m in movies if m.get("poster_path")][:limit]
    if not movies:
        st.warning("No results found.")
        return
    cols = st.columns(columns)
    for i, m in enumerate(movies):
        with cols[i % columns]:
            with st.container(border=True):
                st.image(f"{IMG_BASE}{m['poster_path']}", use_container_width=True)
                title = m.get("title") or m.get("name", "Untitled")
                year = (m.get("release_date") or "----")[:4]
                rating = m.get("vote_average", 0)
                st.markdown(f"**{title}**")
                st.caption(f"⭐ {rating:.1f}  •  {year}")

                c1, c2, c3 = st.columns(3)
                with c1:
                    if show_add:
                        if st.button("➕ List", key=f"{key_prefix}_add_{m['id']}_{i}"):
                            st.session_state.watchlist[m["id"]] = m
                            st.toast(f"Added '{title}' to watchlist ✅")
                            rain(emoji="🎬", font_size=30, falling_speed=5, animation_length=1)
                with c2:
                    if st.button("🔎 Sim", key=f"{key_prefix}_sim_{m['id']}_{i}"):
                        st.session_state["similar_target"] = m
                with c3:
                    if st.button("🎥 Play", key=f"{key_prefix}_play_{m['id']}_{i}"):
                        st.session_state.current_playing = m
                        st.rerun()

                trailer_q = f"{title} {year} trailer".replace(" ", "+")
                st.markdown(f"[▶ Trailer](https://www.youtube.com/results?search_query={trailer_q})")
        if animate and (i + 1) % columns == 0:
            time.sleep(0.08)


def animated_spin(label="Spinning the reel...", steps=20, delay=0.02):
    progress = st.progress(0, text=label)
    for pct in range(steps):
        time.sleep(delay)
        progress.progress(int((pct + 1) / steps * 100), text=label)
    progress.empty()


# ============================================================
# SHOW PLAYER
# ============================================================
if st.session_state.current_playing:
    render_movie_player(st.session_state.current_playing)
    st.divider()


# ============================================================
# HERO
# ============================================================
hero_col1, hero_col2 = st.columns([3, 2])
with hero_col1:
    st.title("🎬 CineSense")
    st.caption(f"Vibe: {st.session_state.theme_mood}  •  AI-Powered Movie Discovery")
    st.write("Discover trending hits, mood-based picks, and hidden gems — curated for you.")
with hero_col2:
    render_bot()

st.space(20)

# ============================================================
# PAGE: Trending & Latest
# ============================================================
if page == "Trending & Latest":
    reveal(
        lambda: st.subheader("🔥 Trending This Week"),
        lambda: render_grid(get_trending(), "trend"),
        lambda: st.subheader("🆕 Latest Releases"),
        lambda: render_grid(get_latest_releases(), "latest"),
    )

# ============================================================
# PAGE: By Genre
# ============================================================
elif page == "By Genre":
    genre_choice = st.multiselect("Pick one or more genres", list(GENRES.keys()), default=["Action"])
    sort_choice = st.selectbox("Sort by", ["Popularity", "Rating"], index=0)
    sort_param = "popularity.desc" if sort_choice == "Popularity" else "vote_average.desc"
    if genre_choice:
        genre_ids = ",".join(str(GENRES[g]) for g in genre_choice)
        results = tmdb_get("/discover/movie", {
            "with_genres": genre_ids, "sort_by": sort_param, "vote_count.gte": 100,
        }).get("results", [])
        reveal(
            lambda: st.subheader("🎭 Top 10 by Genre"),
            lambda: render_grid(results, "genre", limit=10),
        )

# ============================================================
# PAGE: Mood Match
# ============================================================
elif page == "Mood Match":
    st.subheader("🧠 What's your mood today?")
    mood = st.radio("Pick a mood", list(MOODS.keys()), horizontal=True)
    if mood:
        genre_ids = ",".join(str(GENRES[g]) for g in MOODS[mood])
        results = tmdb_get("/discover/movie", {
            "with_genres": genre_ids, "sort_by": "vote_average.desc", "vote_count.gte": 200,
        }).get("results", [])
        reveal(
            lambda: st.caption(f"Recommended for **{mood}** based on genres: {', '.join(MOODS[mood])}"),
            lambda: render_grid(results, "mood"),
        )

# ============================================================
# PAGE: Search
# ============================================================
elif page == "Search":
    st.subheader("🔍 Search Movies, Actors or Directors")
    q = st.text_input("Search by title, actor, or director name")
    search_type = st.radio("Search type", ["Title", "Person (Actor/Director)"], horizontal=True)
    if q:
        with st.spinner("Searching TMDB..."):
            if search_type == "Title":
                render_grid(search_movies(q), "search")
            else:
                render_grid(search_person_credits(q), "search_person")

    if st.session_state.get("similar_target"):
        target = st.session_state["similar_target"]
        st.markdown(f"### 🔎 Movies similar to **{target.get('title', target.get('name'))}**")
        render_grid(get_similar(target["id"]), "similar")

# ============================================================
# PAGE: Surprise Me
# ============================================================
elif page == "Surprise Me":
    st.subheader("🎲 Surprise Me")
    st.write("Can't decide? Let CineSense spin the reel for you.")
    if st.button("🎰 Spin the Reel"):
        animated_spin("Spinning the reel...")
        pool = get_trending() + get_top_rated()
        pick = random.choice([m for m in pool if m.get("poster_path")])
        rain(emoji="🍿", font_size=28, falling_speed=6, animation_length=1)
        c1, c2 = st.columns([1, 2])
        with c1:
            st.image(f"{IMG_BASE}{pick['poster_path']}", use_container_width=True)
        with c2:
            st.markdown(f"### {pick.get('title')}")
            st.caption(f"⭐ {pick.get('vote_average', 0):.1f}  •  {(pick.get('release_date') or '----')[:4]}")
            st.write(pick.get("overview", "No description available."))
            trailer_q = f"{pick.get('title')} trailer".replace(" ", "+")
            st.markdown(f"[▶ Watch Trailer](https://www.youtube.com/results?search_query={trailer_q})")

            c1a, c1b = st.columns(2)
            with c1a:
                if st.button("➕ Add to Watchlist", key="surprise_add"):
                    st.session_state.watchlist[pick["id"]] = pick
                    st.toast("Added to watchlist ✅")
            with c1b:
                if st.button("🎥 Watch Now", key="surprise_play"):
                    st.session_state.current_playing = pick
                    st.rerun()

# ============================================================
# PAGE: Top Rated
# ============================================================
elif page == "Top Rated":
    st.subheader("🏆 Top Rated of All Time")
    min_year, max_year = st.slider("Filter by release year", 1950, datetime.now().year, (1990, datetime.now().year))
    min_rating = st.slider("Minimum rating", 0.0, 10.0, 7.0)
    results = get_top_rated()
    filtered = [
        m for m in results
        if m.get("release_date") and min_year <= int(m["release_date"][:4]) <= max_year
        and m.get("vote_average", 0) >= min_rating
    ]
    render_grid(filtered, "top_rated", limit=15)

# ============================================================
# PAGE: Compare
# ============================================================
elif page == "Compare":
    st.subheader("⚖️ Compare Two Movies")
    c1, c2 = st.columns(2)
    with c1:
        q1 = st.text_input("Movie 1", key="cmp1")
    with c2:
        q2 = st.text_input("Movie 2", key="cmp2")

    def show_compare_card(query, col):
        if not query:
            return
        res = search_movies(query)
        if not res:
            col.warning("Not found")
            return
        m = res[0]
        d = get_details(m["id"])
        with col:
            with st.container(border=True):
                if m.get("poster_path"):
                    st.image(f"{IMG_BASE}{m['poster_path']}", use_container_width=True)
                st.markdown(f"**{d.get('title')}**")
                st.metric("⭐ Rating", f"{d.get('vote_average', 0):.1f}", f"{d.get('vote_count', 0)} votes")
                st.write(f"📅 Release: {d.get('release_date', 'N/A')}")
                st.write(f"⏱ Runtime: {d.get('runtime', 'N/A')} min")
                st.write(f"💰 Budget: ${d.get('budget', 0):,}")
                st.write(f"🎟 Revenue: ${d.get('revenue', 0):,}")
                genres = ", ".join(g["name"] for g in d.get("genres", []))
                st.write(f"🎭 Genres: {genres}")

    cc1, cc2 = st.columns(2)
    show_compare_card(q1, cc1)
    show_compare_card(q2, cc2)
    style_metric_cards()

# ============================================================
# PAGE: AI Recommends
# ============================================================
elif page == "AI Recommends":
    st.subheader("✨ AI Recommends — based on your watchlist")
    wl = list(st.session_state.watchlist.values())
    if not wl:
        st.info("Add a few movies to your watchlist first — CineSense learns your taste from it.")
        lottie_empty = load_lottie(LOTTIE_URLS["empty"])
        if lottie_empty:
            st_lottie(lottie_empty, height=220, key="empty_lottie")
    else:
        genre_counter = {}
        for m in wl:
            for gid in m.get("genre_ids", []):
                genre_counter[gid] = genre_counter.get(gid, 0) + 1
        top_genre_ids = sorted(genre_counter, key=genre_counter.get, reverse=True)[:3]
        rev_genres = {v: k for k, v in GENRES.items()}
        top_genre_names = [rev_genres.get(g, str(g)) for g in top_genre_ids]

        avg_rating = sum(m.get("vote_average", 0) for m in wl) / len(wl)

        st.caption(f"Detected taste profile: **{', '.join(top_genre_names) or 'mixed'}**, "
                   f"average rating threshold ≈ {avg_rating:.1f}")

        with st.spinner("Curating personalized picks..."):
            genre_ids_str = ",".join(str(g) for g in top_genre_ids) if top_genre_ids else ""
            params = {"sort_by": "vote_average.desc", "vote_count.gte": 300}
            if genre_ids_str:
                params["with_genres"] = genre_ids_str
            results = tmdb_get("/discover/movie", params).get("results", [])
            watched_ids = set(st.session_state.watchlist.keys())
            results = [m for m in results if m["id"] not in watched_ids]
        render_grid(results, "ai_rec", limit=10)

# ============================================================
# PAGE: Trivia Quiz
# ============================================================
elif page == "Trivia Quiz":
    st.subheader("❓ Movie Trivia Quiz")
    st.caption(f"Score: {st.session_state.quiz_score} / {st.session_state.quiz_attempts}")

    def new_question():
        pool = get_trending() + get_top_rated()
        pool = [m for m in pool if m.get("release_date") and m.get("poster_path")]
        movie = random.choice(pool)
        correct_year = movie["release_date"][:4]
        wrong_years = set()
        while len(wrong_years) < 3:
            offset = random.choice([-3, -2, -1, 1, 2, 3, 4, 5])
            wrong_years.add(str(int(correct_year) + offset))
        options = list(wrong_years) + [correct_year]
        random.shuffle(options)
        st.session_state.quiz_question = {
            "movie": movie, "correct": correct_year, "options": options,
        }

    if st.session_state.quiz_question is None:
        new_question()

    q = st.session_state.quiz_question
    movie = q["movie"]
    c1, c2 = st.columns([1, 2])
    with c1:
        st.image(f"{IMG_BASE}{movie['poster_path']}", width=200)
    with c2:
        st.markdown(f"### What year was **{movie.get('title')}** released?")
        choice = st.radio("Pick one", q["options"], key=f"quiz_{movie['id']}")
        if st.button("Submit Answer"):
            st.session_state.quiz_attempts += 1
            if choice == q["correct"]:
                st.session_state.quiz_score += 1
                st.success("Correct! 🎉")
                rain(emoji="🌟", font_size=30, falling_speed=5, animation_length=1)
            else:
                st.error(f"Not quite — it was {q['correct']}.")
            new_question()
            st.rerun()

# ============================================================
# PAGE: Watch Providers
# ============================================================
elif page == "Watch Providers":
    st.subheader("📺 Where to Watch")
    q = st.text_input("Search a movie title to see streaming availability")
    region = st.selectbox("Region", ["US", "IN", "GB", "CA", "AU", "DE", "FR"], index=1)
    if q:
        res = search_movies(q)
        if not res:
            st.warning("No results found.")
        else:
            m = res[0]
            with st.container(border=True):
                c1, c2 = st.columns([1, 2])
                with c1:
                    if m.get("poster_path"):
                        st.image(f"{IMG_BASE}{m['poster_path']}", use_container_width=True)
                with c2:
                    st.markdown(f"### {m.get('title')}")
                    providers = get_watch_providers(m["id"]).get(region, {})
                    if not providers:
                        st.info("No streaming info available for this region.")
                    else:
                        for kind, label in [("flatrate", "📡 Stream"), ("rent", "💵 Rent"), ("buy", "🛒 Buy")]:
                            items = providers.get(kind, [])
                            if items:
                                st.write(f"**{label}:** " + ", ".join(p["provider_name"] for p in items))
                        if providers.get("link"):
                            st.markdown(f"[Open on JustWatch]({providers['link']})")

# ============================================================
# PAGE: Stats Dashboard
# ============================================================
elif page == "Stats Dashboard":
    st.subheader("📊 Your Watchlist Stats")
    wl = list(st.session_state.watchlist.values())
    if not wl:
        st.info("Your watchlist is empty — add movies to see stats.")
    else:
        m1, m2, m3 = st.columns(3)
        m1.metric("🎬 Movies", len(wl))
        m2.metric("⭐ Avg Rating", f"{sum(m.get('vote_average', 0) for m in wl) / len(wl):.1f}")
        years = [int((m.get("release_date") or "0000")[:4]) for m in wl if m.get("release_date")]
        m3.metric("📅 Avg Year", int(sum(years) / len(years)) if years else "N/A")
        style_metric_cards()

        st.space(20)
        rev_genres = {v: k for k, v in GENRES.items()}
        genre_counter = {}
        for m in wl:
            for gid in m.get("genre_ids", []):
                genre_counter[rev_genres.get(gid, str(gid))] = genre_counter.get(rev_genres.get(gid, str(gid)), 0) + 1
        if genre_counter:
            st.write("**Genre breakdown**")
            st.bar_chart(pd.Series(genre_counter))

        rating_df = pd.DataFrame([{"Title": m.get("title"), "Rating": m.get("vote_average", 0)} for m in wl])
        st.write("**Ratings by title**")
        st.bar_chart(rating_df.set_index("Title"))

# ============================================================
# PAGE: Poster Collage
# ============================================================
elif page == "Poster Collage":
    st.subheader("🖼️ Poster Collage Maker")
    wl = list(st.session_state.watchlist.values())
    if not wl:
        st.info("Add movies to your watchlist to build a collage.")
    else:
        cols_n = st.slider("Columns", 2, 6, 4)
        if st.button("🧩 Generate Collage"):
            with st.spinner("Assembling collage..."):
                posters = [m for m in wl if m.get("poster_path")]
                thumb_w, thumb_h = 180, 270
                rows_n = (len(posters) + cols_n - 1) // cols_n
                collage = Image.new("RGB", (cols_n * thumb_w, rows_n * thumb_h), (10, 10, 10))
                for i, m in enumerate(posters):
                    try:
                        resp = requests.get(f"{IMG_BASE}{m['poster_path']}", timeout=10)
                        img = Image.open(io.BytesIO(resp.content)).convert("RGB").resize((thumb_w, thumb_h))
                        x = (i % cols_n) * thumb_w
                        y = (i // cols_n) * thumb_h
                        collage.paste(img, (x, y))
                    except Exception:
                        continue
                buf = io.BytesIO()
                collage.save(buf, format="PNG")
                st.image(collage, caption="Your Watchlist Collage", use_container_width=True)
                st.download_button("⬇️ Download Collage", buf.getvalue(), "cinesense_collage.png", "image/png")
                rain(emoji="🎞️", font_size=26, falling_speed=6, animation_length=1)

# ============================================================
# PAGE: My Watchlist
# ============================================================
elif page == "My Watchlist":
    st.subheader("📋 My Watchlist")
    if not st.session_state.watchlist:
        st.info("Your watchlist is empty. Add movies from the other pages using ➕ List.")
        lottie_empty = load_lottie(LOTTIE_URLS["empty"])
        if lottie_empty:
            st_lottie(lottie_empty, height=220, key="wl_empty_lottie")
    else:
        wl = list(st.session_state.watchlist.values())
        render_grid(wl, "wl", limit=50, show_add=False)

        df = pd.DataFrame([{
            "Title": m.get("title"),
            "Year": (m.get("release_date") or "----")[:4],
            "Rating": m.get("vote_average"),
            "Overview": m.get("overview"),
        } for m in wl])
        csv = df.to_csv(index=False).encode("utf-8")
        json_bytes = df.to_json(orient="records", indent=2).encode("utf-8")

        d1, d2, d3 = st.columns(3)
        with d1:
            st.download_button("⬇️ Export as CSV", csv, "my_watchlist.csv", "text/csv")
        with d2:
            st.download_button("⬇️ Export as JSON", json_bytes, "my_watchlist.json", "application/json")
        with d3:
            if st.button("🗑 Clear Watchlist"):
                st.session_state.watchlist = {}
                st.rerun()

# ============================================================
# FOOTER
# ============================================================
st.space(40)
st.divider()
st.caption("Built with ❤️ using Streamlit + TMDB API · CineSense — pure Python.")
