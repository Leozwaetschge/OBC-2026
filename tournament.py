"""Beer pong event logic (no GUI): parameters, schedule, results, ranking and the saved state.

Rules of this first version:
    - always 2 vs 2; every round the duos and the pairings are drawn completely at random
    - EVERY player plays exactly the same number of games (a table may stay empty for that)
    - ranking per person with absolute totals: points (3 per win), then cups hit, then cup difference;
      a team that loses 9:10 gives BOTH its players 9 cups hit
"""
import json                                                            # state file
import math                                                            # number of rounds
import os                                                              # paths
import random                                                          # random duos and pairings
import time                                                            # round timer

import pandas as pd                                                    # ranking table

FOLDER = os.path.dirname(os.path.abspath(__file__))                    # .../OBC/2026_Mitgliederevent
STATE_FILE = os.path.join(FOLDER, "event_state.json")                  # everything of the event (survives a restart)

DEFAULTS = {                                                           # flexible parameters (changed in the admin page)
    "tables": 8,                                                       # beer pong tables in the room
    "duration_min": 240,                                               # whole event in minutes 
    "slot_min": 20,                                                    # one round = game + change
    "game_min": 18,                                                    # playing time of one game
    "cups": 10,                                                        # cups per side
    "points_win": 3,                                                   # points for a win (loss: 0)
    "points_draw": 1,                                                  # points per player for a Ring of Fire draw
    "n_players": 40,                                                   # dummy: number of players
    "seed": 2026,                                                      # random seed of the draw (same seed = same schedule)
}

DUMMY_NAMES = [f"Spieler {i}" for i in range(1, 49)]   # placeholders (real names removed 23 Nov)


def n_rounds(cfg):
    """Rounds that fit into the event: duration / slot, rounded down (210 / 15 = 14)."""
    return math.floor(cfg["duration_min"] / cfg["slot_min"])


def ring_round_indices(rounds):
    """Zero-based Ring of Fire rounds: the middle round and the second-to-last round."""
    if rounds < 4:
        return []
    middle_round = math.ceil((rounds - 2) / 2)
    return sorted({middle_round - 1, rounds - 2})


def _regular_games_per_player(n_players, tables, rounds):
    """Largest equal game count for regular 2v2 rounds only."""
    if n_players < 4 or rounds <= 0:
        return 0
    usable = min(tables, n_players // 4)                               # tables that can be filled in one round
    for g in range(usable * 4 * rounds // max(n_players, 1), -1, -1):  # from the upper bound downwards
        if (n_players * g) % 4 == 0 and n_players * g // 4 <= usable * rounds:   # whole games, fits in time
            return g
    return 0


def games_per_player(n_players, tables, rounds):
    """Regular equal games plus one Ring of Fire game in each special round."""
    fire_rounds = len(ring_round_indices(rounds))
    return _regular_games_per_player(n_players, tables, rounds - fire_rounds) + fire_rounds


def build_schedule(players, cfg):
    """Build regular 2v2 rounds and Ring placeholders for ranking-based matchups."""
    rng = random.Random(cfg["seed"])                                   # reproducible draw
    rounds = n_rounds(cfg)                                             # e.g. 14
    ring_indices = ring_round_indices(rounds)
    regular_rounds = rounds - len(ring_indices)
    regular_g = _regular_games_per_player(len(players), cfg["tables"], regular_rounds)
    total = len(players) * regular_g // 4
    usable = min(cfg["tables"], len(players) // 4)                     # tables per round at most
    per_round = [total // max(regular_rounds, 1) + (1 if r < total % max(regular_rounds, 1) else 0)
                 for r in range(regular_rounds)]
    per_round = [min(k, usable) for k in per_round]                    # never more than the tables (cannot happen with g)
    played = {p: 0 for p in players}                                   # games per player so far
    schedule = []
    regular_index = 0
    for round_index in range(rounds):                                  # one round
        if round_index in ring_indices:
            schedule.append({"kind": "ring", "games": [], "halves": [[], []], "pause": [], "prepared": False})
            for player in players:
                played[player] += 1
            continue
        k = per_round[regular_index]
        regular_index += 1
        order = sorted(players, key=lambda p: (played[p], rng.random()))   # fewest games first, random among equals
        # first sorts by the number of games played, then randomly among those with the same number of games played
        on = order[:4 * k]                                             # the 4k players of this round
        rng.shuffle(on)                                                # random duos and random opponents
        tables = rng.sample(range(1, cfg["tables"] + 1), k)            # random tables, so not always table 1-k
        games = [{"table": t, "a": on[4 * i:4 * i + 2], "b": on[4 * i + 2:4 * i + 4]}   # duo a vs duo b
                 for i, t in enumerate(sorted(tables))] # e.g on[0:2] vs on[2:4] are index 0,1 vs 2,3 
        for p in on:
            played[p] += 1                                             # count the game
        schedule.append({"kind": "regular", "games": games, "pause": sorted(order[4 * k:])})   # the rest sits out this round
    return schedule, regular_g + len(ring_indices)


def is_ring_round(state, rnd):
    """Whether the stored round is a Ring of Fire round."""
    return 0 <= rnd < len(state["schedule"]) and state["schedule"][rnd].get("kind") == "ring"


def prepare_ring_round(state, rnd):
    """Freeze a Ring round's ranking-based groups and divide games evenly between two halves."""
    round_data = state["schedule"][rnd]
    if round_data.get("kind") != "ring" or round_data.get("prepared"):
        return False
    ranked_players = ranking(state)["Name"].tolist()
    games, pause = [], []
    for start in range(0, len(ranked_players), 4):
        group = ranked_players[start:start + 4]
        if len(group) == 4:
            side_a, side_b = [group[0], group[2]], [group[1], group[3]]
        elif len(group) == 3:
            side_a, side_b = [group[0]], group[1:]
        elif len(group) == 2:
            side_a, side_b = group[:1], group[1:]
        else:
            pause.extend(group)
            continue
        games.append({"a": side_a, "b": side_b})
    split = (len(games) + 1) // 2
    for index, game in enumerate(games):
        half = 0 if index < split else 1
        table = index + 1 if half == 0 else index - split + 1
        game.update({"id": f"ring-{rnd}-{index}", "half": half, "table": table})
        round_data["halves"][half].append(game)
    round_data["games"] = games
    round_data["pause"] = pause
    round_data["prepared"] = True
    return True


def active_games(state, rnd, half=0):
    """Games displayed and scored for a normal round or one Ring of Fire half."""
    if is_ring_round(state, rnd):
        return state["schedule"][rnd].get("halves", [[], []])[half]
    return state["schedule"][rnd]["games"]


def _result_key(table):
    """Use a stable Ring game id, or the physical table id for a regular game."""
    if isinstance(table, dict):
        return str(table.get("id", table["table"]))
    return str(table)


def new_event(cfg=None, names=None):
    """Fresh event state with dummy players (names: own list, else the dummy names)."""
    cfg = {**DEFAULTS, **(cfg or {})}                                  # missing values from DEFAULTS
    players = list(names) if names else DUMMY_NAMES[:cfg["n_players"]]   # e.g. the first 40 dummy names
    schedule, g = build_schedule(players, cfg)                         # draw of the whole evening
    return {"cfg": cfg, "players": players, "schedule": schedule, "games_each": g,
            "results": {}, "current": 0, "ring_half": 0, "ring_rule_version": 1,
            "round_started": None}                                    # results: {"<round>": {"<game id>": {...}}}


def load():
    """State from event_state.json (a new dummy event if there is none)."""
    if not os.path.isfile(STATE_FILE):                                 # first start
        state = new_event()
        save(state)
        return state
    with open(STATE_FILE) as f:
        state = json.load(f)
    if state.get("ring_rule_version", 0) < 1:
        state.setdefault("ring_half", 0)
        current = state.get("current", 0)
        for rnd in ring_round_indices(len(state["schedule"])):
            if rnd >= current and not state.get("results", {}).get(str(rnd)):
                state["schedule"][rnd] = {"kind": "ring", "games": [], "halves": [[], []],
                                          "pause": [], "prepared": False}
                if rnd == current:
                    state["round_started"] = None
        state["ring_rule_version"] = 1
        save(state)
    return state


def save(state):
    """Write the state atomically (temp file + rename: a crash never leaves half a file)."""
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f, indent=1, ensure_ascii=False)
    os.replace(tmp, STATE_FILE)


def set_result(state, rnd, table, cups_a, cups_b, winner=None):
    """Store a game score; omitted winner is inferred from the scores, including draws."""
    if winner is None:                                                 # no tie: the higher number wins
        winner = "a" if cups_a > cups_b else "b" if cups_b > cups_a else "draw"
    state["results"].setdefault(str(rnd), {})[_result_key(table)] = {
        "a": int(cups_a), "b": int(cups_b), "winner": winner,
        "table": int(table["table"]) if isinstance(table, dict) else int(table)}


def result(state, rnd, table):
    """Stored result of one game, or None."""
    return state["results"].get(str(rnd), {}).get(_result_key(table))


def random_results(state, rnd, games=None):
    """DEMO: generate results for the supplied games or the active round half."""
    cups = state["cfg"]["cups"]
    for game in games if games is not None else active_games(state, rnd, state.get("ring_half", 0)):
        if is_ring_round(state, rnd):
            set_result(state, rnd, game, random.randint(-1, cups + 3), random.randint(-1, cups + 3))
        else:
            loser = random.randint(0, cups - 1)                        # cups hit by the losing duo
            if random.random() < 0.5:
                set_result(state, rnd, game["table"], cups, loser)     # duo a wins
            else:
                set_result(state, rnd, game["table"], loser, cups)     # duo b wins


def ranking(state):
    """Ranking per person (absolute totals): points, cups hit, cup difference; also games and wins."""
    cfg = state["cfg"]
    rows = {p: {"Name": p, "Spiele": 0, "Siege": 0, "Punkte": 0, "Becher": 0, "Gegen": 0} for p in state["players"]}
    for rnd, games in state["results"].items():                        # every entered round
        by_key = {_result_key(g): g for g in state["schedule"][int(rnd)]["games"]}
        for result_key, res in games.items():
            game = by_key.get(result_key)
            if game is None:
                game = next(g for g in state["schedule"][int(rnd)]["games"] if g["table"] == int(result_key))
            for side, other in (("a", "b"), ("b", "a")):               # both duos
                for p in game[side]:                                   # both players of the duo get the same values
                    r = rows[p]
                    r["Spiele"] += 1
                    r["Becher"] += res[side]                           # cups hit by the own duo
                    r["Gegen"] += res[other]                           # cups hit by the opponents
                    if res["winner"] == side:
                        r["Siege"] += 1
                        r["Punkte"] += cfg["points_win"]
                    elif res["winner"] == "draw":
                        r["Punkte"] += cfg.get("points_draw", 1)
    df = pd.DataFrame(rows.values()) #turns the rows dictionary into a pandas DataFrame, which is a tabular data structure that allows for easy manipulation and analysis of the data. Each row in the DataFrame corresponds to a player, and the columns represent the various statistics (games played, wins, points, cups hit, cups against).
    df["Diff"] = df["Becher"] - df["Gegen"]                            # cup difference (last criterion)
    df = df.sort_values(["Punkte", "Becher", "Diff", "Name"], ascending=[False, False, False, True]) # sort by points, cups hit, cup difference, and name (alphabetically)
    df.insert(0, "Rang", range(1, len(df) + 1))                        # 1, 2, 3 ...
    return df[["Rang", "Name", "Spiele", "Siege", "Punkte", "Becher", "Diff"]]


def clock(state):
    """(phase, seconds left) of the current round: ("wait", None) before the start, ("game", s), ("change", s), ("over", 0)."""
    if state["round_started"] is None:                                 # timer not started
        return "wait", None
    cfg = state["cfg"]
    elapsed = time.time() - state["round_started"]                     # seconds since the start of the round
    ring = is_ring_round(state, state.get("current", 0))
    game_seconds = cfg["game_min"] * (30 if ring else 60)
    change_seconds = max(0, cfg["slot_min"] - cfg["game_min"]) * 60
    slot_seconds = game_seconds + change_seconds
    if elapsed < game_seconds:
        return "game", game_seconds - elapsed                           # game running
    if elapsed < slot_seconds:
        return "change", slot_seconds - elapsed                         # change time
    return "over", 0
