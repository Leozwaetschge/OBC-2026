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
STATE_FILE = os.path.join(FOLDER, "event_state.json")
BACKUP_DIR = os.path.join(FOLDER, "event_backups")                     # 19 Nov: copies of the state (newest 50)                  # everything of the event (survives a restart)

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


KO_ROUND_COUNT = 4  # intermediate KO, quarterfinal, semifinal, final


def n_rounds(cfg):
    """Number of preliminary rounds after reserving four slots for the KO phase."""
    total_slots = math.floor(cfg["duration_min"] / cfg["slot_min"])
    return max(0, total_slots - KO_ROUND_COUNT)


def ring_round_indices(rounds):
    """Zero-based Ring of Fire rounds: the middle round and the second-to-last round."""
    if rounds < 4:
        return []
    middle_round = math.ceil((rounds - 2) / 2)
    return sorted({max(1, middle_round - 1), rounds - 2})             # 19 Nov: never the first round


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
    max_rounds = n_rounds(cfg)                                         # rounds that fit in the time, e.g. 8
    fire = len(ring_round_indices(max_rounds))                         # Ring of Fire rounds planned (everyone plays once)
    parts = ring_parts(len(players), cfg["tables"])                    # 19 Nov: parts of one Ring round (2 = two halves)
    fire_slots = math.ceil(parts / 2)                                  # time slots of one Ring round (2 parts per slot)
    options = []                                                       # 19 Nov: 2, 1 or 0 Ring rounds -> the most games per person
    for f in range(fire, -1, -1):                                      # (e.g. 42 players on 5 tables: the Ring parts eat the
        budget = max_rounds - f * fire_slots                           # time, 0 regular games would remain)
        if budget >= 0:
            g_f = _regular_games_per_player(len(players), cfg["tables"], budget)
            options.append((g_f + f, g_f > 0, f, g_f))                 # most games in total; at a tie: with regular games,
    _, _, fire, _ = max(options)                                       # then more Ring rounds
    regular_g = _regular_games_per_player(len(players), cfg["tables"], max_rounds - fire * fire_slots)   # FIXED POINT: equal games for
    total = len(players) * regular_g // 4                              # all, as many as fit in the time; games in total
    usable = min(cfg["tables"], len(players) // 4)                     # tables per round at most
    regular_rounds = math.ceil(total / usable) if usable else 0        # 19 Nov: only as many rounds as needed -> shorter
    per_round = [min(usable, total - r * usable) for r in range(regular_rounds)]   # full rounds, the last one may be smaller:
                                                                       # never an empty round
    rounds = regular_rounds + fire                                     # rounds really played
    ring_indices = ring_round_indices(rounds)[-fire:] if fire else []  # fewer Ring rounds -> the later one is kept
    if len(ring_indices) < fire or (fire and regular_rounds == 0):     # Ring rounds do not fit any more -> without them
        rounds, ring_indices, fire = regular_rounds, [], 0            # (everyone still plays the same number of games)
    played = {p: 0 for p in players}                                   # games per player so far
    schedule = []
    regular_index = 0
    for round_index in range(rounds):                                  # one round
        if round_index in ring_indices:
            schedule.append({"kind": "ring", "games": [], "halves": [[] for _ in range(parts)], "pause": [],
                             "prepared": False})                       # one list of games per part
            for player in players:
                played[player] += 1
            continue
        k = per_round[regular_index]
        regular_index += 1
        order = sorted(players, key=lambda p: (played[p], rng.random()))   # fewest games first, random among equals
        # first sorts by the number of games played, then randomly among those with the same number of games played
        on = order[:4 * k]                                             # the 4k players of this round
        rng.shuffle(on)                                                # random duos and random opponents
        games = [{"table": i + 1, "a": on[4 * i:4 * i + 2], "b": on[4 * i + 2:4 * i + 4]}   # duo a vs duo b
                 for i in range(k)]                                    # 19 Nov: tables 1 ... k, unused = the highest numbers
        for p in on:
            played[p] += 1                                             # count the game
        schedule.append({"kind": "regular", "games": games, "pause": sorted(order[4 * k:])})   # the rest sits out this round
    return schedule, regular_g + len(ring_indices)


def schedule_size(n_players, cfg):
    """(rounds really played, games per player) of the preliminary phase, as build_schedule makes it (admin preview)."""
    schedule, g = build_schedule([f"p{i}" for i in range(n_players)], cfg)
    return len(schedule), g


def ring_parts(n_players, tables):
    """19 Nov: parts of a Ring of Fire round: everyone plays once (groups of 4, a rest of 2-3 is one game), in at least
    two halves, more parts if the tables are not enough, e.g. 40 players (10 games) on 3 tables -> 4 parts."""
    games = n_players // 4 + (1 if n_players % 4 >= 2 else 0)        # games of one Ring round
    return max(min(2, games), math.ceil(games / max(1, tables)))   # 1 game -> 1 part (never an empty part)


def ring_part_count(state, rnd):
    """Number of parts of Ring round rnd (2 for normal rounds and old events)."""
    return max(1, len(state["schedule"][rnd].get("halves", []))) if is_ring_round(state, rnd) else 2


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
    groups = [ranked_players[s:s + 4] for s in range(0, len(ranked_players), 4)]   # groups of 4 by ranking
    if len(groups) > 1 and len(groups[-1]) == 1:                       # 19 Nov: a single rest player joins the last group
        rest = groups.pop()                                            # (2 vs 3) -> nobody sits out, all play equally often
        groups[-1] += rest
    for group in groups:
        if len(group) == 5:                                            # the merged group: 2 vs 3
            side_a, side_b = [group[0], group[2]], [group[1], group[3], group[4]]
        elif len(group) == 4:
            side_a, side_b = [group[0], group[2]], [group[1], group[3]]
        elif len(group) == 3:
            side_a, side_b = [group[0]], group[1:]
        elif len(group) == 2:
            side_a, side_b = group[:1], group[1:]
        else:
            pause.extend(group)
            continue
        games.append({"a": side_a, "b": side_b})
    parts = max(min(2, len(games)), math.ceil(len(games) / max(1, int(state["cfg"]["tables"]))))   # 19 Nov: as many parts
    parts = max(1, parts)                                              # as the tables need, never an empty part
    per = max(1, math.ceil(len(games) / parts))                        # games per part (never more than the tables)
    round_data["halves"] = [[] for _ in range(parts)]
    for index, game in enumerate(games):
        half = index // per                                            # part of this game
        table = index % per + 1                                        # tables 1 ... per in every part
        game.update({"id": f"ring-{rnd}-{index}", "half": half, "table": table})
        round_data["halves"][half].append(game)
    round_data["games"] = games
    round_data["pause"] = pause
    round_data["prepared"] = True
    return True


def active_games(state, rnd, half=0):
    """Games displayed and scored for a normal round or one Ring of Fire half."""
    if is_ring_round(state, rnd):
        halves = state["schedule"][rnd].get("halves", [[], []])
        return halves[half] if half < len(halves) else []
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
    for attempt in range(5):                                           # 19 Nov: a broken read (e.g. old file) -> try again shortly
        try:
            with open(STATE_FILE) as f:
                state = json.load(f)
            break
        except json.JSONDecodeError:
            if attempt == 4:                                           # still broken: keep it for a look and continue
                os.replace(STATE_FILE, STATE_FILE + ".broken")         # from the newest readable backup (else a new event)
                for name in sorted(os.listdir(BACKUP_DIR), reverse=True) if os.path.isdir(BACKUP_DIR) else []:
                    try:
                        with open(os.path.join(BACKUP_DIR, name)) as f:
                            state = json.load(f)
                        save(state)
                        return load()
                    except (json.JSONDecodeError, OSError):
                        continue
                state = new_event()
                save(state)
                return state
            time.sleep(0.2)
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
    import tempfile                                                    # 19 Nov: own temp file per write: TV, phone and admin
    fd, tmp = tempfile.mkstemp(dir=FOLDER, prefix=".event_state_", suffix=".tmp")   # save at the same time; one shared
    with os.fdopen(fd, "w") as f:                                      # .tmp name let two writers mix their text (broken JSON)
        json.dump(state, f, indent=1, ensure_ascii=False)
    os.replace(tmp, STATE_FILE)                                        # atomic: readers see the old or the new file, never half
    os.makedirs(BACKUP_DIR, exist_ok=True)                             # 19 Nov: a copy per save, the newest 50 are kept
    stamp = time.strftime("%Y%m%d_%H%M%S") + f"_{int(time.time() * 1000) % 1000:03d}"
    with open(os.path.join(BACKUP_DIR, f"event_state_{stamp}.json"), "w") as f:
        json.dump(state, f, indent=1, ensure_ascii=False)
    for old in sorted(os.listdir(BACKUP_DIR))[:-50]:                   # older copies removed
        try:
            os.remove(os.path.join(BACKUP_DIR, old))
        except OSError:                                                # removed by a parallel save already
            pass


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


# ---------------------------------------------------------------- knockout phase
KO_STAGE_ORDER = ["intermediate", "quarterfinal", "semifinal", "final"]
KO_STAGE_LABELS = {
    "intermediate": "Zwischen-KO",
    "quarterfinal": "Viertelfinale",
    "semifinal": "Halbfinale",
    "final": "Finale",
}


def _ko_game(game_id, table, side_a, side_b, label):
    return {"id": game_id, "table": table, "a": list(side_a), "b": list(side_b), "label": label}


def start_knockout(state):
    """Freeze the league ranking and create the 9–24 intermediate knockout draw.

    Ranks 9–16 are each paired with one randomly drawn player from ranks 17–24.
    The resulting duos are seeded by their best-ranked member and drawn best-vs-worst.
    """
    if state.get("ko"):
        return state["ko"]
    ranked = ranking(state)["Name"].tolist()
    if len(ranked) < 24:
        state["ko"] = {"unavailable": True, "reason": "Für die KO-Phase werden mindestens 24 Spieler benötigt."}
        return state["ko"]

    rank_by_name = {name: index + 1 for index, name in enumerate(ranked)} #creates a dictiornary to link name and place
    upper = ranked[8:16]                                               # places 9–16
    lower = ranked[16:24]      # places 17–24
    rng = random.Random(int(state["cfg"].get("seed", 0)) + 91024)
    # 19 Nov: the best free upper player (9, 10, ...) gets a random partner from the rest of 9-16; the worst free lower
    # player (24, 23, ...) a random partner from the rest of 17-24; these two duos play each other, until 4 games
    up, low = upper[:], lower[:]                                       # still without a duo (in ranking order)
    paired, intermediate_games = [], []
    for i in range(4):
        lead_up = up.pop(0)                                            # best upper player still free
        mate_up = up.pop(rng.randrange(len(up)))                       # random partner from the upper half
        lead_low = low.pop()                                           # worst lower player still free
        mate_low = low.pop(rng.randrange(len(low)))                    # random partner from the lower half
        duo_up, duo_low = [lead_up, mate_up], [lead_low, mate_low]
        paired += [duo_up, duo_low]
        intermediate_games.append(_ko_game(
            f"ko-inter-{i + 1}", i + 1, duo_up, duo_low, f"Zwischen-KO {i + 1}"))

    state["ko"] = {
        "unavailable": False,
        "stage": "intermediate",
        "ranked_players": ranked,
        "rank_by_name": rank_by_name,
        "direct_qualifiers": ranked[:8],
        "intermediate_pairs": paired,
        "stages": {"intermediate": {"games": intermediate_games}},
        "results": {},
        "champion": None,
    }
    return state["ko"]


def knockout_games(state):
    """Games for the currently active knockout stage (empty before KO starts/after final)."""
    ko = state.get("ko")
    if not ko or ko.get("unavailable") or not ko.get("stage"):
        return []
    return ko.get("stages", {}).get(ko["stage"], {}).get("games", [])


def knockout_result(state, game_id):
    return state.get("ko", {}).get("results", {}).get(game_id)


def _knockout_winner(state, game):
    res = knockout_result(state, game["id"])
    if not res:
        return None
    return game[res["winner"]]


def _build_quarterfinals(state):
    ko = state["ko"]
    rank = ko["rank_by_name"]
    intermediate = ko["stages"]["intermediate"]["games"]
    winners = []
    for game in intermediate:
        winning_duo = _knockout_winner(state, game)
        if not winning_duo:
            return False
        winners.extend(winning_duo)

    # Randomly partner the direct qualifiers with the intermediate winners.
    # A dedicated seeded RNG keeps the draw reproducible.
    qualifiers = ko["direct_qualifiers"][:]                            # 19 Nov: places 1-8 stay in ranking order (seeding),
    rng = random.Random(int(state["cfg"].get("seed", 0)) + 82008)      # only their partners are drawn
    rng.shuffle(winners)
    qf_teams = [[qualifiers[i], winners[i]] for i in range(8)]

    # Teams are drawn at random, so the bracket order only fixes who meets whom: team 1 vs 8, 4 vs 5, 2 vs 7, 3 vs 6
    games = [
        _ko_game("ko-qf-1", 1, qf_teams[0], qf_teams[7], "Viertelfinale 1"),
        _ko_game("ko-qf-2", 2, qf_teams[3], qf_teams[4], "Viertelfinale 2"),
        _ko_game("ko-qf-3", 3, qf_teams[1], qf_teams[6], "Viertelfinale 3"),
        _ko_game("ko-qf-4", 4, qf_teams[2], qf_teams[5], "Viertelfinale 4"),
    ]
    ko["quarterfinal_teams"] = qf_teams
    ko["stages"]["quarterfinal"] = {"games": games}
    return True


def _build_semifinals(state):
    ko = state["ko"]
    games = ko["stages"]["quarterfinal"]["games"]
    winners = [_knockout_winner(state, game) for game in games]
    if any(w is None for w in winners):
        return False
    ko["stages"]["semifinal"] = {"games": [
        _ko_game("ko-sf-1", 1, winners[0], winners[1], "Halbfinale 1"),
        _ko_game("ko-sf-2", 2, winners[2], winners[3], "Halbfinale 2"),
    ]}
    return True


def _build_final(state):
    ko = state["ko"]
    games = ko["stages"]["semifinal"]["games"]
    winners = [_knockout_winner(state, game) for game in games]
    if any(w is None for w in winners):
        return False
    duo1, duo2 = list(winners[0]), list(winners[1])                    # 22 Nov: the two semifinal-winning duos
    random.shuffle(duo2)                                               # random order of the second duo's players
    losers = [game["b" if knockout_result(state, game["id"])["winner"] == "a" else "a"] for game in games]   # semi losers
    low1, low2 = list(losers[0]), list(losers[1])                      # 22 Nov: the two semifinal-losing duos
    random.shuffle(low2)                                               # mixed like the final: random partner from the other duo
    ko["stages"]["final"] = {"games": [                                # always mixed: each new duo = one player of each winner
        _ko_game("ko-final", 1, [duo1[0], duo2[0]], [duo1[1], duo2[1]], "Finale"),   # random partner from the other duo
        _ko_game("ko-third", 2, [low1[0], low2[0]], [low1[1], low2[1]], "Spiel um Platz 3"),   # 22 Nov: places 3 and 4
    ]}
    return True


def set_knockout_result(state, game_id, cups_a, cups_b, winner=None):
    """Save a KO result and materialise the next bracket stage once all games finish."""
    ko = state.get("ko")
    if not ko or ko.get("unavailable") or not ko.get("stage"):
        raise ValueError("Die KO-Phase ist nicht aktiv.")
    games = ko["stages"][ko["stage"]]["games"]
    game = next((g for g in games if g["id"] == game_id), None)
    if game is None:
        raise KeyError(f"Unbekanntes KO-Spiel: {game_id}")
    if winner is None:
        winner = "a" if cups_a > cups_b else "b" if cups_b > cups_a else "draw"
    if winner == "draw":
        raise ValueError("Ein KO-Spiel braucht bei Gleichstand einen Sieger.")
    ko["results"][game_id] = {"a": int(cups_a), "b": int(cups_b), "winner": winner}
    return ko


def knockout_stage_complete(state):
    """True if every game of the running KO stage has a result (then "Nächste Runde" may continue)."""
    ko = state.get("ko") or {}
    if ko.get("unavailable") or not ko.get("stage"):
        return False
    return all(g["id"] in ko["results"] for g in ko["stages"][ko["stage"]]["games"])


def advance_knockout(state):
    """19 Nov: "Nächste Runde" in the KO phase: draw the next stage (or crown the champion after the final)."""
    ko = state["ko"]
    games = ko["stages"][ko["stage"]]["games"]
    if knockout_stage_complete(state):
        stage = ko["stage"]
        if stage == "intermediate":
            _build_quarterfinals(state)
            ko["stage"] = "quarterfinal"
        elif stage == "quarterfinal":
            _build_semifinals(state)
            ko["stage"] = "semifinal"
        elif stage == "semifinal":
            _build_final(state)
            ko["stage"] = "final"
        elif stage == "final":
            final_game = games[0]
            final_winner = ko["results"][final_game["id"]]["winner"]
            ko["champion"] = list(final_game[final_winner])
            ko["stage"] = None
    return ko


def knockout_bracket(state):
    """Return all created bracket stages with their current results for display."""
    ko = state.get("ko")
    if not ko or ko.get("unavailable"):
        return []
    output = []
    for stage in KO_STAGE_ORDER:
        data = ko.get("stages", {}).get(stage)
        if not data:
            continue
        rows = []
        for game in data["games"]:
            res = ko.get("results", {}).get(game["id"])
            rows.append({"id": game["id"], "label": game["label"], "a": game["a"], "b": game["b"], "result": res})
        output.append({"stage": stage, "label": KO_STAGE_LABELS[stage], "games": rows})
    return output
