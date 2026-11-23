"""All information of one player in the terminal: rank, games, wins, points, cups and every single game.
Run in the app folder (reads event_state.json, changes nothing):
    ../obcvenv/bin/python player_info.py "Spieler 1"
    cd ~/Documents/OBC/2026_Mitgliederevent && ../obcvenv/bin/python player_info.py "Spieler 1"
Part of a name is enough (e.g. "spieler 1"); without a name: list of all players."""
import sys                                                             # name from the command line

import tournament as T                                                 # state file and ranking of the app


def games_of(state, name):
    """Every entered group game of `name`: (round, table text, partner, opponents, own cups, their cups, outcome, points)."""
    cfg = state["cfg"]                                                 # points per win / draw
    out = []                                                           # one entry per game
    for rnd, results in sorted(state["results"].items(), key=lambda x: int(x[0])):   # rounds in order
        schedule = state["schedule"][int(rnd)]                         # games of this round
        by_key = {T._result_key(g): g for g in schedule["games"]}      # same lookup as T.ranking
        for key, res in results.items():                               # every entered result
            game = by_key.get(key) or next((g for g in schedule["games"] if g["table"] == int(key)), None)
            if game is None:                                           # result without a game (should not happen)
                continue
            for side, other in (("a", "b"), ("b", "a")):               # which duo is the player in?
                if name in game[side]:
                    partner = [p for p in game[side] if p != name]     # team mates (Ring: 0-2)
                    if res["winner"] == side:                          # win
                        outcome, points = "Sieg", cfg["points_win"]
                    elif res["winner"] == "draw":                      # Ring of Fire draw
                        outcome, points = "Unentschieden", cfg.get("points_draw", 1)
                    else:                                              # loss
                        outcome, points = "Niederlage", 0
                    where = (f"RoF Teil {game.get('half', 0) + 1}, Tisch {game['table']}" if schedule.get("kind") == "ring"
                             else f"Tisch {game['table']}")            # Ring of Fire or normal table
                    out.append((int(rnd) + 1, where, partner, game[other], res[side], res[other], outcome, points))
    return out


def ko_games_of(state, name):
    """Every KO game of `name`: (stage, partner, opponents, own cups, their cups, outcome or 'offen')."""
    ko = state.get("ko") or {}                                         # no KO yet -> nothing
    out = []
    for stage in T.KO_STAGE_ORDER:                                     # Zwischen-KO ... Finale
        for game in ko.get("stages", {}).get(stage, {}).get("games", []):
            for side, other in (("a", "b"), ("b", "a")):
                if name in game[side]:
                    res = ko.get("results", {}).get(game["id"])        # None = not played yet
                    partner = [p for p in game[side] if p != name]
                    if res:
                        outcome = "Sieg" if res["winner"] == side else "Niederlage"
                        out.append((T.KO_STAGE_LABELS[stage], partner, game[other], res[side], res[other], outcome))
                    else:
                        out.append((T.KO_STAGE_LABELS[stage], partner, game[other], "-", "-", "offen"))
    return out


def main():
    state = T.load()                                                   # the current event (same file as the app)
    players = state["players"]                                         # all names
    if len(sys.argv) < 2:                                              # no name given -> list the names
        print("Name angeben, z.B.: ../obcvenv/bin/python player_info.py "Spieler 1"\nSpieler:", ", ".join(sorted(players)))
        return
    query = " ".join(sys.argv[1:]).lower()                             # e.g. "sar"
    hits = [p for p in players if p.lower() == query] or [p for p in players if query in p.lower()]   # exact, else part
    if len(hits) != 1:                                                 # none or several -> say which
        print(f"'{query}': " + (f"mehrere Treffer: {', '.join(hits)}" if hits else "kein Spieler gefunden"))
        return
    name = hits[0]
    row = T.ranking(state).set_index("Name").loc[name]                 # rank, games, wins, points, cups, diff
    games = games_of(state, name)
    losses = sum(g[6] == "Niederlage" for g in games)                  # counted from the games
    draws = sum(g[6] == "Unentschieden" for g in games)
    against = sum(g[5] for g in games)                                 # cups of the opponents
    print(f"\n=== {name} ===")
    print(f"Rang {row['Rang']} von {len(players)} | Punkte {row['Punkte']} | Spiele {row['Spiele']}: "
          f"{row['Siege']} Siege, {draws} Unentschieden, {losses} Niederlagen")
    print(f"Becher: getroffen {row['Becher']}, kassiert {against}, Differenz {row['Diff']:+d}")
    if games:
        print(f"Schnitt pro Spiel: {row['Becher'] / len(games):.1f} getroffen, {against / len(games):.1f} kassiert")
    print("\nVorrunde:")
    for rnd, where, partner, opp, own, their, outcome, pts in games:   # one line per game
        print(f"  Runde {rnd:2d} | {where:<18} | mit {' & '.join(partner) or '-':<18} | gegen {' & '.join(opp):<24} | "
              f"{own:2d} : {their:<2d} | {outcome} (+{pts})")
    if not games:
        print("  noch keine Resultate")
    ko = ko_games_of(state, name)
    if ko:                                                             # only if the player is in the KO phase
        print("\nKO-Phase:")
        for stage, partner, opp, own, their, outcome in ko:
            print(f"  {stage:<14} | mit {' & '.join(partner):<18} | gegen {' & '.join(opp):<24} | {own} : {their} | {outcome}")
    elif state.get("ko") and not state["ko"].get("unavailable"):       # KO started without this player
        print("\nKO-Phase: nicht qualifiziert")
    if (state.get("ko") or {}).get("champion") and name in state["ko"]["champion"]:
        print("\n🏆 Turniersieger!")


if __name__ == "__main__":
    main()
