# OBC Mitgliederevent 2026 – Beer Pong

Streamlit app that ran the beer pong tournament of the OBC Mitgliederevent on 21/22 November 2026:
TV view with the room, the clock, the next round and the ranking; admin page to enter results; phone page for everyone.

**The event went great – thanks to everyone who played!** 🍺🏓

## Final format (as played)
- 35 players, 7 tables (Clubhuus: tables 1–5, Garderobe: tables 6–7), 10 cups per side
- 7 Vorrunden: 5 regular rounds (2 vs 2, random duos and opponents, 7 players sit out once) and
  2 Ring of Fire rounds (rank-based groups) – everyone played 6 games
- Ranking per person: points (win 3, Ring of Fire draw 1), then cups hit, then cup difference
- KO phase: Zwischen-KO (places 9–24), Viertelfinale (places 1–8 + winners), Halbfinale, Finale with randomly
  mixed duos (one player of each semifinal winner) and a game for places 3/4 (same mixing)

## Run
```bash
cd 2026_Mitgliederevent
../obcvenv/bin/pip install -r requirments.txt     # once (streamlit, pandas)
./start_public.sh                                 # app + public Cloudflare link (phone / TV / admin), Ctrl+C stops
```
Local only: `../obcvenv/bin/streamlit run app.py` → TV `http://localhost:8501/`, admin `/admin`, phone `/phone`.
The admin password is read from `.streamlit/secrets.toml` (`admin_password = "..."`, not in git).

## Files
| File | Content |
|---|---|
| `tournament.py` | tournament logic: schedule, results, ranking, Ring of Fire, KO bracket, state file |
| `room.py` | SVG drawings: room with the tables, next round, KO tree |
| `app.py` | Streamlit pages: TV, admin, phone |
| `player_info.py` | terminal overview of one player (games, partners, results) |
| `start_public.sh` | starts the app and a free Cloudflare quick tunnel (new link at every start) |

`event_state.json` (the live event) and `event_backups/` (automatic copies after every change) are not in git.
