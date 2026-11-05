"""
The look of a guest invitation, by kind of event.

A wedding should feel like a mandap at night, a birthday like balloons and
cake. Each theme is a scene for the top of the page, the shape of the card that
overlaps it, and small decoration elsewhere. Everything here is drawn as inline
SVG, so a page loads nothing from anywhere else and stays small.

Only the *default* colours come from the theme. A colour the organiser chose
always wins, and a cover photo they uploaded replaces the drawn scene.

No user text passes through this module: it returns constants, safe to place
in the page unescaped.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

DEFAULT_PRIMARY = "#5B1226"
DEFAULT_ACCENT = "#B8892F"
DEFAULT_BACKGROUND = "#FBF6EC"


@dataclass(frozen=True)
class Theme:
    key: str
    eyebrow: str
    primary: str
    accent: str
    background: str  # CSS background for the page
    card: str
    panel: str  # CSS background for the RSVP panel
    scene: str
    emblem: str
    arch: str  # SVG path, viewBox 0 0 200 44; open at the bottom
    corner: str = ""  # bottom-left card ornament, mirrored for the right
    panel_decor: str = ""
    foot_decor: str = ""
    divider: str = "◆"
    title_italic: bool = False
    split_when_where: bool = False  # "When | Where" columns instead of rows
    inline_contact: bool = False
    promo_icon: str = ""


def _svg(view: str, body: str, cls: str = "", extra: str = "") -> str:
    return f'<svg class="{cls}" viewBox="{view}" {extra} aria-hidden="true" focusable="false">{body}</svg>'


def _scene(body: str, sky_top: str, sky_bottom: str) -> str:
    return _svg(
        "0 0 480 300",
        f'<defs><linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{sky_top}"/>'
        f'<stop offset="1" stop-color="{sky_bottom}"/></linearGradient></defs>'
        f'<rect width="480" height="300" fill="url(#sky)"/>{body}',
        "scene-art",
        'preserveAspectRatio="xMidYMax slice"',
    )


def _glow(cx: int, cy: int, rx: int, ry: int, colour: str, strength: float, name: str = "glow") -> str:
    """Light that fades to nothing, rather than a disc with an edge."""
    return (
        f'<defs><radialGradient id="{name}"><stop offset="0" stop-color="{colour}" stop-opacity="{strength}"/>'
        f'<stop offset="1" stop-color="{colour}" stop-opacity="0"/></radialGradient></defs>'
        f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="url(#{name})"/>'
    )


def _rng(seed: str) -> random.Random:
    # Seeded: the same page for every guest, and for every test.
    return random.Random(seed)


def _bokeh(seed: str, count: int, colors: tuple[str, ...], lo: float = 2, hi: float = 7, top: int = 190) -> str:
    r = _rng(seed)
    return "".join(
        f'<circle cx="{r.uniform(0, 480):.0f}" cy="{r.uniform(0, top):.0f}" r="{r.uniform(lo, hi):.1f}" '
        f'fill="{r.choice(colors)}" opacity="{r.uniform(0.25, 0.85):.2f}"/>'
        for _ in range(count)
    )


def _flower(x: float, y: float, r: float, petal: str, centre: str, petals: int = 7) -> str:
    parts = []
    for i in range(petals):
        a = i * 2 * math.pi / petals
        parts.append(
            f'<circle cx="{x + math.cos(a) * r * 0.62:.1f}" cy="{y + math.sin(a) * r * 0.62:.1f}" '
            f'r="{r * 0.55:.1f}" fill="{petal}"/>'
        )
    parts.append(f'<circle cx="{x}" cy="{y}" r="{r * 0.42:.1f}" fill="{centre}"/>')
    return "".join(parts)


def _cluster(seed: str, cx: float, cy: float, spread_x: float, spread_y: float, count: int, palette) -> str:
    r = _rng(seed)
    out = []
    for _ in range(count):
        petal, centre = r.choice(palette)
        out.append(_flower(
            cx + r.uniform(-spread_x, spread_x), cy + r.uniform(-spread_y, spread_y),
            r.uniform(7, 13), petal, centre,
        ))
    return "".join(out)


def _garland(x1: float, x2: float, y: float, sag: float, palette, step: float = 9) -> str:
    out = []
    n = max(2, int(abs(x2 - x1) / step))
    for i in range(n + 1):
        t = i / n
        x = x1 + (x2 - x1) * t
        yy = y + sag * 4 * t * (1 - t)
        colour = palette[i % len(palette)]
        out.append(f'<circle cx="{x:.1f}" cy="{yy:.1f}" r="5.2" fill="{colour}"/>')
    return "".join(out)


def _balloon(x: float, y: float, r: float, colour: str, shine: str = "#fff", tail: float = 120) -> str:
    return (
        f'<path d="M{x} {y + r * 1.2} q-9 {tail * 0.4} 4 {tail * 0.7} t-3 {tail * 0.4}" fill="none" stroke="#b9a6a0" stroke-width="1"/>'
        f'<ellipse cx="{x}" cy="{y}" rx="{r}" ry="{r * 1.2}" fill="{colour}"/>'
        f'<path d="M{x - 5} {y + r * 1.18} h10 l-5 -7z" fill="{colour}"/>'
        f'<ellipse cx="{x - r * 0.34}" cy="{y - r * 0.42}" rx="{r * 0.22}" ry="{r * 0.34}" fill="{shine}" opacity=".55"/>'
    )


# ── Emblems: the small mark in the card's arch. currentColor is the accent. ───

_S = 'fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"'


def _emblem(body: str) -> str:
    return _svg("0 0 32 32", f"<g {_S}>{body}</g>", "emblem")


_LOTUS = _emblem(
    '<path d="M16 26c-4-3-6-7-6-11 0-3 3-7 6-10 3 3 6 7 6 10 0 4-2 8-6 11z"/>'
    '<path d="M16 26c-5 0-10-3-12-9 2-1 4-1 6 0"/><path d="M16 26c5 0 10-3 12-9-2-1-4-1-6 0"/>'
)
_CAKE = _emblem(
    '<path d="M5 26h22V17a2 2 0 0 0-2-2H7a2 2 0 0 0-2 2z"/><path d="M5 20c2 2 4 2 5.5 0 1.5 2 4 2 5.5 0 1.5 2 4 2 5.5 0 1.5 2 3.5 2 5.5 0"/>'
    '<path d="M11 15v-4M16 15v-4M21 15v-4"/><path d="M11 8v-1M16 8v-1M21 8v-1"/>'
)
_HEART = _emblem('<path d="M16 26S5 19 5 12a6 6 0 0 1 11-3 6 6 0 0 1 11 3c0 7-11 14-11 14z"/>')
_RINGS = _emblem('<circle cx="12" cy="19" r="7"/><circle cx="20" cy="19" r="7"/><path d="M12 12l-2-3 2-3 2 3zM20 12"/>')
_MOON = _emblem('<path d="M22 22A10 10 0 0 1 12 6a10 10 0 1 0 14 14 10 10 0 0 1-4 2z"/><path d="M23 7v4M21 9h4"/>')
_HOME = _emblem('<path d="M5 15 16 6l11 9"/><path d="M8 13v13h16V13"/><path d="M14 26v-7h4v7"/>')
_DIYA = _emblem(
    '<path d="M4 18c2 5 7 8 12 8s10-3 12-8c-3 1-8 2-12 2s-9-1-12-2z"/>'
    '<path d="M16 16c-2.500-2-2.500-5 0-9 2.500 4 2.500 7 0 9z"/>'
)
_TOWER = _emblem('<path d="M8 26V8l8-3 8 3v18"/><path d="M4 26h24"/><path d="M12 12h1M19 12h1M12 17h1M19 17h1M14 26v-4h4v4"/>')
_SPARK = _emblem('<path d="M16 5l2.500 8.500L27 16l-8.500 2.500L16 27l-2.500-8.500L5 16l8.500-2.500z"/>')


# ── Arch shapes, viewBox 0 0 200 44. They sit on the card's top edge. ─────────

ARCH_CUSP = "M0 44 C22 44 34 40 46 30 C56 21 66 22 72 16 C80 8 90 2 100 0 C110 2 120 8 128 16 C134 22 144 21 154 30 C166 40 178 44 200 44"
ARCH_DOME = "M0 44 C40 44 46 8 100 8 C154 8 160 44 200 44"
ARCH_PEAK = "M0 44 L60 44 L100 8 L140 44 L200 44"
ARCH_CLOUD = "M0 44 C16 44 20 30 36 30 C42 16 62 14 72 22 C80 6 120 6 128 22 C138 14 158 16 164 30 C180 30 184 44 200 44"
ARCH_TEMPLE = "M0 44 L38 44 L38 32 L58 32 L58 20 L80 20 L80 12 C88 8 94 2 100 0 C106 2 112 8 120 12 L120 20 L142 20 L142 32 L162 32 L162 44 L200 44"
ARCH_NOTCH = "M0 44 L58 44 L72 12 L128 12 L142 44 L200 44"
ARCH_WAVE = "M0 44 C30 44 40 22 66 22 C80 22 84 10 100 10 C116 10 120 22 134 22 C160 22 170 44 200 44"


def _corner(body: str) -> str:
    return _svg("0 0 60 60", f'<g {_S.replace("1.5", "1")}>{body}</g>', "corner")


_FLORAL_CORNER = _corner(
    '<path d="M4 56C10 36 24 24 44 18"/><path d="M14 40c-6-2-9-7-8-13 6 1 10 6 8 13z"/>'
    '<path d="M24 30c-2-6 0-11 6-14 3 6 1 11-6 14z"/><path d="M12 50c5 3 11 2 15-3-5-3-11-2-15 3z"/>'
    '<circle cx="20" cy="44" r="5"/><path d="M20 39v10M15 44h10"/><path d="M32 40c4 1 8-1 10-5-4-2-8 0-10 5z"/>'
)
_PARTY_CORNER = _svg(
    "0 0 60 60",
    '<rect x="16" y="26" width="36" height="28" rx="3" fill="#F9B233"/><rect x="12" y="18" width="44" height="11" rx="2" fill="#F6A21E"/>'
    '<rect x="30" y="18" width="8" height="36" fill="#E5486D"/><path d="M34 18c-8-12-18-6-12 0zM34 18c8-12 18-6 12 0z" fill="#E5486D"/>',
    "corner keep",
)

# ── Scenes ────────────────────────────────────────────────────────────────────

_MARIGOLD = ("#F59E0B", "#EA7A12", "#FBBF24", "#E11D48")


def _wedding_scene() -> str:
    lights = "".join(
        f'<path d="M{x} 0 V{h}" stroke="#d9b26644" stroke-width=".7"/>'
        + "".join(f'<circle cx="{x}" cy="{y}" r="1.700" fill="#FFE2A0"/>' for y in range(14, h, 15))
        for x, h in ((16, 150), (40, 118), (64, 170), (96, 92), (384, 92), (416, 170), (440, 118), (464, 150))
    )
    glow = _glow(240, 170, 210, 160, "#FFCE85", .34)
    canopy = (
        '<path d="M92 66 C150 30 330 30 388 66 L388 84 L92 84 Z" fill="#6E1B2E"/>'
        '<path d="M92 84 C130 122 196 122 240 84 C284 122 350 122 388 84 Z" fill="#FBF0DD"/>'
        '<path d="M92 84 C130 122 196 122 240 84" fill="none" stroke="#E7CFA6"/><path d="M240 84 C284 122 350 122 388 84" fill="none" stroke="#E7CFA6"/>'
    )
    pillars = "".join(
        f'<rect x="{x}" y="80" width="15" height="220" fill="url(#pillar)"/>'
        f'<path d="M{x + 7.500} 84 C{x + d} 150 {x + d} 240 {x + 7.500} 300 L{x + d * 1.900} 300 C{x + d * 1.500} 220 {x + d * 1.300} 150 {x + 7.500} 84Z" fill="#FBF0DD" opacity=".92"/>'
        for x, d in ((100, 34), (365, -30))
    )
    defs = '<defs><linearGradient id="pillar" x1="0" x2="1"><stop offset="0" stop-color="#C9A25F"/><stop offset=".5" stop-color="#F3DDA9"/><stop offset="1" stop-color="#B98F4B"/></linearGradient></defs>'
    garlands = _garland(92, 388, 62, -14, _MARIGOLD) + _garland(92, 388, 78, 8, ("#FBF0DD", "#F59E0B", "#E11D48"), 12)
    drop = "".join(_garland(x, x, 84, 0, _MARIGOLD, 8).replace("r=\"5.2\"", 'r="4"') for x in ())
    palette = (("#E11D48", "#9F1239"), ("#F8FAFC", "#FBBF24"), ("#F59E0B", "#B45309"), ("#BE123C", "#7F1D1D"))
    flowers = (
        _cluster("wed-l", 44, 214, 50, 34, 22, palette)
        + _cluster("wed-r", 436, 214, 50, 34, 22, palette)
        + _cluster("wed-top", 240, 42, 150, 8, 22, palette)
    )
    return _scene(defs + glow + lights + canopy + pillars + garlands + drop + flowers, "#14080B", "#3B1820")


def _birthday_scene() -> str:
    bunting = '<path d="M-10 118 C70 160 150 146 214 112" fill="none" stroke="#c9a890" stroke-width="1.200"/>' + "".join(
        f'<path d="M{x} {y} l18 4 -12 22z" fill="{c}"/>'
        for x, y, c in ((2, 124, "#F59E0B"), (34, 139, "#EC6A8E"), (66, 147, "#60A5FA"), (98, 147, "#FBBF24"), (130, 141, "#34B6A5"), (162, 131, "#EC6A8E"), (192, 118, "#F59E0B"))
    )
    balloons = (
        _balloon(66, 76, 44, "#F48FB1", tail=150) + _balloon(134, 66, 40, "#90CAF9", tail=150)
        + _balloon(22, 150, 30, "#FBBF24", tail=120) + _balloon(104, 148, 26, "#F9A8C4", tail=110)
    )
    cake = (
        '<ellipse cx="376" cy="256" rx="96" ry="10" fill="#b9825a"/><rect x="366" y="214" width="20" height="42" fill="#a97650"/>'
        '<ellipse cx="376" cy="214" rx="68" ry="7" fill="#c89268"/>'
        '<rect x="316" y="150" width="120" height="60" rx="8" fill="#FFF7EC"/>'
        '<path d="M316 162c8 16 18 16 24 0 7 18 18 18 24 0 7 18 18 18 24 0 7 18 18 18 24 0 6 16 18 16 24 0V158a8 8 0 0 0-8-8H324a8 8 0 0 0-8 8z" fill="#F7B4C8"/>'
        + "".join(
            f'<rect x="{x}" y="122" width="6" height="30" rx="2" fill="{c}"/><path d="M{x + 3} 110c5 6 4 11 0 12-4-1-5-6 0-12z" fill="#FBBF24"/>'
            for x, c in ((340, "#F48FB1"), (362, "#90CAF9"), (384, "#FDE68A"), (406, "#A7F3D0"))
        )
    )
    gift = (
        '<rect x="432" y="214" width="56" height="44" rx="3" fill="#E5486D"/><rect x="456" y="214" width="9" height="44" fill="#FCE7A8"/>'
        '<path d="M460 214c-14-18-30-8-18 0zM460 214c14-18 30-8 18 0z" fill="#FCE7A8"/>'
    )
    return _scene(
        _bokeh("bday", 40, ("#FFFFFF", "#FDE68A", "#F9A8C4"), 3, 11, 240) + balloons + bunting + f'<g transform="translate(0 -46)">{gift}{cake}</g>',
        "#F4D9DF", "#F6E6D8",
    )


def _anniversary_scene() -> str:
    hearts = "".join(
        f'<path transform="translate({x} {y}) scale({s})" d="M0 8C-10 0-16-8-9-14-4-18 0-13 0-10 0-13 4-18 9-14 16-8 10 0 0 8z" fill="{c}" opacity="{o}"/>'
        for x, y, s, c, o in (
            (60, 70, 1.2, "#F7A8B8", .8), (120, 40, .7, "#FBCFD6", .7), (420, 60, 1.1, "#F7A8B8", .8), (360, 34, .7, "#FBCFD6", .7),
            (34, 150, .8, "#FBCFD6", .6), (452, 150, .8, "#FBCFD6", .6),
        )
    )
    glasses = "".join(
        f'<g transform="translate({x} 92) rotate({a})"><path d="M-22 0h44l-6 44c-2 12-30 12-32 0z" fill="#FBE7BD" opacity=".9"/>'
        f'<path d="M-22 0h44l-2 14h-40z" fill="#FFF" opacity=".55"/><rect x="-2" y="56" width="4" height="62" fill="#F4E3C4"/>'
        f'<rect x="-22" y="116" width="44" height="5" rx="2.500" fill="#F4E3C4"/></g>'
        for x, a in ((206, 11), (274, -11))
    )
    clink = "".join(f'<path d="M240 66 l{dx} {dy}" stroke="#FDE9B8" stroke-width="2" stroke-linecap="round"/>' for dx, dy in ((-9, -16), (0, -22), (9, -16)))
    palette = (("#B91C4B", "#7F1D3D"), ("#E8476F", "#9F1239"), ("#FBCFD6", "#E8476F"), ("#FFF1F2", "#F7A8B8"))
    return _scene(
        _glow(240, 110, 210, 130, "#FFD9A8", .4) + _bokeh("anniv", 30, ("#FFE9C7", "#FBCFD6"), 2, 6) + hearts
        + f'<g transform="translate(0 -30)">{clink}{glasses}</g>'
        + _cluster("ann-l", 40, 214, 52, 34, 22, palette) + _cluster("ann-r", 440, 214, 52, 34, 22, palette),
        "#3B0F24", "#7A2342",
    )


def _engagement_scene() -> str:
    rings = (
        '<g fill="none" stroke-width="11"><circle cx="208" cy="126" r="42" stroke="#E7BF70"/><circle cx="272" cy="126" r="42" stroke="#F5DDA6"/></g>'
        '<path d="M250 62l22-16 22 16-22 22z" fill="#EAF6FF" stroke="#BFE3FF"/><path d="M250 62h44M272 46l-8 16 8 22 8-22z" fill="none" stroke="#9CCBEF"/>'
    )
    sparks = "".join(
        f'<path transform="translate({x} {y}) scale({s})" d="M0-9 2-2 9 0 2 2 0 9-2 2-9 0-2-2z" fill="#FFF3C9"/>'
        for x, y, s in ((316, 40, 1.100), (336, 70, .7), (150, 60, .9), (120, 100, .6), (360, 118, .6), (180, 30, .6))
    )
    leaves = "".join(
        f'<path transform="translate({x} {y}) rotate({a})" d="M0 0C14-14 38-14 52 0 38 14 14 14 0 0z" fill="{c}"/>'
        for x, y, a, c in (
            (10, 220, -40, "#6F8F73"), (40, 250, -25, "#88A68B"), (70, 280, -10, "#6F8F73"),
            (470, 220, 220, "#6F8F73"), (440, 250, 205, "#88A68B"), (410, 280, 190, "#6F8F73"),
        )
    )
    palette = (("#FFF7F2", "#F4BFC4"), ("#F9CDD2", "#D9778A"), ("#FDE7E7", "#E8A3B0"))
    return _scene(
        _bokeh("engage", 34, ("#FFF", "#FBD6DA", "#F8E7B0"), 2, 8) + f'<g transform="translate(0 -60)">{leaves}</g>' + f'<g transform="translate(0 -22)">{rings}{sparks}</g>'
        + _cluster("eng-l", 34, 212, 42, 26, 14, palette) + _cluster("eng-r", 446, 212, 42, 26, 14, palette),
        "#F3C9CE", "#FBE7DE",
    )


def _baby_scene() -> str:
    cloud = lambda x, y, s, o=1: (  # noqa: E731
        f'<g transform="translate({x} {y}) scale({s})" opacity="{o}" fill="#fff">'
        '<circle cx="-30" cy="10" r="20"/><circle cx="0" cy="0" r="28"/><circle cx="32" cy="10" r="20"/><rect x="-50" y="10" width="102" height="20" rx="10"/></g>'
    )
    moon = '<path d="M268 42a48 48 0 1 0 46 66 40 40 0 0 1-46-66z" fill="#FCE7A8"/>'
    stars = "".join(
        f'<path transform="translate({x} {y}) scale({s})" d="M0-8 2.300-2.500 8-2.500 3.500 1 5 7 0 3.800-5 7-3.500 1-8-2.500-2.300-2.500z" fill="#FDE9B8"/>'
        for x, y, s in ((90, 40, 1.100), (150, 74, .7), (360, 42, 1), (420, 80, .8), (40, 96, .7), (440, 30, .6))
    )
    balloons = _balloon(72, 118, 24, "#BFDBFE", tail=90) + _balloon(116, 104, 20, "#FBCFE8", tail=90) + _balloon(398, 112, 24, "#FDE68A", tail=90)
    hanging = "".join(
        f'<path d="M{x} 0V{y}" stroke="#d9c7a7"/>{s}'
        for x, y, s in ((210, 26, ""), (328, 22, ""))
    )
    return _scene(
        moon + hanging + stars + balloons + cloud(70, 230, 1.300) + cloud(240, 252, 1.700) + cloud(410, 226, 1.300) + cloud(160, 180, .7, .8) + cloud(350, 170, .6, .8),
        "#CFE3F6", "#F6E9F2",
    )


def _housewarming_scene() -> str:
    house = (
        '<path d="M120 148 240 62l120 86z" fill="#7C2D12"/><rect x="146" y="146" width="188" height="130" fill="#FDECC8"/>'
        '<rect x="212" y="186" width="56" height="90" rx="4" fill="#92400E"/><circle cx="258" cy="234" r="3" fill="#FBBF24"/>'
        '<rect x="160" y="172" width="38" height="38" rx="3" fill="#FFD976"/><path d="M179 172v38M160 191h38" stroke="#B45309" stroke-width="2"/>'
        '<rect x="282" y="172" width="38" height="38" rx="3" fill="#FFD976"/><path d="M301 172v38M282 191h38" stroke="#B45309" stroke-width="2"/>'
    )
    toran = _garland(205, 275, 180, 12, _MARIGOLD, 8) + "".join(
        f'<path d="M{x} 184 l-5 13 5 5 5-5z" fill="#4D7C0F"/>' for x in (214, 230, 246, 262)
    )
    plants = "".join(
        f'<path d="M{x} 276h28l-4 22h-20z" fill="#B45309"/><path transform="translate({x + 14} 276)" d="M0 0C-16-22-14-40 0-52 14-40 16-22 0 0z" fill="#3F7A4A"/>'
        for x in (100, 352)
    )
    glow = _glow(240, 150, 240, 170, "#FFE7A8", .6)
    sun = '<circle cx="240" cy="80" r="56" fill="#FFE9B5" opacity=".65"/>'
    hills = '<path d="M0 240C80 200 150 228 240 236S400 200 480 240V300H0Z" fill="#E7A764" opacity=".45"/>'
    home = f'<g transform="translate(48 -6) scale(.8)">{house}{toran}{plants}</g>'
    return _scene(sun + hills + glow + home + _bokeh("home", 16, ("#FFF4D1",), 2, 5, 110), "#F7B267", "#FCE3B6")


def _religious_scene() -> str:
    rays = "".join(
        f'<path d="M240 170 L{240 + math.cos(a) * 420:.0f} {170 + math.sin(a) * 420:.0f} L{240 + math.cos(a + .1) * 420:.0f} {170 + math.sin(a + .1) * 420:.0f}Z" fill="#FFE6A8" opacity=".14"/>'
        for a in [i * math.pi / 12 for i in range(24)]
    )
    arch = (
        '<path d="M96 300V130C96 74 170 60 240 20 310 60 384 74 384 130V300H344V136C344 104 286 92 240 66 194 92 136 104 136 136V300Z" fill="#7F1D1D"/>'
        '<path d="M96 300V130C96 74 170 60 240 20 310 60 384 74 384 130V300" fill="none" stroke="#FBBF24" stroke-width="3"/>'
    )
    bells = "".join(
        f'<path d="M{x} 60v26" stroke="#FBBF24"/><path d="M{x - 10} 106c0-16 4-22 10-22s10 6 10 22z" fill="#FBBF24"/><circle cx="{x}" cy="110" r="3" fill="#B45309"/>'
        for x in (60, 420)
    )
    diya = (
        '<defs><radialGradient id="flame"><stop offset="0" stop-color="#FFD98A" stop-opacity=".85"/><stop offset="1" stop-color="#FFD98A" stop-opacity="0"/></radialGradient></defs>'
        '<ellipse cx="240" cy="170" rx="90" ry="90" fill="url(#flame)"/>'
        '<path d="M240 136c16 20 14 38 0 44-14-6-16-24 0-44z" fill="#FF9F1C"/><path d="M240 154c7 10 6 20 0 24-6-4-7-14 0-24z" fill="#FFF3C4"/>'
        '<path d="M186 182c6 24 28 38 54 38s48-14 54-38c-18 6-36 8-54 8s-36-2-54-8z" fill="#C2410C"/>'
        '<path d="M186 182c18 6 36 8 54 8s36-2 54-8" fill="none" stroke="#FDE68A" stroke-width="2"/>'
    )
    palette = (("#F59E0B", "#B45309"), ("#FBBF24", "#B45309"), ("#EA580C", "#9A3412"))
    return _scene(
        rays + arch + bells + f'<g transform="translate(0 -44)">{diya}</g>' + _garland(96, 384, 96, 22, _MARIGOLD, 10)
        + _cluster("rel-l", 40, 216, 42, 24, 14, palette) + _cluster("rel-r", 440, 216, 42, 24, 14, palette),
        "#7C2D12", "#D97706",
    )


def _corporate_scene() -> str:
    r = _rng("corp")
    towers = ""
    x = -8
    while x < 480:
        w, h = r.randint(36, 62), r.randint(70, 210)
        towers += f'<rect x="{x}" y="{300 - h}" width="{w}" height="{h}" fill="{r.choice(("#1E3A5F", "#234673", "#1B3355"))}"/>'
        for wy in range(300 - h + 12, 296, 16):
            for wx in range(x + 7, x + w - 7, 12):
                if r.random() > .42:
                    towers += f'<rect x="{wx}" y="{wy}" width="6" height="8" fill="#FCD980" opacity="{r.uniform(.45, .95):.2f}"/>'
        x += w + r.randint(2, 8)
    beams = "".join(
        f'<path d="M{x} 0 L{x + dx} 300 L{x + dx + 70} 300Z" fill="#7FB4E8" opacity=".09"/>'
        for x, dx in ((90, -60), (240, 0), (390, 40))
    )
    return _scene(beams + _bokeh("corp2", 26, ("#FFFFFF", "#A8CDF0"), 1, 2.500, 120) + towers, "#0D1B33", "#2B4C7E")


def _custom_scene() -> str:
    lanterns = "".join(
        f'<path d="M{x} 0V{y}" stroke="#D9B26688"/><path d="M{x - w} {y + 8}C{x - w} {y + 40} {x + w} {y + 40} {x + w} {y + 8}C{x + w} {y - 8} {x - w} {y - 8} {x - w} {y + 8}Z" fill="{c}"/>'
        f'<path d="M{x - w * .5:.0f} {y - 2}v42M{x + w * .5:.0f} {y - 2}v42M{x} {y - 4}v46" stroke="#fff" opacity=".35"/><rect x="{x - 8}" y="{y - 8}" width="16" height="5" fill="#FBBF24"/>'
        f'<rect x="{x - 8}" y="{y + 32}" width="16" height="5" fill="#FBBF24"/><path d="M{x} {y + 37}v18" stroke="#FBBF24" stroke-width="2"/>'
        for x, y, w, c in ((60, 60, 28, "#E4577F"), (140, 28, 24, "#F59E0B"), (240, 72, 32, "#8B5CF6"), (340, 26, 24, "#10B8A6"), (424, 62, 28, "#E4577F"))
    )
    r = _rng("confetti")
    confetti = "".join(
        f'<rect x="{r.uniform(0, 480):.0f}" y="{r.uniform(0, 280):.0f}" width="{r.uniform(4, 9):.1f}" height="{r.uniform(3, 5):.1f}" '
        f'transform="rotate({r.uniform(0, 180):.0f} {r.uniform(0, 480):.0f} {r.uniform(0, 280):.0f})" fill="{r.choice(("#FBBF24", "#F472B6", "#60E0D2", "#fff"))}" opacity=".85"/>'
        for _ in range(60)
    )
    return _scene(_bokeh("custom", 26, ("#FDE68A", "#F9A8D4", "#A5F3FC"), 3, 10, 260) + confetti + lanterns, "#3D1E6D", "#B5578B")


# ── Small decoration ──────────────────────────────────────────────────────────

def _faded_flowers(colour: str) -> str:
    return _svg("0 0 120 120", "".join(
        f'<g opacity=".28" fill="none" stroke="{colour}" stroke-width="1"><circle cx="{x}" cy="{y}" r="{s}"/>'
        + "".join(
            f'<ellipse cx="{x + math.cos(i * math.pi / 3) * s * 1.300:.1f}" cy="{y + math.sin(i * math.pi / 3) * s * 1.300:.1f}" rx="{s * .9:.1f}" ry="{s * .55:.1f}" transform="rotate({i * 60} {x + math.cos(i * math.pi / 3) * s * 1.300:.1f} {y + math.sin(i * math.pi / 3) * s * 1.300:.1f})"/>'
            for i in range(6)
        ) + "</g>"
        for x, y, s in ((34, 40, 12), (84, 80, 9), (92, 22, 6))
    ), "decor")


def _confetti_decor() -> str:
    r = _rng("decor")
    colours = ("#F472B6", "#60A5FA", "#FBBF24", "#34D399", "#A78BFA")
    return _svg("0 0 120 120", "".join(
        f'<rect x="{r.uniform(4, 110):.0f}" y="{r.uniform(4, 110):.0f}" width="9" height="4" rx="2" fill="{r.choice(colours)}" '
        f'transform="rotate({r.uniform(0, 180):.0f} 60 60)"/>'
        for _ in range(9)
    ), "decor")


def _foot_balloons() -> str:
    return (
        _svg("0 0 120 150", _balloon(36, 60, 42, "#BFDBFE", tail=70), "foot left keep")
        + _svg("0 0 120 150", _balloon(84, 60, 36, "#F9A8C4", tail=70), "foot right keep")
    )


def _foot_flowers(colour: str) -> str:
    return (
        _svg("0 0 120 120", _faded_flowers_body(colour), "foot left keep")
        + _svg("0 0 120 120", _faded_flowers_body(colour), "foot right keep")
    )


def _faded_flowers_body(colour: str) -> str:
    return _faded_flowers(colour).split(">", 1)[1].rsplit("</svg>", 1)[0]


_GIFT_ICON = _emblem('<rect x="5" y="13" width="22" height="14" rx="1.500"/><path d="M3 9h26v4H3zM16 9v18"/><path d="M16 9c-8-8-13-1-7 0M16 9c8-8 13-1 7 0"/>')

THEMES: dict[str, Theme] = {
    "wedding": Theme(
        key="wedding", eyebrow="You're invited", primary=DEFAULT_PRIMARY, accent=DEFAULT_ACCENT,
        background="linear-gradient(180deg,#FBF4E6 0%,#FBF1E2 60%,#F8EADB 100%)", card="#FFFAF0",
        panel="linear-gradient(180deg,#F5E6DC,#F3E0D8)", scene=_wedding_scene(), emblem=_LOTUS, arch=ARCH_CUSP,
        corner=_FLORAL_CORNER, panel_decor=_faded_flowers("#7A1F3D"), foot_decor=_foot_flowers("#7A1F3D"),
    ),
    "birthday": Theme(
        key="birthday", eyebrow="You're invited to", primary=DEFAULT_PRIMARY, accent="#E79A1A",
        background="linear-gradient(180deg,#FDF3EE 0%,#FBEFF3 55%,#F6ECF8 100%)", card="#FFF8F3",
        panel="linear-gradient(120deg,#F7ECF6,#EFE9FA)", scene=_birthday_scene(), emblem=_CAKE, arch=ARCH_DOME,
        corner=_PARTY_CORNER, panel_decor=_confetti_decor(), foot_decor=_foot_balloons(), title_italic=True,
        split_when_where=True, inline_contact=True, promo_icon=_GIFT_ICON, divider="✦",
    ),
    "anniversary": Theme(
        key="anniversary", eyebrow="Celebrating love", primary="#7A1F3D", accent="#C98A5A",
        background="linear-gradient(180deg,#FFF3F2,#FBE9EA)", card="#FFF9F7", panel="linear-gradient(180deg,#FBE3E5,#F8DDE3)",
        scene=_anniversary_scene(), emblem=_HEART, arch=ARCH_WAVE, corner=_FLORAL_CORNER,
        panel_decor=_faded_flowers("#B91C4B"), foot_decor=_foot_flowers("#B91C4B"), title_italic=True, divider="♥",
    ),
    "engagement": Theme(
        key="engagement", eyebrow="Join us as we say yes", primary="#6B2B47", accent="#C39A55",
        background="linear-gradient(180deg,#FFF6F3,#FBEEEA)", card="#FFFBF8", panel="linear-gradient(180deg,#F9EBE6,#F5E4E3)",
        scene=_engagement_scene(), emblem=_RINGS, arch=ARCH_CUSP, corner=_FLORAL_CORNER,
        panel_decor=_faded_flowers("#6F8F73"), foot_decor=_foot_flowers("#6F8F73"), title_italic=True, divider="✦",
    ),
    "baby_shower": Theme(
        key="baby_shower", eyebrow="A little one is on the way", primary="#3D5A80", accent="#E3A857",
        background="linear-gradient(180deg,#F2F8FE,#F8F1FA)", card="#FFFFFF", panel="linear-gradient(120deg,#E8F2FC,#F4EAF8)",
        scene=_baby_scene(), emblem=_MOON, arch=ARCH_CLOUD, panel_decor=_confetti_decor(), title_italic=True,
        split_when_where=True, inline_contact=True, promo_icon=_GIFT_ICON, divider="✦",
    ),
    "housewarming": Theme(
        key="housewarming", eyebrow="Welcome to our new home", primary="#7C2D12", accent="#D97706",
        background="linear-gradient(180deg,#FFF7EA,#FDF0DD)", card="#FFFCF5", panel="linear-gradient(180deg,#FBEBD0,#F9E4C6)",
        scene=_housewarming_scene(), emblem=_HOME, arch=ARCH_PEAK, panel_decor=_faded_flowers("#B45309"),
        foot_decor=_foot_flowers("#B45309"), split_when_where=True, inline_contact=True,
    ),
    "religious": Theme(
        key="religious", eyebrow="With divine blessings", primary="#7F1D1D", accent="#D97706",
        background="linear-gradient(180deg,#FFF6E5,#FDEBCF)", card="#FFFBF0", panel="linear-gradient(180deg,#FBE7C4,#F8DFB6)",
        scene=_religious_scene(), emblem=_DIYA, arch=ARCH_TEMPLE, corner=_FLORAL_CORNER,
        panel_decor=_faded_flowers("#B45309"), foot_decor=_foot_flowers("#B45309"), divider="ॐ",
    ),
    "corporate": Theme(
        key="corporate", eyebrow="You're invited to attend", primary="#1E3A5F", accent="#B08D57",
        background="linear-gradient(180deg,#F5F7FA,#EEF2F7)", card="#FFFFFF", panel="linear-gradient(180deg,#E9EEF5,#E3E9F2)",
        scene=_corporate_scene(), emblem=_TOWER, arch=ARCH_NOTCH, split_when_where=True, inline_contact=True, divider="—",
    ),
    "custom": Theme(
        key="custom", eyebrow="You're invited", primary="#4C1D95", accent="#D97706",
        background="linear-gradient(180deg,#FBF6FF,#FDF2F7)", card="#FFFBFF", panel="linear-gradient(120deg,#F1EAFB,#FBE9F2)",
        scene=_custom_scene(), emblem=_SPARK, arch=ARCH_WAVE, panel_decor=_confetti_decor(), foot_decor="",
        split_when_where=True, inline_contact=True, promo_icon=_GIFT_ICON, divider="✦",
    ),
}

# For events from the booking flow, which have an occasion name rather than a type.
_KEYWORDS = (
    ("wedding", ("wedding", "shaadi", "vivah", "sangeet", "mehendi", "haldi", "reception")),
    ("engagement", ("engagement", "roka", "sagai", "ring ceremony")),
    ("anniversary", ("anniversary",)),
    ("birthday", ("birthday", "bday", "party")),
    ("baby_shower", ("baby", "godh", "naming", "naamkaran")),
    ("housewarming", ("housewarming", "griha", "griha pravesh", "house warming")),
    ("religious", ("puja", "pooja", "religious", "diwali", "navratri", "festival", "havan", "katha", "eid", "christmas")),
    ("corporate", ("corporate", "office", "conference", "launch")),
)


def theme_for(event_type: str | None, label: str | None = None) -> Theme:
    if event_type in THEMES:
        return THEMES[event_type]
    text = (label or "").lower()
    for key, words in _KEYWORDS:
        if any(w in text for w in words):
            return THEMES[key]
    return THEMES["custom"]
