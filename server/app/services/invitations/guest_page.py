"""
The guest's invitation page: what opens from the WhatsApp message.

Should feel like a card someone made, not a website, and like *this kind of
event*: see guest_themes for what a wedding or a birthday looks like. No app,
no account, no third-party scripts or fonts: a guest's personal link is a
credential, so nothing here loads from anywhere but our own server and the
event's cover image.

Two layers:

* **Server-rendered shell** — the scene, card, date, venue and Open Graph tags
  are in the HTML response itself. WhatsApp's crawler runs no script, so this is
  the only thing it can build a preview from. The preview carries the event,
  never the guest: the same link may be forwarded.
* **Script** — once the page is actually on screen it calls ``/i/_api/view`` for
  the guest's own details. That call is what counts as a visit, which is why a
  crawler fetching the preview doesn't look like a guest opening it.

Every server string reaches the DOM through ``textContent`` or html.escape. The
only markup injected is the QR SVG this server generated and fixed icon constants.
"""

from __future__ import annotations

import json
import secrets
from html import escape
from pathlib import Path
from urllib.parse import urlparse

from fastapi.responses import HTMLResponse, Response

from app.core.config import settings
from app.services.invitations.guest_themes import (
    DEFAULT_ACCENT,
    DEFAULT_BACKGROUND,
    DEFAULT_PRIMARY,
    Theme,
    theme_for,
)

_FONT_DIR = Path(__file__).resolve().parents[2] / "assets" / "fonts"
_SERVED_FONTS = {
    "pf-500-normal.woff2", "pf-600-normal.woff2", "pf-600-italic.woff2", "pf-700-italic.woff2",
}
_PLAYFAIR = '"Playfair Display","Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif'
_FONTS = {
    "serif": _PLAYFAIR,
    "traditional": '"Noto Serif Devanagari",' + _PLAYFAIR,
    "modern": '-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif',
}


def font_file(name: str) -> Response | None:
    """A self-hosted font. Only names on the list: this never touches a path a visitor chose."""
    if name not in _SERVED_FONTS:
        return None
    return Response(
        (_FONT_DIR / name).read_bytes(),
        media_type="font/woff2",
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )


_FONT_FACES = "".join(
    f"@font-face{{font-family:'Playfair Display';font-style:{style};font-weight:{weight};font-display:swap;"
    f"src:url(/i/_font/pf-{weight}-{style}.woff2) format('woff2')}}"
    for weight, style in ((500, "normal"), (600, "normal"), (600, "italic"), (700, "italic"))
)

_CSS = """
*{box-sizing:border-box}html,body{margin:0}html{-webkit-text-size-adjust:100%}
html{background:var(--fade)}
body{background:var(--page);min-height:100vh;color:var(--ink);position:relative;overflow-x:hidden;
font:15.5px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif}
a{color:var(--primary)}
.banner{position:relative;z-index:3;background:var(--primary);color:#fff;text-align:center;font-size:12.5px;padding:7px 12px}
.scene{position:relative;height:clamp(200px,62vw,300px);overflow:hidden;background:var(--primary)}
.scene img,.scene-art{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;display:block}
.scene::after{content:"";position:absolute;left:0;right:0;bottom:0;height:42%;background:linear-gradient(180deg,transparent,var(--fade))}
.wrap{position:relative;z-index:1;max-width:460px;margin:0 auto;padding:0 14px}
.invite{position:relative;margin-top:-58px;background:var(--card);border:1.5px solid var(--gold);border-radius:18px;
padding:20px 20px 22px;text-align:center;box-shadow:0 12px 30px rgba(60,20,20,.14)}
.arch{position:absolute;left:50%;top:-43px;transform:translateX(-50%);width:204px;height:44px;display:block;overflow:visible}
.arch path{fill:var(--card);stroke:var(--gold);stroke-width:1.500}
.emblem-wrap{position:absolute;left:50%;top:-30px;transform:translateX(-50%);color:var(--gold);line-height:0}
.emblem{width:30px;height:30px}
.eyebrow{display:flex;align-items:center;justify-content:center;gap:10px;font-size:11px;font-weight:650;letter-spacing:2.500px;
text-transform:uppercase;color:var(--primary);margin-top:6px}
.eyebrow::before,.eyebrow::after{content:"";height:1px;flex:1 1 24px;max-width:56px;background:var(--gold)}
h1{font-family:var(--display);font-weight:600;font-size:clamp(29px,8.6vw,37px);line-height:1.14;color:var(--primary);margin:9px 0 6px;overflow-wrap:anywhere}
.italic-title h1{font-style:italic;font-weight:700}
.ribbon{display:inline-block;position:relative;margin:2px 0 8px;padding:4px 20px;background:var(--gold);color:#fff;font-family:var(--display);font-style:italic;font-weight:600;font-size:17px;
clip-path:polygon(0 0,100% 0,calc(100% - 9px) 50%,100% 100%,0 100%,9px 50%)}
.host{font-family:var(--display);font-style:italic;font-size:17px;margin:0 0 4px;color:var(--ink)}
.orn{display:flex;align-items:center;justify-content:center;gap:9px;color:var(--gold);font-size:11px;margin:11px auto;max-width:210px}
.orn::before,.orn::after{content:"";flex:1;height:1px;background:var(--gold);opacity:.7}
.facts{display:inline-grid;gap:7px;text-align:left;font-size:14.5px;position:relative;z-index:1}
.fact{display:flex;align-items:flex-start;gap:11px;color:var(--ink)}
.ico{flex:none;width:19px;height:19px;color:var(--primary);display:inline-block;line-height:0}
.ico svg{width:100%;height:100%}
.corner{position:absolute;bottom:5px;left:5px;width:40px;height:40px;color:var(--gold);opacity:.8;pointer-events:none}
.corner.flip{left:auto;right:5px;transform:scaleX(-1)}
.corner.keep{left:auto;right:8px;opacity:1;width:38px;height:38px}
.has-corner{padding-bottom:30px}.has-corner .facts{padding:0 16px}
.message{font-family:var(--display);font-size:17.5px;line-height:1.55;text-align:center;white-space:pre-line;color:var(--ink);padding:20px 8px 0;margin:0}
.sec{padding:18px 0 0}
.card{background:color-mix(in srgb,var(--card) 88%,transparent);border:1px solid var(--line);border-radius:14px;padding:14px 16px}
.card+.card{margin-top:10px}
h2{font-family:var(--display);font-weight:600;font-size:21px;margin:0 0 8px;line-height:1.25;color:var(--primary)}
h3{font-family:var(--display);font-weight:600;font-size:16.5px;margin:0;color:var(--primary)}
.muted{color:var(--ink2);font-size:14px}.small{font-size:13px;color:var(--ink2)}
.ww{display:flex;align-items:center;gap:10px;justify-content:space-between;flex-wrap:wrap}
.ww-rows{display:grid;gap:7px;flex:1 1 150px;min-width:0;font-size:14px}
.ww-col{flex:1 1 78px;min-width:0;display:grid;gap:3px;font-size:12.5px;align-content:start}
.ww-col+.ww-col{border-left:1px solid var(--line);padding-left:10px}
.ww-head{display:flex;align-items:center;gap:6px;font-family:var(--display);font-weight:600;font-size:15px;color:var(--primary)}
.ww-head .ico{width:16px;height:16px}
.pill{display:inline-flex;align-items:center;gap:6px;background:var(--primary);color:#fff;text-decoration:none;font-size:11.5px;font-weight:600;
padding:7px 11px;border-radius:99px;min-height:38px;white-space:nowrap}
.pill .ico{width:13px;height:13px;color:#fff}
.contact{display:grid;gap:6px;font-size:14px}.contact.inline{display:flex;flex-wrap:wrap;align-items:center;gap:10px}
.contact a{color:var(--ink);text-decoration:none}.sep{width:1px;height:14px;background:var(--line)}
.fn+.fn{margin-top:10px}.fn .when{color:var(--primary);font-weight:600;font-size:13.5px;margin:3px 0 2px}
.fn .row{display:flex;justify-content:space-between;gap:10px;align-items:baseline}
.fn .pill{margin-top:9px}
.tag{display:inline-block;font-size:11.5px;font-weight:600;padding:2px 8px;border-radius:99px;background:#f8e1e6;color:#8f2340}
.rsvp{position:relative;margin-top:18px;background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:16px 14px 18px;overflow:hidden}
.rsvp-head{display:flex;align-items:center;justify-content:center;gap:10px;font-family:var(--display);font-weight:600;font-size:20px;letter-spacing:1px;color:var(--primary);position:relative;z-index:1}
.rsvp-head::before,.rsvp-head::after{content:"";flex:0 1 54px;height:1px;background:var(--primary);opacity:.35}
.rsvp-sub{text-align:center;margin:3px 0 10px;font-size:14px;color:var(--ink2);position:relative;z-index:1}
.rsvp .card{position:relative;z-index:1;background:var(--card)}
.decor{position:absolute;width:72px;height:72px;top:-4px;pointer-events:none}.decor.l{left:-6px}.decor.r{right:-6px;transform:scaleX(-1)}
.off{display:flex;align-items:center;justify-content:center;gap:8px;margin:8px auto 0;padding:11px 18px;width:fit-content;max-width:100%;background:#E7E1DF;color:var(--ink2);font-size:14px;border-radius:99px;position:relative;z-index:1}
fieldset{border:0;padding:0;margin:12px 0 0}legend{padding:0;font-size:14px;font-weight:600;margin-bottom:8px}
.choices{display:grid;gap:8px}
.choice{font:inherit;font-size:15px;font-weight:550;text-align:left;width:100%;min-height:48px;padding:10px 14px;border-radius:12px;border:1.5px solid var(--line);background:#fff;color:var(--ink);cursor:pointer}
.choice[aria-pressed=true]{border-color:var(--primary);background:color-mix(in srgb,var(--primary) 9%,#fff);color:var(--primary)}
.chips{display:flex;flex-wrap:wrap;gap:8px}.chips .choice{width:auto;min-height:44px;padding:8px 13px;font-size:14px}
label{display:block;font-size:14px;font-weight:600;margin:12px 0 6px}
input,textarea,select{font:inherit;font-size:16px;width:100%;padding:11px 13px;border-radius:12px;border:1.5px solid var(--line);background:#fff;color:#2a2018}
textarea{min-height:72px;resize:vertical}
input:focus,textarea:focus,.choice:focus-visible,.primary:focus-visible{outline:2px solid var(--primary);outline-offset:1px}
.stepper{display:flex;align-items:center;gap:14px;margin-top:6px}
.stepper button{font:inherit;width:46px;height:46px;font-size:22px;border-radius:12px;border:1.5px solid var(--line);background:#fff;color:var(--ink);cursor:pointer}
.stepper b{font-size:20px;min-width:26px;text-align:center}
.primary{font:inherit;font-weight:650;font-size:16px;width:100%;min-height:52px;margin-top:14px;border:0;border-radius:14px;background:var(--primary);color:#fff;cursor:pointer}
.primary:disabled{opacity:.55;cursor:default}
.secondary{background:transparent;color:var(--primary);border:1.5px solid var(--line)}
.err{color:#a82845;font-size:14px;margin-top:10px}
.thanks{text-align:center;padding:22px 16px}
.pass{text-align:center}.pass svg{width:176px;height:176px;max-width:100%}
.code{font:700 21px ui-monospace,Menlo,Consolas,monospace;letter-spacing:3px;margin:6px 0 2px}
.promo{position:relative;margin:26px -14px 0;padding:18px 26px 34px;text-align:center;overflow:hidden}
.promo-rule{display:flex;align-items:center;gap:10px;color:var(--gold);max-width:260px;margin:0 auto 10px;line-height:0}
.promo-rule::before,.promo-rule::after{content:"";flex:1;height:1px;background:var(--gold);opacity:.5}
.promo-rule .emblem{width:22px;height:22px;color:var(--primary)}
.promo p{margin:0}.promo .t{font-family:var(--display);font-weight:600;font-size:19px;color:var(--primary)}
.promo .cta{display:inline-flex;align-items:center;gap:8px;margin-top:11px;font-size:14px;font-weight:650;color:var(--primary);border:1.5px solid var(--primary);padding:9px 20px;border-radius:99px;text-decoration:none;min-height:42px}
.promo .apps{margin-top:8px;font-size:12.5px}
.foot{position:absolute;bottom:-30px;width:92px;height:116px;pointer-events:none}.foot.left{left:-22px}.foot.right{right:-22px}
.promo>*:not(.foot){position:relative;z-index:1}
.t-minimal .corner,.t-minimal .decor,.t-minimal .foot{display:none}
.t-royal .invite{outline:1px solid var(--gold);outline-offset:-7px}
.hidden{display:none!important}
.skeleton{height:110px;border-radius:14px;background:var(--line);animation:p 1.2s ease-in-out infinite}
@keyframes p{50%{opacity:.5}}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
"""

_ICON = {
    "cal": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.700" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3.500" y="5" width="17" height="15.500" rx="2"/><path d="M3.500 10h17M8 3v4M16 3v4M8 14h2M14 14h2M8 17h2"/></svg>',
    "pin": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.700" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 21.500s7-6.300 7-11.500a7 7 0 1 0-14 0c0 5.200 7 11.500 7 11.500z"/><circle cx="12" cy="10" r="2.500"/></svg>',
    "nav": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 3 3 10.500l7.500 3 3 7.500z"/></svg>',
    "user": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.700" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="8" r="4"/><path d="M4.500 21c.8-4.200 3.800-6.500 7.500-6.500s6.700 2.300 7.500 6.500"/></svg>',
    "phone": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.700" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 16.500v3a2 2 0 0 1-2.200 2A18 18 0 0 1 2.500 5.200 2 2 0 0 1 4.500 3h3a2 2 0 0 1 2 1.700l.5 3a2 2 0 0 1-.6 1.800L8 11a14 14 0 0 0 5 5l1.500-1.400a2 2 0 0 1 1.800-.6l3 .5a2 2 0 0 1 1.700 2z"/></svg>',
    "arrow": '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 12h15M13 6l6 6-6 6"/></svg>',
}


def _theme_css(design, theme: Theme) -> str:
    # Colours were validated as #RRGGBB when saved, so they are safe inside
    # <style>. Unchanged defaults give way to the theme; a real choice wins.
    primary = theme.primary if design.primary_color.upper() == DEFAULT_PRIMARY.upper() else design.primary_color
    accent = theme.accent if design.accent_color.upper() == DEFAULT_ACCENT.upper() else design.accent_color
    custom_bg = design.background_color.upper() != DEFAULT_BACKGROUND.upper()
    page = design.background_color if custom_bg else theme.background
    fade = design.background_color if custom_bg else _first_colour(theme.background)
    return (
        ":root{"
        f"--primary:{primary};--gold:{accent};--page:{page};--fade:{fade};--card:{theme.card};--panel:{theme.panel};"
        "--ink:#2a2018;--ink2:#6b5d50;--line:rgba(120,80,60,.22);"
        f"--display:{_FONTS.get(design.font, _PLAYFAIR)}"
        "}"
    )


def _first_colour(css_gradient: str) -> str:
    start = css_gradient.find("#")
    return css_gradient[start:start + 7] if start >= 0 else "#FFFFFF"


def _csp(nonce: str, api_origin: str, cover: str | None) -> str:
    images = ["'self'", "data:"]
    if cover:
        parsed = urlparse(cover)
        if parsed.scheme in ("http", "https") and parsed.netloc:
            images.append(f"{parsed.scheme}://{parsed.netloc}")
    return (
        "default-src 'none'; "
        f"script-src 'nonce-{nonce}'; "
        "style-src 'unsafe-inline'; "
        "font-src 'self'; "
        f"img-src {' '.join(images)}; "
        f"connect-src 'self' {api_origin}; "
        "base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
    )


def _date_text(meta: dict) -> str:
    day = meta["date"]
    text = f"{day:%A}, {day.day} {day:%B %Y}"
    end = meta.get("end_date")
    if end and end != day:
        text = f"{day.day} {day:%B} – {end.day} {end:%B %Y}"
    elif meta.get("start_time"):
        t = meta["start_time"]
        text += f" · {(t.hour % 12) or 12}:{t.minute:02d} {'AM' if t.hour < 12 else 'PM'}"
    return text


def _place_text(meta: dict) -> str:
    """Venue then address, without repeating the name when the address starts with it."""
    name = (meta.get("venue_name") or "").strip()
    address = (meta.get("venue_address") or "").strip()
    if name and address.lower().startswith(name.lower()):
        address = address[len(name):].lstrip(" ,")
    return ", ".join(p for p in (name, address) if p)


def _short_place(meta: dict) -> str:
    name = meta.get("venue_name")
    address = (meta.get("venue_address") or "").strip()
    if name and address:
        return f"{name}, {address.split(',')[-2].strip() if address.count(',') >= 2 else address}"
    return name or address


def _og_tags(meta: dict, page_url: str) -> str:
    """Event only. This link can be forwarded, so a guest's name doesn't belong in its preview."""
    title = meta["title"]
    place = _short_place(meta)
    description = _date_text(meta) + (f" · {place}" if place else "")
    host = meta.get("host_name")
    if host:
        description = f"{host} invite you. {description}"
    image = meta.get("cover") or f"{settings.TYOHAAR_WEBSITE_URL.rstrip('/')}/logo.png"
    tags = {
        "og:type": "website",
        "og:site_name": "Tyohaar",
        "og:title": f"You're invited: {title}",
        "og:description": description,
        "og:image": image,
    }
    if page_url:
        tags["og:url"] = page_url
    html = "".join(f'<meta property="{k}" content="{escape(v, quote=True)}">' for k, v in tags.items())
    html += '<meta name="twitter:card" content="summary_large_image">'
    html += f'<meta name="description" content="{escape(description, quote=True)}">'
    return html


def _document(*, title: str, head: str, theme: str, body: str, script: str, csp: str, nonce: str, css_class: str = "") -> HTMLResponse:
    html = (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
        '<meta name="robots" content="noindex,nofollow"><meta name="referrer" content="no-referrer">'
        f"<title>{escape(title)}</title>{head}<style>{_FONT_FACES}{theme}{_CSS}</style></head>"
        f'<body class="{css_class}">{body}'
        + (f'<script nonce="{nonce}">{script}</script>' if script else "")
        + "</body></html>"
    )
    return HTMLResponse(
        html,
        headers={"Content-Security-Policy": csp, "Cache-Control": "no-store", "X-Robots-Tag": "noindex, nofollow"},
    )


def problem_page(title: str, text: str) -> HTMLResponse:
    """Invalid, revoked, unpublished: said plainly, with nothing about the event."""
    from app.schemas.events import InvitationDesign
    from app.services.invitations.guest_themes import THEMES

    nonce = secrets.token_urlsafe(16)
    body = (
        '<div class="wrap" style="padding-top:18vh;text-align:center"><div class="eyebrow">Tyohaar</div>'
        f'<h1 style="font-size:30px">{escape(title)}</h1><p class="muted">{escape(text)}</p></div>'
    )
    return _document(
        title=f"{title} — Tyohaar", head="", theme=_theme_css(InvitationDesign(), THEMES["wedding"]), body=body, script="",
        csp=_csp(nonce, "'self'", None), nonce=nonce,
    )


def invitation_page(meta: dict, *, page_url: str, api_origin: str, token: str) -> HTMLResponse:
    design = meta["design"]
    nonce = secrets.token_urlsafe(16)
    cover = meta.get("cover")
    place = _place_text(meta)
    label = meta.get("label") or "Celebration"
    theme = theme_for(meta.get("event_type"), label)
    eyebrow = meta.get("heading") or theme.eyebrow
    is_preview = meta["kind"] == "preview"

    picture = f'<img src="{escape(cover, quote=True)}" alt="" fetchpriority="high">' if cover else theme.scene
    corners = ""
    if theme.corner:
        corners = theme.corner if "keep" in theme.corner[:40] else (
            theme.corner + theme.corner.replace('class="corner', 'class="corner flip', 1)
        )
    tagline = design.tagline
    invite = (
        f'<div class="invite{" has-corner" if corners else ""}">'
        f'<svg class="arch" viewBox="0 0 200 44" aria-hidden="true" focusable="false"><path d="{theme.arch}"/></svg>'
        f'<div class="emblem-wrap">{theme.emblem}</div>'
        f'<div class="eyebrow"><span>{escape(eyebrow)}</span></div>'
        f"<h1>{escape(meta['title'])}</h1>"
        + (f'<div class="ribbon">{escape(tagline)}</div>' if tagline else "")
        + (f'<p class="host">hosted by {escape(meta["host_name"])}</p>' if meta.get("host_name") else "")
        + f'<div class="orn"><span>{theme.divider}</span></div>'
        + '<div class="facts">'
        + f'<div class="fact"><span class="ico">{_ICON["cal"]}</span><span>{escape(_date_text(meta))}</span></div>'
        + (f'<div class="fact"><span class="ico">{_ICON["pin"]}</span><span>{escape(place)}</span></div>' if place else "")
        + "</div>"
        + corners
        + "</div>"
    )
    website = settings.TYOHAAR_WEBSITE_URL.rstrip("/")
    apps = []
    if settings.TYOHAAR_ANDROID_APP_URL:
        apps.append(f'<a href="{escape(settings.TYOHAAR_ANDROID_APP_URL, quote=True)}" rel="noopener noreferrer" target="_blank">Android</a>')
    if settings.TYOHAAR_IOS_APP_URL:
        apps.append(f'<a href="{escape(settings.TYOHAAR_IOS_APP_URL, quote=True)}" rel="noopener noreferrer" target="_blank">iPhone</a>')
    # After everything. It must never sit between the invitation and the answer.
    promo = (
        '<footer class="promo">'
        + theme.foot_decor
        + (f'<div class="promo-rule">{theme.promo_icon}</div>' if theme.promo_icon else '<div class="promo-rule"></div>')
        + '<p class="t">Planning your own celebration?</p>'
        '<p class="small">Create beautiful invitations and manage your guests with Tyohaar.</p>'
        f'<a class="cta" href="{escape(website, quote=True)}" rel="noopener noreferrer" target="_blank">Explore Tyohaar {_ICON["arrow"]}</a>'
        + (f'<p class="apps small">Get the app: {" · ".join(apps)}</p>' if apps else "")
        + "</footer>"
    )
    body = (
        ('<div class="banner">Preview · Responses are turned off</div>' if is_preview else "")
        + f'<div class="scene">{picture}</div>'
        + '<main class="wrap">'
        + invite
        + '<div id="root"><div class="sec"><div class="skeleton"></div></div></div>'
        + f"<noscript><p class=\"muted\" style=\"padding-top:18px\">{escape(label)}. Turn on JavaScript to respond to this invitation.</p></noscript>"
        + promo
        + "</main>"
    )
    panel_decor = ""
    if theme.panel_decor:
        panel_decor = theme.panel_decor.replace('class="decor"', 'class="decor l"') + theme.panel_decor.replace('class="decor"', 'class="decor r"')
    config = {
        "api": f"{api_origin.rstrip('/')}/i/_api",
        "token": token,
        "preview": is_preview,
        "calendar": "" if is_preview else f"{token}/calendar.ics",
        "split": theme.split_when_where,
        "inlineContact": theme.inline_contact,
        "divider": theme.divider,
        "icons": {k: v for k, v in _ICON.items()},
        "panelDecor": panel_decor,
    }
    script = "var TY=" + json.dumps(config, ensure_ascii=False).replace("<", "\\u003c") + ";" + _SCRIPT
    title_class = "italic-title" if theme.title_italic or design.template == "floral" else ""
    return _document(
        title=f"{meta['title']} — you're invited",
        head=_og_tags(meta, page_url),
        theme=_theme_css(design, theme),
        body=body,
        script=script,
        csp=_csp(nonce, api_origin, cover),
        nonce=nonce,
        css_class=f"t-{design.template} e-{theme.key} {title_class}".strip(),
    )


_SCRIPT = r"""
(function(){
var root=document.getElementById('root'),page=null,state={},note='',editing=false,started=false,sending=false;
var DIET={vegetarian:'Vegetarian',non_vegetarian:'Non-vegetarian',jain:'Jain',vegan:'Vegan',other:'Other'};
function h(tag,attrs,kids){var e=document.createElement(tag);attrs=attrs||{};
  Object.keys(attrs).forEach(function(k){var v=attrs[k];if(v===null||v===undefined||v===false)return;
    if(k==='text')e.textContent=v;else if(k==='on'){Object.keys(v).forEach(function(n){e.addEventListener(n,v[n]);});}
    else if(k==='cls')e.className=v;else e.setAttribute(k,v===true?'':v);});
  (kids||[]).forEach(function(c){if(c)e.appendChild(c);});return e;}
function ico(name){var s=h('span',{cls:'ico'});s.innerHTML=TY.icons[name];return s;}
function api(method,path,body){var headers={'X-Invite-Token':TY.token};if(body)headers['Content-Type']='application/json';
  return fetch(TY.api+'/'+path,{method:method,headers:headers,cache:'no-store',credentials:'omit',body:body?JSON.stringify(body):undefined})
    .then(function(r){return r.text().then(function(t){var j={};try{j=t?JSON.parse(t):{};}catch(e){}return{status:r.status,body:j};});});}
function msg(r,fallback){return(r.body&&r.body.error&&r.body.error.message)||fallback;}
function time(t){if(!t)return'';var p=t.split(':'),n=+p[0];return((n%12)||12)+':'+p[1]+(n<12?' AM':' PM');}
function date(d,opts){return new Date(d+'T00:00:00').toLocaleDateString(undefined,opts||{weekday:'long',day:'numeric',month:'long',year:'numeric'});}
function when(o){var s=date(o.function_date||o.celebration_date),a=time(o.start_time),b=time(o.end_time);
  return s+(a?' · '+a+(b?' – '+b:''):'');}
function card(kids,cls){return h('div',{cls:'card '+(cls||'')},kids);}
function section(title,kids){return h('section',{cls:'sec'},[title?h('h2',{text:title}):null].concat(kids));}
function notice(title,text,retry){root.textContent='';root.appendChild(h('div',{cls:'sec'},[card([h('h2',{text:title}),h('p',{cls:'muted',text:text}),
  retry?h('button',{cls:'primary',text:'Try again',on:{click:load}}):null])]));}
function directions(url){return h('a',{cls:'pill',href:url,target:'_blank',rel:'noopener noreferrer'},[ico('nav'),h('span',{text:'Get directions'})]);}
function placeOf(name,address){if(name&&address&&address.toLowerCase().indexOf(name.toLowerCase())===0)address=address.slice(name.length).replace(/^[ ,]+/,'');
  return[name,address].filter(Boolean).join(', ');}

function key(g,f){return(g||'')+'|'+(f||'');}
function seed(){state={};
  page.members.forEach(function(m){(m.responses||[]).forEach(function(r){
    if(r.status==='pending'||r.status==='no_response')return;
    state[key(m.id,r.function_id)]={status:r.status,attendee_count:r.attendee_count||1,dietary_type:r.dietary_type,
      meal_selection:r.meal_selection,allergies:r.allergies,special_requirements:r.special_requirements,answers:r.answers||{}};});});
  note=page.guest_note||'';}
function touched(){if(started||TY.preview)return;started=true;api('POST','activity',{type:'rsvp_started'}).catch(function(){});}
function slots(){ // one entry per thing the guest answers
  var fns=page.functions.filter(function(f){return f.is_open;}),out=[];
  var people=page.response_mode==='individual'?page.members:page.members.slice(0,1);
  people.forEach(function(m){
    if(page.functions.length){fns.forEach(function(f){if(page.response_mode==='group'||m.function_ids.indexOf(f.id)>=0)out.push({m:m,f:f});});}
    else out.push({m:m,f:null});});
  return out;}
function limit(m){if(page.response_mode==='group')return page.capacity;return Math.min(1+m.plus_ones_allowed,page.capacity);}

function renderWhenWhere(){var e=page.event,place=placeOf(e.venue_name,e.venue_address),t=time(e.start_time);
  if(TY.split){
    return section('',[card([h('div',{cls:'ww'},[
      h('div',{cls:'ww-col'},[h('div',{cls:'ww-head'},[ico('cal'),h('span',{text:'When'})]),
        h('div',{text:date(e.celebration_date,{weekday:'short',day:'numeric',month:'short',year:'numeric'})}),t?h('div',{text:t}):null]),
      place?h('div',{cls:'ww-col'},[h('div',{cls:'ww-head'},[ico('pin'),h('span',{text:'Where'})]),h('div',{text:place})]):null,
      e.map_url?directions(e.map_url):null])])]);}
  return section('',[card([h('h3',{text:'When & Where',style:'margin-bottom:8px'}),h('div',{cls:'ww'},[
    h('div',{cls:'ww-rows'},[h('div',{cls:'fact'},[ico('cal'),h('span',{text:when(e)})]),
      place?h('div',{cls:'fact'},[ico('pin'),h('span',{text:place})]):null]),
    e.map_url?directions(e.map_url):null])])]);}
function renderDetails(){var out=[],e=page.event,fns=page.functions;
  if(e.message){out.push(h('p',{cls:'message',text:e.message}));out.push(h('div',{cls:'orn',style:'margin-bottom:0'},[h('span',{text:TY.divider})]));}
  if(fns.length){out.push(section(fns.length>1?'The celebrations':'The celebration',fns.map(function(f){
    var venue=placeOf(f.venue_name||e.venue_name,f.venue_address||e.venue_address);
    var map=f.map_url||e.map_url;
    return card([h('div',{cls:'row'},[h('h3',{text:f.name}),f.is_cancelled?h('span',{cls:'tag',text:'Cancelled'}):null]),
      h('div',{cls:'when',text:when(f)}),venue?h('div',{cls:'muted',text:venue}):null,
      f.description?h('p',{cls:'small',style:'margin:5px 0 0',text:f.description}):null,
      f.dress_code?h('p',{cls:'small',style:'margin:4px 0 0',text:'Dress code: '+f.dress_code}):null,
      map&&!f.is_cancelled?directions(map):null],'fn');})));}
  else out.push(renderWhenWhere());
  return out;}
function renderContact(){var e=page.event,p=e.contact_phone,name=e.contact_name;if(!p&&!name)return null;
  var call=p?h('a',{href:'tel:'+p.replace(/[^+0-9]/g,''),text:p}):null;
  var body=TY.inlineContact
    ?h('div',{cls:'contact inline'},[p?ico('phone'):ico('user'),name?h('span',{text:name}):null,name&&p?h('span',{cls:'sep'}):null,call])
    :h('div',{cls:'contact'},[name?h('div',{cls:'fact'},[ico('user'),h('span',{text:name})]):null,p?h('div',{cls:'fact'},[ico('phone'),call]):null]);
  return section('',[card([h('h3',{text:'Questions?',style:'font-size:18px;margin-bottom:7px'}),body])]);}

function choiceRow(slot,cur,set){var c=page.rsvp,opts=[['attending',"Yes, I'll attend"],['declined',"Sorry, I can't attend"]];
  if(c.allow_maybe)opts.splice(1,0,['maybe','Maybe / Not sure yet']);
  return h('div',{cls:'choices'},opts.map(function(o){return h('button',{cls:'choice',type:'button','aria-pressed':String(cur.status===o[0]),text:o[1],
    on:{click:function(){touched();cur.status=o[0];set();}}});}));}
function stepper(label,cur,max,set){return h('div',{},[h('label',{text:label}),h('div',{cls:'stepper'},[
  h('button',{type:'button','aria-label':'Fewer',text:'−',on:{click:function(){if((cur.attendee_count||1)>1){cur.attendee_count=(cur.attendee_count||1)-1;set();}}}}),
  h('b',{text:String(cur.attendee_count||1)}),
  h('button',{type:'button','aria-label':'More',text:'+',on:{click:function(){if((cur.attendee_count||1)<max){cur.attendee_count=(cur.attendee_count||1)+1;set();}}}}),
  h('span',{cls:'small',text:'of '+max})])]);}
function field(tag,label,value,on,attrs){var id='f'+Math.random().toString(36).slice(2,9);
  var input=h(tag,Object.assign({id:id,on:{input:function(ev){touched();on(ev.target.value);}}},attrs||{}));input.value=value||'';
  return h('div',{},[h('label',{for:id,text:label}),input]);}
function foodFields(cur,set){var c=page.rsvp,out=[];
  if(c.ask_food){out.push(h('fieldset',{},[h('legend',{text:'Food preference'}),h('div',{cls:'chips'},Object.keys(DIET).map(function(d){
    return h('button',{cls:'choice',type:'button','aria-pressed':String(cur.dietary_type===d),text:DIET[d],on:{click:function(){touched();cur.dietary_type=cur.dietary_type===d?null:d;set();}}});}))]));
    if(c.meal_options.length)out.push(h('fieldset',{},[h('legend',{text:'Meal'}),h('div',{cls:'chips'},c.meal_options.map(function(o){
      return h('button',{cls:'choice',type:'button','aria-pressed':String(cur.meal_selection===o),text:o,on:{click:function(){touched();cur.meal_selection=cur.meal_selection===o?null:o;set();}}});}))]));
    if(c.ask_allergies)out.push(field('input','Allergies or dietary restrictions (optional)',cur.allergies,function(v){cur.allergies=v;},{maxlength:500}));}
  if(c.ask_special_requirements)out.push(field('input','Anything we should arrange for you? (optional)',cur.special_requirements,function(v){cur.special_requirements=v;},{maxlength:1000}));
  c.questions.forEach(function(q){cur.answers=cur.answers||{};
    if(q.kind==='text'){out.push(field('input',q.label+(q.required?'':' (optional)'),cur.answers[q.id],function(v){cur.answers[q.id]=v;},{maxlength:1000}));return;}
    var opts=q.kind==='yes_no'?[['yes','Yes'],['no','No']]:q.options.map(function(o){return[o,o];});
    out.push(h('fieldset',{},[h('legend',{text:q.label}),h('div',{cls:'chips'},opts.map(function(o){
      return h('button',{cls:'choice',type:'button','aria-pressed':String(cur.answers[q.id]===o[0]),text:o[1],on:{click:function(){touched();cur.answers[q.id]=o[0];set();}}});}))]));});
  return out;}

function panel(sub,kids){var p=h('section',{cls:'rsvp'},[h('div',{cls:'rsvp-head',text:'RSVP'}),sub?h('p',{cls:'rsvp-sub',text:sub}):null].concat(kids));
  if(TY.panelDecor){var d=document.createElement('div');d.innerHTML=TY.panelDecor;while(d.firstChild)p.insertBefore(d.firstChild,p.firstChild);}
  return p;}
function renderForm(){var all=slots(),multi=all.length>1,formBits=[];
  function redraw(){renderAll();}
  // Attendance is one question when there's only one function; food only once it's a yes/maybe.
  all.forEach(function(s){var k=key(s.m.id,s.f&&s.f.id),cur=state[k]=state[k]||{};
    var title=[page.response_mode==='individual'?s.m.name:null,s.f&&multi?s.f.name:null].filter(Boolean).join(' — ');
    var kids=[title?h('h3',{text:title,style:'margin-bottom:9px'}):null,choiceRow(s,cur,redraw)];
    if(cur.status==='attending'&&page.rsvp.ask_attendee_count&&limit(s.m)>1)kids.push(stepper('How many people, including you?',cur,limit(s.m),redraw));
    if(cur.status==='attending'||cur.status==='maybe')foodFields(cur,redraw).forEach(function(x){kids.push(x);});
    formBits.push(card(kids));});
  var err=h('div',{cls:'err hidden',role:'alert'});
  var answered=all.every(function(s){return state[key(s.m.id,s.f&&s.f.id)].status;});
  var btn=h('button',{cls:'primary',type:'button',disabled:!answered||sending,text:sending?'Sending…':(page.has_responded?'Update my response':'Send my response'),
    on:{click:function(){submit(all,err);}}});
  var tail=[field('textarea','A note for the host (optional)',note,function(v){note=v;},{maxlength:1000}),btn,err];
  var sub=page.response_mode==='group'?('Your response for '+page.members.map(function(m){return m.name;}).join(', ')):'Will you join us?';
  return panel(sub,formBits.concat([card(tail)]));}
function submit(all,err){if(sending)return;sending=true;err.classList.add('hidden');
  var responses=all.map(function(s){var cur=state[key(s.m.id,s.f&&s.f.id)];
    return{guest_id:s.m.id,function_id:s.f?s.f.id:null,status:cur.status,attendee_count:cur.status==='attending'?(cur.attendee_count||1):null,
      dietary_type:cur.dietary_type||null,meal_selection:cur.meal_selection||null,allergies:cur.allergies||null,
      special_requirements:cur.special_requirements||null,answers:cur.answers||null};});
  api('POST','rsvp',{responses:responses,note:note||null}).then(function(r){sending=false;
    if(r.status===200){page=r.body.data;seed();editing=false;renderAll(true);var t=root.querySelector('.thanks');if(t)t.scrollIntoView({behavior:'smooth',block:'center'});return;}
    renderAll();showErr(r.status===409||r.status===422||r.status===400?msg(r,'Please check your answers.'):msg(r,'We could not save your response. Please try again.'));
  }).catch(function(){sending=false;renderAll();showErr('No connection. Your response was not sent, so please try again.');});}
function showErr(text){var e=root.querySelector('.err');if(e){e.textContent=text;e.classList.remove('hidden');e.scrollIntoView({block:'center'});}}

function renderThanks(justSent){var kids=[h('h2',{text:justSent?'Thank you for responding!':'You have responded'}),
  h('p',{cls:'muted',style:'margin:0 0 6px',text:'We look forward to celebrating with you.'})];
  var lines=[];page.members.forEach(function(m){(m.responses||[]).forEach(function(r){if(r.status==='pending'||r.status==='no_response')return;
    var f=null;page.functions.forEach(function(x){if(x.id===r.function_id)f=x;});
    var who=page.response_mode==='individual'?m.name+' · ':'';if(page.response_mode==='group'&&!m.is_self)return;
    lines.push(who+(f?f.name+': ':'')+({attending:'Attending'+(r.attendee_count>1?' ('+r.attendee_count+')':''),maybe:'Maybe',declined:'Not attending'}[r.status]));});});
  lines.forEach(function(l){kids.push(h('div',{cls:'small',text:l}));});
  if(page.can_respond&&page.rsvp.allow_edit)kids.push(h('button',{cls:'primary secondary',type:'button',text:'Change my response',on:{click:function(){editing=true;renderAll();}}}));
  return h('section',{cls:'sec'},[card(kids,'thanks')]);}

function renderClaim(){var d={name:'',phone:'',email:'',website:''},err=h('div',{cls:'err hidden',role:'alert'}),send;
  send=h('button',{cls:'primary',type:'button',text:'Continue',on:{click:function(){send.disabled=true;send.textContent='One moment…';err.classList.add('hidden');
    api('POST','claim',d).then(function(r){if(r.status===200){location.replace(r.body.data.url);return;}
      send.disabled=false;send.textContent='Continue';err.textContent=msg(r,'Please check your details and try again.');err.classList.remove('hidden');
    }).catch(function(){send.disabled=false;send.textContent='Continue';err.textContent='No connection. Please try again.';err.classList.remove('hidden');});}}});
  var trap=field('input','Leave this empty',d.website,function(v){d.website=v;},{tabindex:'-1',autocomplete:'off'});trap.className='hidden';
  return panel('Will you join us?',[card([h('p',{cls:'muted',style:'margin:0',text:'Tell us who you are so the host knows to expect you.'}),
    field('input','Your name',d.name,function(v){d.name=v;},{autocomplete:'name',maxlength:200}),
    field('input','Mobile number',d.phone,function(v){d.phone=v;},{type:'tel',autocomplete:'tel',maxlength:20,inputmode:'tel'}),
    trap,send,err])]);}
function renderPreviewPanel(){var s=ico('cal');return panel('',[h('div',{cls:'off'},[s,h('span',{text:'RSVP unavailable in preview'})])]);}

function renderPasses(){if(!page.passes.length)return null;
  return section(page.passes.length>1?'Your entry passes':'Your entry pass',page.passes.map(function(p){
    var qr=h('div',{role:'img','aria-label':'Entry QR code for '+p.name});qr.innerHTML=p.qr_svg;
    return card([page.passes.length>1?h('h3',{text:p.name}):null,qr,h('div',{cls:'code',text:p.entry_code}),
      h('p',{cls:'small',style:'margin:2px 0 0',text:'Show this at the entrance. It is personal to you.'})],'pass');}));}
function renderExtras(){var e=page.event,kids=[];
  if(e.instructions)kids.push(card([h('h3',{text:'Good to know',style:'margin-bottom:5px'}),h('p',{cls:'muted',style:'white-space:pre-line;margin:0',text:e.instructions})]));
  if(TY.calendar)kids.push(card([h('a',{href:TY.calendar,style:'display:flex;align-items:center;gap:9px;font-weight:600;font-size:14px;text-decoration:none;min-height:30px'},[ico('cal'),h('span',{text:'Add to calendar'})])]));
  return kids.length?h('section',{cls:'sec'},kids):null;}

function renderAll(justSent){root.textContent='';
  renderDetails().forEach(function(n){root.appendChild(n);});
  var c=renderContact();if(c)root.appendChild(c);
  if(page.kind==='preview')root.appendChild(renderPreviewPanel());
  else if(page.kind==='general'){if(page.can_respond)root.appendChild(renderClaim());else if(page.closed_reason)root.appendChild(section('',[card([h('p',{cls:'muted',style:'margin:0',text:page.closed_reason})])]));}
  else if(page.can_respond&&(editing||!page.has_responded))root.appendChild(renderForm());
  else if(page.has_responded)root.appendChild(renderThanks(justSent));
  else if(page.closed_reason)root.appendChild(section('',[card([h('p',{cls:'muted',style:'margin:0',text:page.closed_reason})])]));
  var passes=renderPasses();if(passes)root.appendChild(passes);
  var extras=renderExtras();if(extras)root.appendChild(extras);}

function load(){root.textContent='';root.appendChild(h('div',{cls:'sec'},[h('div',{cls:'skeleton'})]));
  api('GET',TY.preview?'preview':'view').then(function(r){
    if(r.status===200){page=r.body.data;seed();renderAll();return;}
    if(r.status===404)notice('Invitation not found','This link is not valid. It may have been replaced by a newer one, so please ask your host to send it again.');
    else if(r.status===429)notice('Please wait a moment','Too many attempts. Try again in a minute.',true);
    else notice('Something went wrong',msg(r,'We could not load this invitation.'),true);
  }).catch(function(){notice('No connection','Check your internet connection and try again.',true);});}
// Counted as a visit only once it's on screen: a tab restored in the background isn't one.
if(document.visibilityState==='visible')load();
else document.addEventListener('visibilitychange',function once(){if(document.visibilityState==='visible'){document.removeEventListener('visibilitychange',once);load();}});
})();
"""
