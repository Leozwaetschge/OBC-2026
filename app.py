"""Beer pong event GUI (Streamlit). From OBC root: obcvenv/bin/streamlit run 2026_Mitgliederevent/app.py
Two browser windows on the same laptop:
    http://localhost:8501/       -> full screen on the TV: room with the current games, next round, clock, ranking
                                    (the default page always sits at the root address, "/tv" does not exist)
    http://localhost:8501/admin  -> your laptop screen: enter results, start the timer, next round, parameters
Both read and write event_state.json, so the TV shows every change within a second."""
import base64                                                          # room SVG and logo as images (data URI)
import math                                                            # 19 Nov: time slots of the Ring rounds
import html                                                            # names in the HTML tables
import json                                                            # state as text: did something change? (phone page)
import os                                                              # path of the logo

import streamlit as st                                                 # GUI

import tournament as T                                                 # schedule, results, ranking, state file
from room import room_svg, next_room_svg, ko_tree_svg, BLUE, ORANGE                 # SVG of the room (current and next round)

st.set_page_config(page_title="OBC Mitgliederevent", page_icon="🍺", layout="wide")

LOGO_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "obc_logo_transparent.svg")   # OBC logo
LOGO = "data:image/svg+xml;base64," + base64.b64encode(open(LOGO_FILE, "rb").read()).decode()   # embedded once (no file server needed)

CSS = """
<style>
.stApp {background: #FFFFFF; color: #2E1A5E;}
.stApp::before {content: ""; position: fixed; inset: 0; pointer-events: none; z-index: 0;
    background: url(""" + LOGO + """) center 55% / min(85vh, 70vw) no-repeat; opacity: 0.07;}   /* large faint logo */
.block-container {padding-top: 1.0rem; padding-bottom: 0.5rem; max-width: 100%; position: relative; z-index: 1;}

/* Full-width header shell keeps the clock centered on the screen. */
.header-shell {position:relative; width:100%; min-height:6.5rem;}

/* Header band uses the left-side room width; the brand sits inside its frame. */
.headline {display:flex; align-items:center; width:calc(68.75% - 1.375rem); min-height:6.5rem; margin-bottom:0;}

/* Temporary gray borders show the bounds of each TV region. */
/*.debug-frame {box-sizing:border-box; border:1px solid #999; padding:2px;}*/
.brand {display:flex; align-items:center; gap:0.9rem;}
.brand {justify-self:start;}
.brand img {height: 6.2rem;}
.title {font-size:3.4rem; font-weight:800; color:#2E1A5E; letter-spacing:0.01em; line-height:1.05;}
.subtitle {font-size:1.25rem; font-weight:700; color:#7CC800; letter-spacing:0.08em; text-transform:uppercase;}

/* Clock is centered relative to the full-width header shell, not the room-width frame. */
.clock {position:absolute; left:50%; top:50%; transform:translate(-50%, -50%); white-space:nowrap; font-size:4.25rem; font-weight:600; font-variant-numeric:tabular-nums; padding:0.3rem 1.5rem; border-radius:14px;}
.clock.game {background:#7CC800; color:#fff;} .clock.change {background:#F28C00; color:#fff;}
.clock.wait, .clock.over {background:#B9AEDB; color:#fff;}
@media (max-width: 760px) {
    .header-shell {display:flex; flex-direction:column; align-items:center; gap:0.5rem;}
    .headline {width:100%; justify-content:center;}
    .clock {position:static; transform:none;}
}
.section {font-size:2.15rem; font-weight:800; color:#2E1A5E; margin:0.1rem 0 0.05rem 0;}
.fire-preview {font-size:1.6rem; font-weight:800; color:#E08600; padding:0.8rem;}

/* Ranking panel fills the available TV height; title stays above the table. */
.ranking-region {min-height:calc(100vh - 8rem); margin-top: -120px;}
.ranking-title {font-size:2.1rem; font-weight:800; color:#2E1A5E; margin:0 0 0.15rem;}
.pause {color:#5E4B8B; font-size:1.0rem; margin-top:0.4rem;}
table.rank {width:100%; border-collapse:collapse; font-size:0.9rem; color:#2E1A5E;}
table.rank th {color:#2E1A5E; text-align:right; padding:4px 7px; border-bottom:3px solid #7CC800;}
table.rank th:nth-child(2), table.rank td:nth-child(2) {text-align:left;}
table.rank td {text-align:right; padding:3px 7px; font-variant-numeric:tabular-nums;}
table.rank tr:nth-child(even) td {background:rgba(176,136,249,0.12);}
.ko-bracket {display:grid; grid-template-columns:repeat(4,minmax(190px,1fr)); gap:0 1.25rem; min-width:820px; padding:.6rem .15rem 1rem; overflow:visible;}
.ko-stage {display:grid; grid-template-rows:repeat(16,30px); row-gap:4px; min-width:0; position:relative;}
.ko-stage-title {grid-row:1; font-size:1.05rem; line-height:1.15; font-weight:800; color:#2E1A5E; padding:.1rem .15rem .25rem;}
.ko-match {grid-row:var(--match-row) / span 2; align-self:stretch; position:relative; border:2px solid #F2B705; border-radius:9px; background:#FFF8E1; padding:.2rem .35rem; font-size:.82rem; min-width:0; display:flex; flex-direction:column; justify-content:center;}
.ko-match:not(:last-child)::after {content:""; position:absolute; right:-1.28rem; top:50%; width:1.2rem; border-top:2px solid #B9AEDB;}
.ko-team {padding:.1rem .08rem; color:#5E4B8B; overflow-wrap:anywhere; line-height:1.15;}
.ko-score {text-align:center; font-weight:800; color:#2E1A5E; border-top:1px solid rgba(46,26,94,.15); border-bottom:1px solid rgba(46,26,94,.15); line-height:1.2;}
.ko-winner {font-weight:900; color:#2E1A5E; background:rgba(124,200,0,.18);}
.ko-pending {color:#9A91AE; font-style:italic;}
.ko-champion {font-size:1.5rem; font-weight:900; color:#2E1A5E; padding:.6rem;}
.ko-board-wrap {overflow-x:auto; width:100%;}
.st-key-next_btn button, .st-key-next_ko_btn button {background:#7CC800; border-color:#7CC800; color:#fff;}  /* 19 Nov: green */
.st-key-next_btn button:hover, .st-key-next_ko_btn button:hover {background:#6AB000; border-color:#6AB000; color:#fff;}
</style>
"""


def mmss(seconds):
    """Seconds -> "mm:ss"."""
    s = max(0, int(seconds))
    return f"{s // 60:02d}:{s % 60:02d}"


def svg_img(svg):
    """SVG as an <img> (data URI), full column width: the browser draws the whole SVG (st.html filters SVG parts,
    16 Nov: cups not shown); width as an HTML attribute because Streamlit drops the style of the image."""
    data = base64.b64encode(svg.encode()).decode()                     # SVG text -> base64
    return f'<img src="data:image/svg+xml;base64,{data}" width="100%" style="width:100%;height:auto">'


def next_round_html(state, rnd, half=0):
    """Compact room of round rnd (names on the tables) and who sits out."""
    if rnd >= len(state["schedule"]):                                  # after the last round
        return '<div class="pause">fertiiiiiiig :))</div>'
    r = state["schedule"][rnd]
    if T.is_ring_round(state, rnd):
        return '<div class="fire-preview">🔥 Ring of Fire 🔥</div>'
    pause = f'<div class="pause">Pause: {html.escape(", ".join(r["pause"]))}</div>' if r["pause"] else ""
    return svg_img(next_room_svg(state["cfg"]["tables"], r["games"])) + pause


def ranking_html(state):
    """Ranking as a compact HTML table (fits the TV without scrolling); top 3 highlighted."""
    df = T.ranking(state)[["Rang", "Name", "Spiele", "Becher", "Punkte"]]
    head = "".join(f"<th>{c}</th>" for c in df.columns)
    body = "".join(
        '<tr>' + "".join(f"<td>{html.escape(str(v))}</td>" for v in row[1:]) + "</tr>"
        for row in df.itertuples())
    return f'<table class="rank"><tr>{head}</tr>{body}</table>'


def ko_table(state, index):
    """Table of the index-th game of a KO stage: tables 1, 2, ... (fewer games -> the high tables are not needed);
    more games than tables -> they wait and are played one after another on the same tables."""
    return index % max(1, int(state["cfg"]["tables"])) + 1


def knockout_room(state):
    """Room during the KO phase: tables stay where they are, only the tables of this stage are drawn (the unneeded
    ones are removed from the highest number down). Per table: its first game without a result, else its last game.
    Returns games, results and the set of visible tables."""
    games, results, visible = [], {}, set()
    stage_games = T.knockout_games(state)                              # games of the running stage ([] after the final)
    ko = state.get("ko") or {}
    if not stage_games and ko.get("champion"):                         # after the final: the final stays on its table
        stage_games = ko.get("stages", {}).get("final", {}).get("games", [])
    for index, game in enumerate(stage_games):
        table = ko_table(state, index)
        visible.add(table)
        res = T.knockout_result(state, game["id"])
        shown = next((g for g in games if g["table"] == table), None)  # game already on this table
        if shown and not results.get(table):                           # an earlier game still open there -> it stays
            continue
        if shown:                                                      # earlier game finished -> the next one replaces it
            games.remove(shown); results.pop(table, None)
        games.append({**game, "table": table})
        if res:
            results[table] = res
    if not visible:                                                    # after the final: the final table stays visible
        visible = {1}
    return games, results, visible


def knockout_tree_html(state):
    """KO tree (instead of the next round) from the KO phase on: Zwischen-KO, Viertelfinale, Halbfinale, Finale."""
    ko = state.get("ko", {})
    if ko.get("unavailable"):
        return f'<div class="pause">{html.escape(ko.get("reason", "KO nicht verfügbar"))}</div>'
    if not ko:
        return '<div class="pause">Die KO-Phase beginnt nach der letzten Vorrunde.</div>'
    made = {s["stage"]: s["games"] for s in T.knockout_bracket(state)}   # stages drawn so far, with results
    stages = []
    for key, count in (("intermediate", 4), ("quarterfinal", 4), ("semifinal", 2), ("final", 2)):   # 22 Nov: final + 3rd-place game
        games = [dict(g, table=ko_table(state, i)) for i, g in enumerate(made.get(key, []))]
        stages.append({"key": key, "label": T.KO_STAGE_LABELS[key],
                       "games": games + [None] * (count - len(games))})   # not drawn yet -> "offen"
    out = svg_img(ko_tree_svg(stages))
    if ko.get("champion"):
        out += f'<div class="ko-champion">🏆 Sieger: {html.escape(" & ".join(ko["champion"]))}</div>'
    return out


# ---------------------------------------------------------------- TV page
def tv_page():
    st.markdown(CSS + "<style>[data-testid='stSidebar'],[data-testid='stHeader']{display:none;} "
                ".block-container{padding-top:.05rem;} "
                ".block-container > div[data-testid='stVerticalBlock']{gap:.05rem;}</style>",
                unsafe_allow_html=True)                                # no sidebar and header on the TV

    @st.fragment(run_every=1)                                          # redrawn every second: clock and new results
    def board():
        state = T.load()
        zoom = state.get("tv_zoom", 120)                               # size of the whole TV page in % (set in the admin page)
        st.markdown(f"<style>.block-container {{zoom: {zoom}%;}}</style>", unsafe_allow_html=True)   # scales everything
        rounds = len(state["schedule"])
        cur = state["current"]
        if cur >= rounds and not state.get("ko"):
            T.start_knockout(state)
            T.save(state)
        ring_round = T.is_ring_round(state, cur)
        if ring_round and T.prepare_ring_round(state, cur):
            T.save(state)
        half = state.get("ring_half", 0)
        parts = T.ring_part_count(state, cur) if cur < rounds else 2  # parts of this Ring round
        phase, left = T.clock(state)
        label = {"wait": "Bereit", "game": f"Spiel {mmss(left or 0)}", "change": f"Wechsel {mmss(left or 0)}",
                 "over": "Zeit um"}[phase]
        if ring_round:
            label = f"🔥 {label} 🔥"
        header = (f'<div class="header-shell"><div class="headline debug-frame"><div class="brand"><img src="{LOGO}">'
              f'<div><div class="title">OBC Mitgliederevent</div><div class="subtitle">1000 Master Event</div></div></div>'
              f'</div><div class="clock {phase}">{label}</div></div>')
        st.markdown(header, unsafe_allow_html=True)
        if cur >= rounds:                                              # 21 Nov: KO phase -> room and tree side by side, ranking below
            ko_games, ko_results, visible = knockout_room(state)
            room_col, tree_col = st.columns([1, 3.4], gap="large")      # narrow Clubhuus room left, wide KO tree right (same height)
            with room_col:
                current_room = svg_img(room_svg(state["cfg"]["tables"], ko_games, ko_results, title="KO-Phase",
                                                visible=visible))      # only the tables of this KO stage, no Garderobe
                st.markdown(f'<div class="debug-frame">{current_room}</div>', unsafe_allow_html=True)
            with tree_col:
                st.markdown(f'<div class="debug-frame"><div class="section">KO-Baum</div>{knockout_tree_html(state)}</div>',
                            unsafe_allow_html=True)                    # KO tree parallel to the tables
            ranking = f'<div class="ranking-title">Rangliste</div>{ranking_html(state)}'
            st.markdown(f'<div class="debug-frame">{ranking}</div>', unsafe_allow_html=True)   # ranking at the bottom, full width
            return                                                     # rest of the board = layout of the Vorrunden
        left_col, right_col = st.columns([2.2, 1], gap="large")
        # Left column always keeps the fixed room map at the top; the KO tree sits underneath it.
        with left_col:
            if cur < rounds:
                games = T.active_games(state, cur, half)
                res = {game["table"]: T.result(state, cur, game if ring_round else game["table"])
                       for game in games if T.result(state, cur, game if ring_round else game["table"])}
                part = f" · Ring Teil {half + 1}/{parts}" if ring_round else ""   # 19 Nov: current round shown, 1, 2, 3 ...
                current_room = svg_img(room_svg(state["cfg"]["tables"], games, res, ring_of_fire=ring_round,
                                                title=f"Runde {cur + 1}/{rounds}{part}"))
                st.markdown(f'<div class="debug-frame">{current_room}</div>', unsafe_allow_html=True)
            else:
                ko_games, ko_results, visible = knockout_room(state)
                current_room = svg_img(room_svg(state["cfg"]["tables"], ko_games, ko_results, title="KO-Phase · aktuelle Spiele",
                                                visible=visible))      # only the tables of this KO stage
                st.markdown(f'<div class="debug-frame">{current_room}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="debug-frame"><div class="section">KO-Baum</div>{knockout_tree_html(state)}</div>',
                            unsafe_allow_html=True)                    # in the place of "Nächste Runde"
            if cur < rounds:
                if ring_round and half < parts - 1:                    # next part of the same Ring round
                    next_round, next_half = cur, half + 1
                    next_label = f'Nächste: Runde {cur + 1}/{rounds} · Ring Teil {half + 2}/{parts}'
                else:
                    next_round, next_half = cur + 1, 0
                    next_label = f'Nächste Runde {next_round + 1}/{rounds}' if next_round < rounds else "Nächste Runde"
                next_room = f'<div class="section">{next_label}</div>' + next_round_html(state, next_round, next_half)
                st.markdown(f'<div class="debug-frame">{next_room}</div>', unsafe_allow_html=True)
        # Right column contains the ranking title and ranking table.
        with right_col:
            ranking = f'<div class="ranking-title">Rangliste</div>{ranking_html(state)}'
            st.markdown(f'<div class="debug-frame ranking-region">{ranking}</div>', unsafe_allow_html=True)

    board()


# ---------------------------------------------------------------- phone page
def phone_page():
    """/phone: for phones on mobile data. Only the small clock is sent every 1 s; room plan, next round and ranking
    are sent again only when the state changed (result, next round, timer start) -> little data, no lag."""
    st.markdown(CSS + "<style>[data-testid='stSidebar'],[data-testid='stHeader']{display:none;} "
                ".block-container{padding:.3rem .5rem;}</style>", unsafe_allow_html=True)   # no sidebar/header, small margins
    state = T.load()                                                   # state at this full redraw
    st.session_state["phone_state"] = json.dumps(state, sort_keys=True)   # remembered: compared by the clock

    @st.fragment(run_every=1)                                          # only this small part every 1 s
    def clock():
        now = T.load()                                                 # current state
        if json.dumps(now, sort_keys=True) != st.session_state["phone_state"]:   # something changed
            st.rerun(scope="app")                                      # -> redraw the whole page once
        phase, left = T.clock(now)                                     # phase and seconds left
        label = {"wait": "Bereit", "game": f"Spiel {mmss(left or 0)}", "change": f"Wechsel {mmss(left or 0)}",
                 "over": "Zeit um"}[phase]                             # same texts as the TV
        st.markdown(f'<div class="clock {phase}">{label}</div>', unsafe_allow_html=True)
    clock()

    rounds = len(state["schedule"])                                    # number of rounds
    cur = state["current"]
    if cur >= rounds and not state.get("ko"):
        T.start_knockout(state)
        T.save(state)                                             # current round
    ring_round = T.is_ring_round(state, cur)                           # ring of fire round?
    if ring_round and T.prepare_ring_round(state, cur):                # 19 Nov: parts fixed here too (phone opened first)
        T.save(state)
    half = state.get("ring_half", 0)                                   # part of the ring round
    parts = T.ring_part_count(state, cur) if cur < rounds else 2       # parts of this Ring round
    if cur < rounds:                                                   # current room
        games = T.active_games(state, cur, half)
        res = {g["table"]: T.result(state, cur, g if ring_round else g["table"])
               for g in games if T.result(state, cur, g if ring_round else g["table"])}
        st.markdown(f'<div class="section">Runde {cur + 1}/{rounds}</div>'
                    + svg_img(room_svg(state["cfg"]["tables"], games, res, ring_of_fire=ring_round)), unsafe_allow_html=True)
    else:
        ko_games, ko_results, visible = knockout_room(state)
        st.markdown(svg_img(room_svg(state["cfg"]["tables"], ko_games, ko_results, title="KO-Phase · aktuelle Spiele",
                                     visible=visible)), unsafe_allow_html=True)   # only the tables of this KO stage
        st.markdown('<div class="section">KO-Baum</div>' + knockout_tree_html(state), unsafe_allow_html=True)
    if cur < rounds and ring_round and half < parts - 1:               # next part / round (as on the TV)
        nxt, nhalf = cur, half + 1
    elif cur < rounds:
        nxt, nhalf = cur + 1, 0
    if cur < rounds:
        st.markdown('<div class="section">Nächste Runde</div>' + next_round_html(state, nxt, nhalf), unsafe_allow_html=True)
    st.markdown(f'<div class="ranking-title">Rangliste</div>{ranking_html(state)}', unsafe_allow_html=True)   # ranking


# ---------------------------------------------------------------- admin page
def tournament_overview(state):
    """19 Nov: overview of this event for the admin page: games per person, rounds with their time, Ring of Fire, KO."""
    cfg, schedule = state["cfg"], state["schedule"]
    n = len(state["players"])                                          # players of this event
    counts = {}                                                        # planned group games per player
    lines, minute = [], 0                                              # one line per round, start minute of the round
    for i, r in enumerate(schedule):
        if r["kind"] == "ring":                                        # Ring of Fire: everyone plays once, in parts
            parts = T.ring_part_count(state, i)
            for p in state["players"]:
                counts[p] = counts.get(p, 0) + 1
            lines.append(f"- Runde {i + 1} (ab {minute} min): 🔥 **Ring of Fire**, alle spielen, in {parts} Teilen")
            minute += math.ceil(parts / 2) * cfg["slot_min"]          # two parts per time slot
        else:                                                          # normal round
            for g in r["games"]:
                for p in g["a"] + g["b"]:
                    counts[p] = counts.get(p, 0) + 1
            lines.append(f"- Runde {i + 1} (ab {minute} min): {len(r['games'])} Tische, {4 * len(r['games'])} spielen, "
                         f"{len(r['pause'])} Pause")
            minute += cfg["slot_min"]
    games = sorted(set(counts.get(p, 0) for p in state["players"]))   # should be one value
    equal = f"**{games[0]} Gruppenspiele pro Person**" if len(games) == 1 else f"⚠️ ungleich: {games} Spiele"
    ko = ("KO-Phase: Zwischen-KO (Ränge 9–24), Viertelfinale (1–8 + Sieger), Halbfinale, Finale – je eine Runde"
          if n >= 24 else "⚠️ keine KO-Phase (weniger als 24 Spieler)")
    head = (f"**Turnierform:** {n} Spieler · {cfg['tables']} Tische · {cfg['duration_min']} min · {equal} · "
            f"{len(schedule)} Vorrunden, Gruppenphase bis ca. {minute} min · "
            f"{sum(r['kind'] == 'ring' for r in schedule)}× Ring of Fire")
    return "\n".join([head, ""] + lines + ["", ko])


def save_typed(state, games, cur, ko_phase, ring_round):
    """19 Nov: store what is typed in the result boxes (Speichern and Nächste Runde): same keys as the boxes."""
    for g in games:
        key = g.get("id", g["table"])
        suffix = f"ko_{key}" if ko_phase else (f"{cur}_{key}" if ring_round else f"{cur}_{g['table']}")
        ca, cb = st.session_state.get(f"a{suffix}"), st.session_state.get(f"b{suffix}")   # None = box not shown yet
        win = st.session_state.get(f"w{suffix}")
        if ca is None or cb is None:
            continue
        if ko_phase:
            if ca or cb:                                               # 0 : 0 = nothing entered
                T.set_knockout_result(state, g["id"], ca, cb, win if ca == cb else None)
        elif ring_round or ca or cb:                                   # Ring draws are valid results
            T.set_result(state, cur, g if ring_round else g["table"], ca, cb, win if ca == cb else None)
    if not ko_phase and state.get("ko") and cur < len(state["schedule"]):
        state.pop("ko", None)                                          # qualification changed: redraw the KO seeding


def admin_page():
    st.markdown(CSS, unsafe_allow_html=True)
    if not st.session_state.get("admin_ok"):                           # not logged in yet in this browser tab
        pw = st.text_input("Admin password", type="password")          # password field
        if pw and pw == st.secrets.get("admin_password", ""):          # correct (from .streamlit/secrets.toml, never in git)
            st.session_state["admin_ok"] = True                        # remember for this session
            st.rerun()                                                 # show the admin page
        elif pw:
            st.error("Wrong password")                                 # wrong input
        st.stop()                                                      # nothing else of the admin page without password
    state = T.load()
    rounds = len(state["schedule"])

    with st.sidebar:                                                   # TV size, parameters, new event
        st.header("TV")
        zoom = st.number_input("Grösse auf dem TV (%)", min_value=50, max_value=250, value=state.get("tv_zoom", 120), step=5,
                    help="Der TV übernimmt die Grösse innert einer Sekunde")
        if zoom != state.get("tv_zoom", 100):                          # changed -> save at once (no reset needed)
            state["tv_zoom"] = zoom
            T.save(state)
        st.header("Parameter")
        cfg = state["cfg"]
        tables = st.number_input("Tische", 1, 20, cfg["tables"])
        duration = st.number_input("Dauer (min)", 30, 600, cfg["duration_min"], step=15)
        slot = st.number_input("Runde = Spiel + Wechsel (min)", 5, 60, cfg["slot_min"])
        game = st.number_input("Spielzeit (min)", 3, 60, cfg["game_min"])
        n = st.number_input("Spieler (Dummy)", 4, len(T.DUMMY_NAMES), min(cfg["n_players"], len(T.DUMMY_NAMES)))   # 21 Nov:
                                                                       # start value capped: a shorter list no longer crashes the page
        seed = st.number_input("Zufalls-Seed", 0, 99999, cfg["seed"])
        preview = {**cfg, "tables": tables, "duration_min": duration, "slot_min": slot, "game_min": game,
                   "n_players": n, "seed": seed}
        r_prev, g_prev = T.schedule_size(n, preview)                   # rounds really played and games per person
        st.caption(f"→ {r_prev} Vorrunden (max. {T.n_rounds(preview)}) + {T.KO_ROUND_COUNT} KO-Runden · "
                   f"{g_prev} Spiele pro Person in der Vorrunde (alle gleich viele)")
        sure = st.checkbox("Ja, alles zurücksetzen")
        if st.button("Neues Event erstellen", disabled=not sure, type="primary"):
            T.save(T.new_event(preview))                               # new draw, all results gone
            st.rerun()

    cur = state["current"]
    if cur >= rounds and not state.get("ko"):
        T.start_knockout(state)
        T.save(state)
    ko_phase = cur >= rounds and bool(state.get("ko")) and not state["ko"].get("unavailable") and bool(state["ko"].get("stage"))
    ring_round = T.is_ring_round(state, cur)
    if ring_round and T.prepare_ring_round(state, cur):
        T.save(state)
    half = state.get("ring_half", 0)
    parts = T.ring_part_count(state, cur) if cur < rounds else 2       # parts of this Ring round
    round_title = f" · 🔥 Ring of Fire · Teil {half + 1}/{parts}" if ring_round else (f" · {T.KO_STAGE_LABELS.get(state['ko'].get('stage'), 'KO abgeschlossen')}" if ko_phase else "")
    st.title(f"Admin · Runde {min(cur + 1, rounds)} / {rounds}{round_title}")
    with st.expander("Turnierform"):                                   # 19 Nov: form of the tournament (games, Ring rounds),
        st.markdown(tournament_overview(state))                        # a box like "Ganzer Spielplan"
    if cur >= rounds and state.get("ko", {}).get("unavailable"):
        st.warning(state["ko"].get("reason", "KO-Phase nicht verfügbar"))
    if cur >= rounds and state.get("ko", {}).get("stage") is None and state.get("ko", {}).get("champion"):
        st.success("KO-Phase abgeschlossen · Sieger: " + " & ".join(state["ko"]["champion"]))
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("▶ Timer starten", width="stretch"):        # starts the clock on the TV
        state["round_started"] = T.time.time()
        T.save(state)
        st.rerun()
    next_label = f"⏭ Ring Teil {half + 2}/{parts}" if ring_round and half < parts - 1 else "⏭ Nächste Runde"
    if ko_phase:                                                       # 19 Nov: KO stage continues only with this button
        if c2.button("⏭ Nächste Runde", width="stretch", key="next_ko_btn",
                     help="speichert die eingetippten Resultate; weiter erst wenn alle KO-Spiele ein Resultat haben"):
            save_typed(state, T.knockout_games(state), cur, True, False)   # 19 Nov: typed results saved first
            if T.knockout_stage_complete(state):
                T.advance_knockout(state)                              # next stage drawn (or champion after the final)
                state["round_started"] = None                          # timer waits for the next start
            else:
                st.session_state["ko_missing"] = True                  # message after the rerun
            T.save(state)
            st.rerun()
        if st.session_state.pop("ko_missing", False):
            st.warning("Gespeichert, aber noch nicht alle KO-Spiele haben ein Resultat.")
    elif c2.button(next_label, width="stretch", disabled=cur >= rounds, key="next_btn",
                   help="speichert zuerst die eingetippten Resultate"):
        save_typed(state, T.active_games(state, cur, half), cur, False, ring_round)   # 19 Nov: typed results saved first
        if ring_round and half < parts - 1:
            state["ring_half"] = half + 1
        else:
            state["current"] = cur + 1                                 # TV moves on, timer waits for the next start
            state["ring_half"] = 0
        state["round_started"] = None
        T.save(state)
        st.rerun()
    back_label = f"⏮ Ring Teil {half}/{parts}" if ring_round and half > 0 else "⏮ Runde zurück"
    if c3.button(back_label, width="stretch", disabled=cur == 0):
        if ring_round and half > 0:
            state["ring_half"] = half - 1
        else:
            state["current"] = cur - 1
            state["ring_half"] = 0
        state["round_started"] = None
        T.save(state)
        st.rerun()
    if c4.button("🎲 Demo: Zufallsresultate", width="stretch", disabled=(cur >= rounds and not ko_phase)):
        games = T.knockout_games(state) if ko_phase else T.active_games(state, cur, half)
        if ko_phase:
            previous_ko_stage = state["ko"].get("stage")
            for game in games:
                loser = __import__("random").randint(0, state["cfg"]["cups"] - 1)
                if __import__("random").random() < 0.5:
                    T.set_knockout_result(state, game["id"], state["cfg"]["cups"], loser, "a")
                else:
                    T.set_knockout_result(state, game["id"], loser, state["cfg"]["cups"], "b")
            for game in games:                                         # 19 Nov: also into the admin boxes (as the group phase)
                res = T.knockout_result(state, game["id"])
                st.session_state[f'ako_{game["id"]}'] = res["a"]
                st.session_state[f'bko_{game["id"]}'] = res["b"]
                st.session_state[f'wko_{game["id"]}'] = res["winner"]
            if state["ko"].get("stage") != previous_ko_stage:
                state["round_started"] = None
            T.save(state)
            st.rerun()
        T.random_results(state, cur, games)                             # only for testing the display
        for game in games:
            game_key = game.get("id", game["table"])
            generated = T.result(state, cur, game if ring_round else game["table"])
            suffix = f"{cur}_{game_key}" if ring_round else f"{cur}_{game['table']}"
            st.session_state[f'a{suffix}'] = generated["a"]
            st.session_state[f'b{suffix}'] = generated["b"]
            if not ring_round:
                st.session_state[f'w{suffix}'] = generated["winner"]
        T.save(state)
        st.rerun()

    if cur < rounds or ko_phase:                                       # results of the current round / KO stage
        st.subheader(T.KO_STAGE_LABELS[state["ko"]["stage"]] if ko_phase else ("Ring of Fire · Gesamttally" if ring_round else "Resultate (getroffene Becher)"))
        if ring_round:
            st.caption("Gezählte Gesamttally inkl. Bonus/Abzug · Sieg 3 Punkte · Unentschieden 1 · Niederlage 0")
        cups = state["cfg"]["cups"]
        games = T.knockout_games(state) if ko_phase else T.active_games(state, cur, half)
        with st.container():                                           # 19 Nov: no st.form, values known without submit
            entries = []
            for gi, g in enumerate(games):                             # gi: position in the KO stage -> its table
                old = (T.knockout_result(state, g["id"]) if ko_phase else T.result(state, cur, g if ring_round else g["table"])) or {"a": 0, "b": 0, "winner": "a"}
                game_key = g.get("id", g["table"])
                suffix = f"ko_{game_key}" if ko_phase else (f"{cur}_{game_key}" if ring_round else f"{cur}_{g['table']}")
                a_key, b_key, w_key = f'a{suffix}', f'b{suffix}', f'w{suffix}'
                if ring_round:
                    a, b = st.columns(2)
                    w_col = None
                else:
                    a, b, w_col = st.columns([3, 3, 2])
                if ring_round:
                    a_options = {"step": 1, "key": a_key}
                    b_options = {"step": 1, "key": b_key}
                else:
                    a_options = {"min_value": 0, "max_value": cups, "key": a_key}
                    b_options = {"min_value": 0, "max_value": cups, "key": b_key}
                if not ring_round:
                    w_options = {"options": ["a", "b"], "horizontal": True, "key": w_key,
                                 "help": "nur nötig, wenn beide gleich viele Becher haben"}
                if a_key not in st.session_state:
                    a_options["value"] = old["a"]
                if b_key not in st.session_state:
                    b_options["value"] = old["b"]
                if not ring_round and w_key not in st.session_state:
                    w_options["index"] = 0 if old["winner"] == "a" else 1
                match_label = (f'{g["label"]} · Tisch {ko_table(state, gi)}' if ko_phase   # same table as TV and tree
                               else g.get("label", f'Tisch {g["table"]}'))
                ca = a.number_input(f'{match_label}: {" & ".join(g["a"])}', **a_options)
                cb = b.number_input(f'vs {" & ".join(g["b"])}', **b_options)
                win = w_col.radio("Bei Gleichstand", **w_options) if w_col else None
                entries.append((g, ca, cb, win))
            if st.button("💾 Speichern", type="primary", key="save_btn"):
                previous_ko_stage = state["ko"].get("stage") if ko_phase else None
                save_typed(state, games, cur, ko_phase, ring_round)   # everything typed in the boxes
                if ko_phase and state["ko"].get("stage") != previous_ko_stage:
                    state["round_started"] = None
                T.save(state)
                st.success("Gespeichert, der TV zeigt es in einer Sekunde.")
                st.rerun()

    with st.expander("Ganzer Spielplan"):
        for i, r in enumerate(state["schedule"]):
            if T.is_ring_round(state, i):
                if r.get("prepared"):
                    half_text = " · ".join(
                        f'Teil {half + 1}: ' + ", ".join(
                            f'T{g["table"]} {" & ".join(g["a"])} vs {" & ".join(g["b"])}'
                            for g in half_games)
                        for half, half_games in enumerate(r["halves"]))
                    pause = f' · Pause: {", ".join(r["pause"])}' if r["pause"] else ""
                    st.markdown(f"**Runde {i + 1}** · 🔥 Ring of Fire · {half_text}{pause}")
                else:
                    st.markdown(f"**Runde {i + 1}** · 🔥 Ring of Fire · in Teilen")
            else:
                st.markdown(f"**Runde {i + 1}**  ·  " + "  ·  ".join(
                    f'T{g["table"]}: {" & ".join(g["a"])} vs {" & ".join(g["b"])}' for g in r["games"])
                    + (f'  ·  _Pause: {", ".join(r["pause"])}_' if r["pause"] else ""))
    with st.expander("Rangliste"):
        st.dataframe(T.ranking(state)[["Rang", "Name", "Spiele", "Becher", "Punkte"]],
                     hide_index=True, width="stretch")


pg = st.navigation([st.Page(tv_page, title="TV", url_path="tv", default=True),
                    st.Page(phone_page, title="Phone", url_path="phone"),   # phones: refresh 4 s, little data
                    st.Page(admin_page, title="Admin", url_path="admin")], position="hidden")
pg.run()
