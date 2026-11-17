"""Room view as SVG: the beer pong tables seen from above, with the two duos and (if entered) the score."""
import html                                                            # names with & < > are escaped in the SVG
import math                                                            # grid of the tables

COLS = 3                                                               # tables per row in the room
CELL_W, CELL_H = 400, 260                                              # tighter vertical spacing between room rows
TABLE_W, TABLE_H = 300, 100                                             # the table itself (high enough for 4 cups side by side)
VERTICAL_TABLES = {}                                               # six horizontal tables, then one vertical at each row end
BLUE, ORANGE = "#6A3FC9", "#E08600"                                    # duo a = OBC purple, duo b = amber (readable on white)
INK = "#2E1A5E"                                                        # dark purple of the logo outlines


def _cups(x_end, y_mid, inward, color, empty=False):
    """10 cups as a triangle at one end of the table, as in real beer pong: the row of 4 at the table end, the tip
    (1 cup) towards the opponent. x_end = centre of the back row, inward = +1 (left end, tip points right) or -1."""
    r, gap = 8, 18.5                                                   # cup radius and centre distance (cups nearly touch)
    dx = gap * 0.866                                                   # row distance of a close-packed triangle (sqrt(3)/2)
    out = []
    for row, n in enumerate((4, 3, 2, 1)):                             # back row with 4 cups ... tip with 1 cup
        x = x_end + inward * row * dx                                  # each row one step closer to the middle
        for i in range(n):
            y = y_mid + (i - (n - 1) / 2) * gap                        # cups of one row centred on the table axis
            fill = "none" if empty else color
            stroke = "#90A4AE" if empty else "white"
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="2"/>')
    return "".join(out)

def _ring_of_fire(x_end, y_mid, inward, color, empty=False):
    """Draw the 10-cup pyramid minus its three corner cups and central cup."""
    r, gap = 8, 18.5                                                   # cup radius and centre distance
    dx = gap * 0.866                                                   # spacing between triangle rows
    out = []
    for row, n in enumerate((4, 3, 2, 1)):
        x = x_end + inward * row * dx
        for i in range(n):
            corner = (row == 0 and i in (0, 3)) or row == 3
            center = row == 1 and i == 1
            if corner or center:
                continue
            y = y_mid + (i - (n - 1) / 2) * gap
            fill = "none" if empty else color
            stroke = "#90A4AE" if empty else "white"
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="2"/>')
    return "".join(out)


def _names(duo, x, y, anchor, color):
    """The two names of a duo, one under the other."""
    return "".join(f'<text x="{x}" y="{y + i * 24}" text-anchor="{anchor}" fill="{color}" font-size="28" '
                   f'font-weight="700">{html.escape(p)}</text>' for i, p in enumerate(duo))


def room_svg(n_tables, games, results=None, title=None, ring_of_fire=False):
    """SVG of the room: n_tables tables, games = [{"table", "a", "b"}], results = {table: {"a", "b", "winner"}}."""
    results = results or {}
    by_table = {g["table"]: g for g in games}                          # which game is on which table
    rows = math.ceil(n_tables / COLS)
    width, height = COLS * CELL_W, rows * CELL_H + (40 if title else 0)
    top = 40 if title else 0                                           # room for the title line
    parts = [f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" '
             f'font-family="Inter,Helvetica,Arial,sans-serif">']   # own size: as an <img> it is otherwise only 300 x 150 px
    if title:
        parts.append(f'<text x="8" y="28" fill="{INK}" font-size="24" font-weight="700">{html.escape(title)}</text>')
    for t in range(1, n_tables + 1):                                   # every table of the room
        col, row = (t - 1) % COLS, (t - 1) // COLS #table nr 1 is then at col 0, row 0
        cx, cy = col * CELL_W + CELL_W / 2, top + row * CELL_H + CELL_H / 2    # centre of the table
        x0, y0 = cx - TABLE_W / 2, cy - TABLE_H / 2
        game = by_table.get(t)
        felt = "#7CC800" if game else "#ECEFF1"                        # OBC green = played, light grey = free
        vertical = t in VERTICAL_TABLES
        if vertical:
            parts.append(f'<g transform="rotate(90 {cx} {cy})">')
        parts.append(f'<rect x="{x0}" y="{y0}" width="{TABLE_W}" height="{TABLE_H}" rx="14" fill="{felt}" '
                     f'stroke="{INK if game else "#CFD8DC"}" stroke-width="3"/>')
        parts.append(f'<line x1="{cx}" y1="{y0 + 6}" x2="{cx}" y2="{y0 + TABLE_H - 6}" stroke="white" '
                     f'stroke-opacity="0.35" stroke-width="2"/>')      # middle line
        if vertical:
            parts.append("</g>")
        if not game:                                                   # free table
            if ring_of_fire:
                parts.append(_ring_of_fire(x0 + 14, cy, +1, BLUE, empty=True))
                parts.append(_ring_of_fire(x0 + TABLE_W - 14, cy, -1, ORANGE, empty=True))
            else:
                parts.append(_cups(x0 + 14, cy, +1, BLUE, empty=True))
                parts.append(_cups(x0 + TABLE_W - 14, cy, -1, ORANGE, empty=True))
            parts.append(f'<text x="{cx}" y="{y0 - 12}" text-anchor="middle" fill="#90A4AE" font-size="22">frei</text>')
            parts.append(f'<text x="{cx}" y="{cy + 8}" text-anchor="middle" fill="#90A4AE" font-size="22">'
                         f'Tisch {t}</text>')
            continue
        if vertical:
            parts.append(f'<g transform="rotate(90 {cx} {cy})">')
        if ring_of_fire:
            parts.append(_ring_of_fire(x0 + 14, cy, +1, BLUE))          # Ring rounds omit pyramid corners and centre cups
            parts.append(_ring_of_fire(x0 + TABLE_W - 14, cy, -1, ORANGE))
        else:
            parts.append(_cups(x0 + 14, cy, +1, BLUE))                 # cups of duo a at one end
            parts.append(_cups(x0 + TABLE_W - 14, cy, -1, ORANGE))     # cups of duo b at the other end
        if vertical:
            parts.append("</g>")
            vx0, vy0 = cx - TABLE_H / 2, cy - TABLE_W / 2
            parts.append(_names(game["a"], vx0 + 210, cy - 120, "end", BLUE))
            parts.append(_names(game["b"], vx0 + TABLE_H + 10, cy + 115, "start", ORANGE))
        else:
            parts.append(_names(game["a"], x0, y0 - 34, "start", BLUE))    # duo a above the left half
            parts.append(_names(game["b"], x0 + TABLE_W, y0 - 34, "end", ORANGE))   # duo b above the right half
        res = results.get(t)
        parts.append(f'<circle cx="{cx}" cy="{cy}" r="{18 if res else 19}" fill="{INK}" stroke="white" stroke-width="2"/>')
        if res:
            parts.append(f'<text x="{cx - 38}" y="{cy + 7}" text-anchor="end" fill="{BLUE}" font-size="26" '
                         f'font-weight="800">{res["a"]}</text>') #append the score left
            parts.append(f'<text x="{cx}" y="{cy + 7}" text-anchor="middle" fill="white" font-size="26" '
                            f'font-weight="800">:</text>') #append the colon in the middle
            parts.append(f'<text x="{cx + 38}" y="{cy + 7}" text-anchor="start" fill="{ORANGE}" font-size="26" '
                         f'font-weight="800">{res["b"]}</text>') #append the score right
        else:
            parts.append(f'<text x="{cx}" y="{cy + 7}" text-anchor="middle" fill="white" font-size="20" '
                         f'font-weight="800">{t}</text>') # append the table nr in the middle of the circle if no score is entered yet
        label_y = vy0 + TABLE_W + 26 if vertical else y0 + TABLE_H + 26
        parts.append(f'<text x="{cx}" y="{label_y}" text-anchor="middle" fill="#5E4B8B" font-size="22" font-weight="700">'
                     f'Tisch {t}</text>')                              # label under the table
    parts.append("</svg>")
    return "".join(parts)


NEXT_CARD_W, NEXT_CARD_H, NEXT_CARD_GAP = 220, 110, 15                # one compact matchup card per next-round game
GOLD = "#F2B705"                                                       # outline of the tables of the next round (logo yellow, darker)


def next_room_svg(n_tables, games):
    """One horizontal row of next-round matchup cards, using the existing gold and pale-yellow colors."""
    ordered_games = sorted(games, key=lambda game: game["table"])
    card_count = max(len(ordered_games), 1)
    width = card_count * NEXT_CARD_W + (card_count + 1) * NEXT_CARD_GAP
    height = NEXT_CARD_H + 2.5 * NEXT_CARD_GAP
    parts = [f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" '
             f'font-family="Inter,Helvetica,Arial,sans-serif">']
    if not ordered_games:
        parts.append(f'<text x="{width / 2}" y="{height / 2 + 7}" text-anchor="middle" fill="#90A4AE" '
                     f'font-size="28">Keine Spiele</text>')
    for index, game in enumerate(ordered_games):
        x0 = NEXT_CARD_GAP + index * (NEXT_CARD_W + NEXT_CARD_GAP)
        y0 = NEXT_CARD_GAP
        cx = x0 + NEXT_CARD_W / 2
        parts.append(f'<rect x="{x0}" y="{y0}" width="{NEXT_CARD_W}" height="{NEXT_CARD_H}" rx="12" '
                     f'fill="#FFF8E1" stroke="{GOLD}" stroke-width="3"/>')
        parts.append(f'<text x="{cx}" y="{y0 + 25}" text-anchor="middle" fill="{INK}" '
                     f'font-size="26" font-weight="800">Tisch {game["table"]}</text>') # here we write the table nr
        parts.append(f'<line x1="{cx}" y1="{y0 + 30}" x2="{cx}" y2="{y0 + NEXT_CARD_H - 10}" stroke="{INK}" '
                     f'stroke-opacity="0.2" stroke-width="2"/>') # here we draw a vertical line in the middle of the card
        for side, color, side_x, anchor in (("a", BLUE, x0 + 10, "start"), ("b", ORANGE, x0 + NEXT_CARD_W - 10, "end")): #here we define the two sides of the card, side a and side b, with their respective colors, x positions, and text anchors
            for player_index, player in enumerate(game[side]): # here we write the names of the players on each side of the card
                parts.append(f'<text x="{side_x}" y="{y0 + 58 + player_index * 26}" text-anchor="{anchor}" '
                             f'fill="{color}" font-size="22" font-weight="700">{html.escape(player)}</text>')
    parts.append("</svg>")
    return "".join(parts)
