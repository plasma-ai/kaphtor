"""The names section's map of Crete: `guide/crete.svg`, a dot for each name at each find site, and `guide/map`, the
page that shows it with a table of the sites.

A dot is one name at one site, in the colour of its language layer; a name found at two sites has a dot at each. The
dots of a site form one cluster. Clusters that would overlap are parted, the smaller giving way, and a line ties a
moved cluster to its site. Sites off Crete, and finds on Crete with no site on record, are listed under the map.

Coastline: Natural Earth, 1:10m land (public domain), in `crete_coast.json` as rings of [longitude, latitude].
Site positions: Pleiades, except those in APPROX, which are placed by hand. Palaikastro is Roussolakkos and Kophinas
the peak; Pyrgos is set a little north of Myrtos-Pyrgos, so the coarse coastline keeps it on land. A site the map
does not know stops the build.
"""
from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from pathlib import Path

from .markdown import escape as esc
from .markdown import table
from .names import GUIDE, KINDS, LAYERS, Names, _page, aff

COAST = Path(__file__).with_name("crete_coast.json")
IMAGE = "crete.svg"
# (latitude, longitude)
SITES = {
    "Haghia Triada": (35.059, 24.793), "Phaistos": (35.051, 24.814), "Kamilari": (35.045, 24.787),
    "Platanos": (35.020, 24.930), "Kophinas": (34.9615, 25.0796), "Khania": (35.516, 24.019),
    "Nerokurou": (35.480, 24.040), "Knossos": (35.298, 25.163), "Poros Herakleiou": (35.340, 25.150),
    "Prassa": (35.320, 25.190), "Tylissos": (35.299, 25.020), "Arkhanes": (35.236, 25.160),
    "Troullos": (35.240, 25.166), "Iouktas": (35.240, 25.142), "Skoteino Cave": (35.300, 25.300),
    "Malia": (35.293, 25.492), "Kardamoutsa": (35.207, 25.458), "Papourou": (35.211, 25.471),
    "Inatos": (34.988, 25.284), "Syme": (35.056, 25.500), "Pyrgos": (35.014, 25.590), "Gournia": (35.109, 25.793),
    "Mokhlos": (35.183, 25.904), "Petras": (35.197, 26.115), "Palaikastro": (35.1953, 26.2756),
    "Zakros": (35.098, 26.261),
}
APPROX = {"Platanos", "Nerokurou", "Poros Herakleiou", "Prassa", "Troullos", "Iouktas", "Skoteino Cave", "Pyrgos"}
SAME = {"Kophinas (?)": "Kophinas"}   # a doubtful attribution is drawn at the site it is attributed to
OFF_CRETE = {"Lachish", "Miletos", "Samothrace", "Thera", "Troy"}
NO_SITE = "Crete"   # a find on Crete with no site on record
COLORS = {"semitic": "#e8e4dc", "hurrian": "#87bfab", "egyptian": "#d69897", "aegean": "#89afd6",
          "anatolian": "#b499c1", "indo_european": "#aebf92", "sumerian": "#d5a77b", "unknown": "#77777c"}
W, H, PAD, TOP = 900, 452, 26, 58
LON0, LON1, LAT1 = 23.45, 26.40, 35.72
SCALE = (W - 2 * PAD) / ((LON1 - LON0) * math.cos(math.radians(35.25)))
STEP = 5.6 * 0.62   # a cluster's spread: a dot sits STEP·√(i + ½) from its centre
GOLDEN = math.pi * (3 - math.sqrt(5))


def xy(lat: float, lon: float) -> tuple[float, float]:
    return PAD + (lon - LON0) * math.cos(math.radians(35.25)) * SCALE, TOP + (LAT1 - lat) * SCALE


def by_site(names: Names) -> dict[str, list[dict]]:
    """Site -> the names found there, in the record's order; ValueError for a site the map has no place for."""
    at: dict[str, list[dict]] = defaultdict(list)
    for n in names.names:
        for site in dict.fromkeys(SAME.get(s, s) for s in n.get("sites") or []):
            at[site].append(n)
    unknown = sorted(set(at) - set(SITES) - OFF_CRETE - {NO_SITE})
    if unknown:
        raise ValueError(f"no place on the names map for: {', '.join(unknown)} (add each to SITES or OFF_CRETE)")
    return dict(at)


def clusters(at: dict[str, list[dict]]) -> list[dict]:
    """One cluster per site on the map, the largest first, each moved off any it would overlap and drawn back
    toward its site."""
    out = []
    for site in sorted(s for s in at if s in SITES):
        sx, sy = xy(*SITES[site])
        out.append({"site": site, "names": at[site], "sx": sx, "sy": sy, "x": sx, "y": sy,
                    "r": max(7.0, STEP * math.sqrt(len(at[site])) + 4)})
    out.sort(key=lambda c: (-len(c["names"]), c["site"]))
    for _ in range(400):
        for i, a in enumerate(out):
            for b in out[i + 1:]:
                dx, dy = b["x"] - a["x"], b["y"] - a["y"]
                d = math.hypot(dx, dy) or 0.01
                overlap = a["r"] + b["r"] + 10 - d
                if overlap > 0:
                    share = b["r"] ** 2 / (a["r"] ** 2 + b["r"] ** 2)   # the smaller cluster moves further
                    a["x"] -= dx / d * overlap * 0.5 * share
                    a["y"] -= dy / d * overlap * 0.5 * share
                    b["x"] += dx / d * overlap * 0.5 * (1 - share)
                    b["y"] += dy / d * overlap * 0.5 * (1 - share)
        for c in out:
            c["x"] += (c["sx"] - c["x"]) * 0.02
            c["y"] += (c["sy"] - c["y"]) * 0.02
            c["x"] = min(W - PAD - c["r"], max(PAD + c["r"], c["x"]))
            c["y"] = min(H - 62 - c["r"], max(TOP - 30 + c["r"], c["y"]))
    return out


def _labels(found: list[dict]) -> list[str]:
    """A label for each site with three names or more, at the first free place of above, below, right and left; the
    large sites choose first."""
    placed: list[tuple[float, float, float, float]] = []
    out = []

    def free(box: tuple[float, float, float, float], own: dict) -> bool:
        x0, y0, x1, y1 = box
        if x0 < 4 or x1 > W - 4 or y0 < 4 or y1 > H - 44:
            return False
        for other in found:
            if other is own:
                continue
            nx, ny = min(max(other["x"], x0), x1), min(max(other["y"], y0), y1)
            if math.hypot(other["x"] - nx, other["y"] - ny) < other["r"] - 1:
                return False
        return all(x1 < a or x0 > c or y1 < b or y0 > d for a, b, c, d in placed)

    for c in found:
        count = len(c["names"])
        if count < 3:
            continue
        big = count >= 4
        size = 15 if big else 12.5
        width, r = len(f"{c['site']} {count}") * size * 0.56, c["r"]
        options = [(c["x"], c["y"] - r - 5, "middle"), (c["x"], c["y"] + r + size + 2, "middle"),
                   (c["x"] + r + 5, c["y"] + size * 0.35, "start"), (c["x"] - r - 5, c["y"] + size * 0.35, "end"),
                   (c["x"] + r * 0.7 + 4, c["y"] - r * 0.7 - 3, "start"), (c["x"] - r * 0.7 - 4, c["y"] - r * 0.7 - 3, "end"),
                   (c["x"] + r * 0.7 + 4, c["y"] + r * 0.7 + size, "start"),
                   (c["x"] - r * 0.7 - 4, c["y"] + r * 0.7 + size, "end")]

        def box(x: float, y: float, anchor: str, width: float = width, size: float = size) -> tuple[float, ...]:
            x0 = x - width / 2 if anchor == "middle" else x if anchor == "start" else x - width
            return x0 - 2, y - size, x0 + width + 2, y + 3

        x, y, anchor = next((o for o in options if free(box(*o), c)), options[0])
        placed.append(box(x, y, anchor))
        out.append(f'<text x="{x:.1f}" y="{y:.1f}" fill="#ffffff" fill-opacity="{0.92 if big else 0.66}" '
                   'stroke="#0f1012" stroke-width="3" stroke-opacity="0.85" paint-order="stroke" '
                   f'stroke-linejoin="round" font-size="{size}" font-weight="{500 if big else 400}" '
                   f'text-anchor="{anchor}">{esc(c["site"])} <tspan fill-opacity="0.55">{count}</tspan></text>')
    return out


def svg(names: Names) -> str:
    """The map, on its own dark ground so it reads on any page."""
    found = clusters(by_site(names))
    order = list(COLORS)
    out = [(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
            'font-family="Inter, ui-sans-serif, system-ui, sans-serif">'),
           "<title>The names of the Linear A inscriptions on Crete, by find site</title>",
           f'<rect width="{W}" height="{H}" rx="8" fill="#0f1012"/>']
    for ring in json.loads(COAST.read_text(encoding="utf-8")):
        points = " ".join(f"{x:.1f},{y:.1f}" for x, y in (xy(lat, lon) for lon, lat in ring))
        out.append(f'<polygon points="{points}" fill="#ffffff" fill-opacity="0.045" stroke="#ffffff" '
                   'stroke-opacity="0.38" stroke-width="1" stroke-linejoin="round"/>')
    for label, lat, lon in (("Sea of Crete", 35.66, 25.05), ("Libyan Sea", 34.86, 24.35)):
        x, y = xy(lat, lon)
        out.append(f'<text x="{x:.0f}" y="{y:.0f}" fill="#ffffff" fill-opacity="0.28" font-size="13" '
                   f'font-style="italic" letter-spacing="2" text-anchor="middle">{label}</text>')
    for c in found:   # the lines first, so the dots sit over them
        if math.hypot(c["x"] - c["sx"], c["y"] - c["sy"]) > 3:
            out.append(f'<line x1="{c["sx"]:.1f}" y1="{c["sy"]:.1f}" x2="{c["x"]:.1f}" y2="{c["y"]:.1f}" '
                       'stroke="#ffffff" stroke-opacity="0.3" stroke-width="0.8"/>')
        out.append(f'<circle cx="{c["sx"]:.1f}" cy="{c["sy"]:.1f}" r="2.2" fill="none" stroke="#ffffff" '
                   'stroke-opacity="0.7" stroke-width="1"/>')
    for c in found:
        group = sorted(c["names"], key=lambda n: (order.index(aff(n)), n["token"]))
        for i, n in enumerate(group):
            r, t = STEP * math.sqrt(i + 0.5), i * GOLDEN
            out.append(f'<circle cx="{c["x"] + r * math.cos(t):.1f}" cy="{c["y"] + r * math.sin(t):.1f}" r="2.1" '
                       f'fill="{COLORS[aff(n)]}"/>')
    out += _labels(found)
    x, y = PAD, H - 16
    layers = Counter(aff(n) for n in names.names)
    for key in order:
        if not layers[key]:
            continue
        label = f"{LAYERS[key][1]} {layers[key]}"
        out.append(f'<circle cx="{x + 4}" cy="{y - 4}" r="4" fill="{COLORS[key]}"/>')
        out.append(f'<text x="{x + 14}" y="{y}" fill="#ffffff" fill-opacity="0.8" font-size="13">{label}</text>')
        x += 24 + 7.3 * len(label)
    return "\n".join([*out, "</svg>", ""])


def page(names: Names) -> tuple[str, str]:
    at = by_site(names)
    found = clusters(at)
    rows = []
    for c in found:
        layers = Counter(LAYERS[aff(n)][1] for n in c["names"])
        kinds = Counter(KINDS[n["type"]][2] for n in c["names"])
        shown = sorted(c["names"], key=lambda n: (-n.get("frequency", 0), n["token"]))[:8]
        more = len(c["names"]) - len(shown)
        rows.append([esc(c["site"]) + (" (approx.)" if c["site"] in APPROX else ""), str(len(c["names"])),
                     ", ".join(f"{layer} {k}" for layer, k in layers.most_common()),
                     ", ".join(f"{kind} {k}" for kind, k in kinds.most_common()),
                     ", ".join(names.link(n) for n in shown) + (f" and {more} more" if more > 0 else "")])
    away = [[esc(site), str(len(at[site])), ", ".join(names.link(n) for n in at[site])]
            for site in sorted(OFF_CRETE) if site in at]
    body = [("Each name stands where its inscriptions were found. A dot is one name at one site, in the colour of its "
             "language layer, and a ring marks the site. A name found at two sites has a dot at each. Sites with one "
             "or two names are dots without a label; the table below names them."), "",
            f"![The names of the Linear A inscriptions on a map of Crete, clustered at their find sites]({IMAGE})", "",
            "## Sites on Crete", ""]
    body += table(["Site", "Names", "Layers", "Kinds", "Most attested"], rows) + [""]
    if away:
        body += ["## Off Crete", ""] + table(["Site", "Names", "Names found there"], away) + [""]
    if at.get(NO_SITE):
        body += ["## On Crete, find site unknown", "", ", ".join(names.link(n) for n in at[NO_SITE]) + ".", ""]
    body += ["## Sources", "",
             ("Coastline: Natural Earth, 1:10m land, public domain. Site positions: Pleiades, except the sites marked "
              "approximate, which are placed by hand near their villages. Names and sites: "
              "`data/linear-a/onomasticon.json`."), ""]
    drawn = sum(len(c["names"]) for c in found)
    fields = {"title": "Crete by find site",
              "desc": (f"A map of Crete with the {drawn} dots of the names, one for each name at each of {len(found)} "
                       "find sites, coloured by language layer."),
              "tags": ["names", "guide", "map"], "kind": "ledger"}
    return _page(f"{GUIDE}/map", fields, body)
