# Instructions for GitHub Copilot – OBC Mitgliederevent 2026 (beer pong GUI)

Read `../claude_log/2026_Mitgliederevent_log.md` (full history of what was built and why) before larger changes.

## Project in short
Streamlit app for the beer pong part of the OBC member event. Laptop + TV:
TV page `http://localhost:8501/` (room with tables and duos, next round, clock, ranking) and admin page
`http://localhost:8501/admin` (enter results, timer, next round, parameters). Start from this folder: `../obcvenv/bin/streamlit run app.py`.

Files: `tournament.py` (logic, no GUI), `room.py` (SVG of the room), `app.py` (GUI), `event_state.json` (saved event).

## Rules that must stay
- Regular rounds are always 2 vs 2; duos AND opponents are completely random (never balanced by strength).
- Ring of Fire rounds are on rounds 6 and 13 in a 14-round event. Group the live ranking in fours and pair positions 1+3 against 2+4; 3 players left means 1 vs 2, 2 left means 1 vs 1, and 1 left sits out.
- Split each Ring of Fire event into two halves with the matchup counts as even as possible. Each half is 6 minutes playing + 3 minutes changeover, so each Fire event takes 18 minutes (3 minutes over a regular slot).
- During Ring of Fire only, use the 10-cup pyramid positions without its three corners or center (6 cups per side); enter the final tally including bonus/penalty manually. Win = 3 points, draw = 1 point each, loss = 0.
- Keep regular-round games balanced as before; ranking is points > cups hit > cup difference, and both players of a duo get their duo's totals.
- Flexible parameters: tables, duration, slot (game + change), game time, number of players.
- GUI text in German (Swiss spelling, "ss" instead of "ß"); code comments in English, a comment on every line.
- White background, OBC logo as faint watermark and in the header; colours of the logo
  (purple `#6A3FC9`, amber `#E08600`, green `#7CC800`, ink `#2E1A5E`).

## Technical notes
- SVGs are shown as `<img src="data:image/svg+xml;base64,...">` (st.html filters SVG); SVGs need width/height.
- The default page is served at `/` (not `/tv`).
- Changed names/parameters only take effect for a NEW event (admin sidebar → "Neues Event erstellen").
- Ring of Fire rules also apply to newly created events; preserve schedules/results in an already completed event.
- Use the OBC-root environment: `../obcvenv/bin/pip`, `../obcvenv/bin/python`, `../obcvenv/bin/streamlit`.
- Test headless with `streamlit.testing.v1.AppTest` before saying something works.
