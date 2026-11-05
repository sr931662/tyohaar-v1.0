"""
The guest's invitation page: what opens from the WhatsApp message.

Should feel like a card someone made, not a website. No app, no account, no
third-party scripts or fonts: a guest's personal link is a credential, so
nothing on this page loads from anywhere but our own API and the event's cover
image.

Two layers:

* **Server-rendered shell** — the hero, date, venue and Open Graph tags are in
  the HTML response itself. WhatsApp's crawler runs no script, so this is the
  only thing it can build a preview from. The preview carries the event, never
  the guest: the same link may be forwarded.
* **Script** — once the page is actually on screen it calls ``/i/_api/view`` for
  the guest's own details. That call is what counts as a visit, which is why a
  crawler fetching the preview doesn't look like a guest opening it.

Every server string reaches the DOM through ``textContent`` or html.escape. The
only HTML injected is the QR SVG this server generated.
"""

from __future__ import annotations

import json
import secrets
from html import escape
from urllib.parse import urlparse

from fastapi.responses import HTMLResponse

from app.core.config import settings

_FONTS = {
    "serif": '"Iowan Old Style","Palatino Linotype",Palatino,"Book Antiqua",Georgia,serif',
    "traditional": '"Noto Serif Devanagari","Palatino Linotype",Palatino,Georgia,"Times New Roman",serif',
    "modern": '-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif',
}

_CSS = """
*{box-sizing:border-box}html,body{margin:0}html{-webkit-text-size-adjust:100%}
body{background:var(--bg);color:var(--ink);font:16px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif}
a{color:var(--primary)}
.wrap{max-width:480px;margin:0 auto;padding:0 18px}
.hero{position:relative;background:var(--primary);color:#fff;text-align:center;overflow:hidden}
.hero img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}
.hero:has(img)::after{content:"";position:absolute;inset:0;background:linear-gradient(180deg,rgba(0,0,0,.28),rgba(0,0,0,.62))}
.hero-in{position:relative;z-index:1;max-width:480px;margin:0 auto;padding:64px 26px 54px;min-height:420px;display:flex;flex-direction:column;justify-content:flex-end}
.t-royal .hero-in,.t-floral .hero-in{padding-top:72px}
.eyebrow{font-size:11.5px;letter-spacing:2.6px;text-transform:uppercase;font-weight:600;opacity:.92}
h1{font-family:var(--display);font-weight:500;font-size:clamp(34px,10vw,46px);line-height:1.12;margin:12px 0 10px;overflow-wrap:anywhere}
.host{font-family:var(--display);font-size:18px;font-style:italic;opacity:.95;margin:0 0 16px}
.rule{width:44px;height:1px;background:var(--accent);margin:0 auto 16px}
.hero-meta{font-size:15px;opacity:.96}
.t-royal .hero-in{outline:1px solid color-mix(in srgb,var(--accent) 70%,transparent);outline-offset:-14px}
.t-floral h1{font-style:italic}
.t-minimal .hero{background:var(--bg);color:var(--ink)}.t-minimal .hero:has(img){color:#fff}
.sec{padding:30px 0 0}
.card{background:var(--surface);border:1px solid var(--line);border-radius:16px;padding:20px}
.card+.card{margin-top:12px}
h2{font-family:var(--display);font-weight:500;font-size:24px;margin:0 0 12px;line-height:1.25}
h3{font-size:16px;margin:0;font-weight:650}
.message{font-family:var(--display);font-size:18.5px;line-height:1.6;text-align:center;white-space:pre-line;padding:30px 6px 0;margin:0}
.muted{color:var(--ink2);font-size:14.5px}.small{font-size:13px;color:var(--ink2)}
.row{display:flex;justify-content:space-between;gap:12px;align-items:baseline;flex-wrap:wrap}
.fn+.fn{margin-top:12px}.fn .when{color:var(--primary);font-weight:600;font-size:14px;margin:4px 0 2px}
.linkbtn{display:inline-block;margin-top:10px;font-size:14px;font-weight:600;text-decoration:none;color:var(--primary);border:1px solid var(--line);padding:9px 14px;border-radius:10px;min-height:40px}
.tag{display:inline-block;font-size:11.5px;font-weight:600;padding:3px 9px;border-radius:99px;background:color-mix(in srgb,var(--accent) 16%,var(--surface));color:var(--ink)}
.tag.bad{background:#f8e1e6;color:#8f2340}
fieldset{border:0;padding:0;margin:14px 0 0}legend{padding:0;font-size:14px;font-weight:600;margin-bottom:8px}
.choices{display:grid;gap:8px}
.choice{font:inherit;font-size:15.5px;font-weight:550;text-align:left;width:100%;min-height:50px;padding:12px 14px;border-radius:12px;border:1.5px solid var(--line);background:var(--surface);color:var(--ink);cursor:pointer}
.choice[aria-pressed=true]{border-color:var(--primary);background:color-mix(in srgb,var(--primary) 9%,var(--surface));color:var(--primary)}
.chips{display:flex;flex-wrap:wrap;gap:8px}.chips .choice{width:auto;min-height:44px;padding:9px 14px;font-size:14.5px}
label{display:block;font-size:14px;font-weight:600;margin:14px 0 6px}
input,textarea,select{font:inherit;font-size:16px;width:100%;padding:12px 13px;border-radius:12px;border:1.5px solid var(--line);background:#fff;color:#2a2018}
textarea{min-height:76px;resize:vertical}
input:focus,textarea:focus,select:focus,.choice:focus-visible,.primary:focus-visible{outline:2px solid var(--primary);outline-offset:1px}
.stepper{display:flex;align-items:center;gap:14px;margin-top:6px}
.stepper button{font:inherit;width:46px;height:46px;font-size:22px;border-radius:12px;border:1.5px solid var(--line);background:var(--surface);color:var(--ink);cursor:pointer}
.stepper b{font-size:20px;min-width:26px;text-align:center}
.primary{font:inherit;font-weight:650;font-size:16.5px;width:100%;min-height:54px;margin-top:18px;border:0;border-radius:14px;background:var(--primary);color:#fff;cursor:pointer}
.primary:disabled{opacity:.55;cursor:default}
.err{color:#a82845;font-size:14px;margin-top:12px}
.thanks{text-align:center;padding:28px 20px}
.thanks h2{margin-bottom:6px}
.pass{text-align:center}.pass svg{width:190px;height:190px;max-width:100%}
.code{font:700 22px ui-monospace,Menlo,Consolas,monospace;letter-spacing:3px;margin:8px 0 2px}
.promo{margin:38px 0 0;padding:22px 0 34px;border-top:1px solid var(--line);text-align:center}
.promo p{margin:0}.promo .t{font-family:var(--display);font-size:17px}
.promo a.cta{display:inline-block;margin-top:10px;font-size:14px;font-weight:600;color:var(--primary)}
.promo .apps{margin-top:6px;font-size:12.5px}
.banner{background:var(--ink);color:#fff;text-align:center;font-size:13px;padding:9px 12px}
.hidden{display:none!important}
.skeleton{height:120px;border-radius:16px;background:var(--line);animation:p 1.2s ease-in-out infinite}
@keyframes p{50%{opacity:.5}}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
"""

_PROMO_NOTE = "Create beautiful invitations and manage your guests with Tyohaar."


def _theme(design) -> str:
    # Validated as #RRGGBB when saved, so these are safe inside <style>.
    return (
        ":root{"
        f"--primary:{design.primary_color};--accent:{design.accent_color};--bg:{design.background_color};"
        "--surface:#fff;--ink:#2a2018;--ink2:#6b5d50;--line:rgba(42,32,24,.13);"
        f"--display:{_FONTS.get(design.font, _FONTS['serif'])}"
        "}"
    )


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
        f"<title>{escape(title)}</title>{head}<style>{theme}{_CSS}</style></head>"
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

    nonce = secrets.token_urlsafe(16)
    body = (
        '<div class="wrap" style="padding-top:18vh;text-align:center"><div class="eyebrow">Tyohaar</div>'
        f'<h1 style="font-size:32px">{escape(title)}</h1><p class="muted">{escape(text)}</p></div>'
    )
    return _document(
        title=f"{title} — Tyohaar", head="", theme=_theme(InvitationDesign()), body=body, script="",
        csp=_csp(nonce, "'self'", None), nonce=nonce,
    )


def invitation_page(meta: dict, *, page_url: str, api_origin: str, token: str) -> HTMLResponse:
    design = meta["design"]
    nonce = secrets.token_urlsafe(16)
    cover = meta.get("cover")
    place = _short_place(meta)
    label = meta.get("label") or "Celebration"
    heading = meta.get("heading") or "You're invited"
    is_preview = meta["kind"] == "preview"

    hero = (
        '<header class="hero">'
        + (f'<img src="{escape(cover, quote=True)}" alt="" fetchpriority="high">' if cover else "")
        + '<div class="hero-in">'
        + f'<div class="eyebrow">{escape(heading)}</div>'
        + f"<h1>{escape(meta['title'])}</h1>"
        + (f'<p class="host">hosted by {escape(meta["host_name"])}</p>' if meta.get("host_name") else "")
        + '<div class="rule"></div>'
        + f'<div class="hero-meta">{escape(_date_text(meta))}</div>'
        + (f'<div class="hero-meta">{escape(place)}</div>' if place else "")
        + "</div></header>"
    )
    website = settings.TYOHAAR_WEBSITE_URL.rstrip("/")
    apps = []
    if settings.TYOHAAR_ANDROID_APP_URL:
        apps.append(f'<a href="{escape(settings.TYOHAAR_ANDROID_APP_URL, quote=True)}" rel="noopener noreferrer" target="_blank">Android</a>')
    if settings.TYOHAAR_IOS_APP_URL:
        apps.append(f'<a href="{escape(settings.TYOHAAR_IOS_APP_URL, quote=True)}" rel="noopener noreferrer" target="_blank">iPhone</a>')
    # After everything. It must never sit between the invitation and the answer.
    promo = (
        '<footer class="promo"><p class="t">Planning your own celebration?</p>'
        f'<p class="small">{_PROMO_NOTE}</p>'
        f'<a class="cta" href="{escape(website, quote=True)}" rel="noopener noreferrer" target="_blank">Explore Tyohaar</a>'
        + (f'<p class="apps small">Get the app: {" · ".join(apps)}</p>' if apps else "")
        + "</footer>"
    )
    body = (
        ('<div class="banner">Preview: this is what your guests will see. Responses are turned off.</div>' if is_preview else "")
        + hero
        + '<main class="wrap"><div id="root"><div class="sec"><div class="skeleton"></div></div></div>'
        + f"<noscript><p class=\"muted\" style=\"padding-top:24px\">{escape(label)}. Turn on JavaScript to respond to this invitation.</p></noscript>"
        + promo
        + "</main>"
    )
    config = {
        "api": f"{api_origin.rstrip('/')}/i/_api",
        "token": token,
        "preview": is_preview,
        "calendar": "" if is_preview else f"{token}/calendar.ics",
    }
    script = "var TY=" + json.dumps(config).replace("<", "\\u003c") + ";" + _SCRIPT
    return _document(
        title=f"{meta['title']} — you're invited",
        head=_og_tags(meta, page_url),
        theme=_theme(design),
        body=body,
        script=script,
        csp=_csp(nonce, api_origin, cover),
        nonce=nonce,
        css_class=f"t-{design.template}",
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
function api(method,path,body){var headers={'X-Invite-Token':TY.token};if(body)headers['Content-Type']='application/json';
  return fetch(TY.api+'/'+path,{method:method,headers:headers,cache:'no-store',credentials:'omit',body:body?JSON.stringify(body):undefined})
    .then(function(r){return r.text().then(function(t){var j={};try{j=t?JSON.parse(t):{};}catch(e){}return{status:r.status,body:j};});});}
function msg(r,fallback){return(r.body&&r.body.error&&r.body.error.message)||fallback;}
function time(t){if(!t)return'';var p=t.split(':'),n=+p[0];return((n%12)||12)+':'+p[1]+(n<12?' AM':' PM');}
function date(d){return new Date(d+'T00:00:00').toLocaleDateString(undefined,{weekday:'short',day:'numeric',month:'long',year:'numeric'});}
function when(o){var s=date(o.function_date||o.celebration_date),a=time(o.start_time),b=time(o.end_time);
  return s+(a?' · '+a+(b?' – '+b:''):'');}
function card(kids,cls){return h('div',{cls:'card '+(cls||'')},kids);}
function section(title,kids){return h('section',{cls:'sec'},[title?h('h2',{text:title}):null].concat(kids));}
function notice(title,text,retry){root.textContent='';root.appendChild(h('div',{cls:'sec'},[card([h('h2',{text:title}),h('p',{cls:'muted',text:text}),
  retry?h('button',{cls:'primary',text:'Try again',on:{click:load}}):null])]));}

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

function renderDetails(){var out=[],e=page.event;
  if(e.message)out.push(h('p',{cls:'message',text:e.message}));
  var fns=page.functions;
  if(fns.length){out.push(section(fns.length>1?'The celebrations':'The celebration',fns.map(function(f){
    var venue=[f.venue_name||e.venue_name,f.venue_address||e.venue_address].filter(Boolean).join(', ');
    var map=f.map_url||e.map_url;
    return card([h('div',{cls:'row'},[h('h3',{text:f.name}),f.is_cancelled?h('span',{cls:'tag bad',text:'Cancelled'}):null]),
      h('div',{cls:'when',text:when(f)}),venue?h('div',{cls:'muted',text:venue}):null,
      f.description?h('p',{cls:'small',text:f.description}):null,
      f.dress_code?h('p',{cls:'small',text:'Dress code: '+f.dress_code}):null,
      map&&!f.is_cancelled?h('a',{cls:'linkbtn',href:map,target:'_blank',rel:'noopener noreferrer',text:'Get directions'}):null],'fn');})));}
  else{var v=[e.venue_name,e.venue_address].filter(Boolean).join(', ');
    out.push(section('When & where',[card([h('div',{cls:'when',style:'color:var(--primary);font-weight:600',text:when(e)}),
      v?h('div',{cls:'muted',text:v}):null,
      e.map_url?h('a',{cls:'linkbtn',href:e.map_url,target:'_blank',rel:'noopener noreferrer',text:'Get directions'}):null])]));}
  return out;}

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

function renderForm(){var all=slots(),multi=all.length>1,formBits=[];
  function redraw(){renderAll();}
  // Attendance is one question when there's only one function; food only once it's a yes/maybe.
  all.forEach(function(s){var k=key(s.m.id,s.f&&s.f.id),cur=state[k]=state[k]||{};
    var title=[page.response_mode==='individual'?s.m.name:null,s.f&&multi?s.f.name:null].filter(Boolean).join(' — ');
    var kids=[title?h('h3',{text:title,style:'margin-bottom:10px'}):null,choiceRow(s,cur,redraw)];
    if(cur.status==='attending'&&page.rsvp.ask_attendee_count&&limit(s.m)>1)kids.push(stepper('How many people, including you?',cur,limit(s.m),redraw));
    if(cur.status==='attending'||cur.status==='maybe')foodFields(cur,redraw).forEach(function(x){kids.push(x);});
    formBits.push(card(kids));});
  var err=h('div',{cls:'err hidden',role:'alert'});
  var answered=all.every(function(s){return state[key(s.m.id,s.f&&s.f.id)].status;});
  var btn=h('button',{cls:'primary',type:'button',disabled:!answered||sending||TY.preview,text:TY.preview?'Responses are off in preview':(sending?'Sending…':(page.has_responded?'Update my response':'Send my response')),
    on:{click:function(){submit(all,err);}}});
  var tail=[field('textarea','A note for the host (optional)',note,function(v){note=v;},{maxlength:1000}),btn,err];
  var heading=page.response_mode==='group'?('Your response for '+page.members.map(function(m){return m.name;}).join(', ')):'Will you join us?';
  return section(heading,formBits.concat([card(tail)]));}
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
  h('p',{cls:'muted',text:'We look forward to celebrating with you.'})];
  var lines=[];page.members.forEach(function(m){(m.responses||[]).forEach(function(r){if(r.status==='pending'||r.status==='no_response')return;
    var f=null;page.functions.forEach(function(x){if(x.id===r.function_id)f=x;});
    var who=page.response_mode==='individual'?m.name+' · ':'';if(page.response_mode==='group'&&!m.is_self)return;
    lines.push(who+(f?f.name+': ':'')+({attending:'Attending'+(r.attendee_count>1?' ('+r.attendee_count+')':''),maybe:'Maybe',declined:'Not attending'}[r.status]));});});
  lines.forEach(function(l){kids.push(h('div',{cls:'small',text:l}));});
  if(page.can_respond&&page.rsvp.allow_edit)kids.push(h('button',{cls:'primary',type:'button',text:'Change my response',style:'background:transparent;color:var(--primary);border:1.5px solid var(--line)',on:{click:function(){editing=true;renderAll();}}}));
  return h('section',{cls:'sec'},[card(kids,'thanks')]);}

function renderClaim(){var d={name:'',phone:'',email:'',website:''},err=h('div',{cls:'err hidden',role:'alert'}),send;
  send=h('button',{cls:'primary',type:'button',text:'Continue',on:{click:function(){send.disabled=true;send.textContent='One moment…';err.classList.add('hidden');
    api('POST','claim',d).then(function(r){if(r.status===200){location.replace(r.body.data.url);return;}
      send.disabled=false;send.textContent='Continue';err.textContent=msg(r,'Please check your details and try again.');err.classList.remove('hidden');
    }).catch(function(){send.disabled=false;send.textContent='Continue';err.textContent='No connection. Please try again.';err.classList.remove('hidden');});}}});
  var trap=field('input','Leave this empty',d.website,function(v){d.website=v;},{tabindex:'-1',autocomplete:'off'});trap.className='hidden';
  return section('Will you join us?',[card([h('p',{cls:'muted',text:'Tell us who you are so the host knows to expect you.'}),
    field('input','Your name',d.name,function(v){d.name=v;},{autocomplete:'name',maxlength:200}),
    field('input','Mobile number',d.phone,function(v){d.phone=v;},{type:'tel',autocomplete:'tel',maxlength:20,inputmode:'tel'}),
    trap,send,err])]);}

function renderPasses(){if(!page.passes.length)return null;
  return section(page.passes.length>1?'Your entry passes':'Your entry pass',page.passes.map(function(p){
    var qr=h('div',{role:'img','aria-label':'Entry QR code for '+p.name});qr.innerHTML=p.qr_svg;
    return card([page.passes.length>1?h('h3',{text:p.name}):null,qr,h('div',{cls:'code',text:p.entry_code}),
      h('p',{cls:'small',text:'Show this at the entrance. It is personal to you.'})],'pass');}));}
function renderExtras(){var e=page.event,kids=[];
  var dress=[];page.functions.forEach(function(f){if(f.dress_code)dress.push(1);});
  if(e.instructions)kids.push(card([h('h3',{text:'Good to know',style:'margin-bottom:6px'}),h('p',{cls:'muted',style:'white-space:pre-line;margin:0',text:e.instructions})]));
  if(e.contact_phone||e.contact_name){var p=e.contact_phone;kids.push(card([h('h3',{text:'Questions?',style:'margin-bottom:6px'}),
    h('div',{cls:'muted',text:'Contact '+(e.contact_name||'the host')}),p?h('a',{cls:'linkbtn',href:'tel:'+p.replace(/[^+0-9]/g,''),text:'Call '+p}):null]));}
  if(TY.calendar)kids.push(card([h('a',{cls:'linkbtn',style:'margin-top:0',href:TY.calendar,text:'Add to calendar'})]));
  return kids.length?h('section',{cls:'sec'},kids):null;}

function renderAll(justSent){root.textContent='';
  renderDetails().forEach(function(n){root.appendChild(n);});
  if(page.kind==='general'){if(page.can_respond)root.appendChild(renderClaim());else if(page.closed_reason)root.appendChild(section('',[card([h('p',{cls:'muted',style:'margin:0',text:page.closed_reason})])]));}
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
