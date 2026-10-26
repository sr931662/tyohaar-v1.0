"""
Self-contained mobile web pages for people without the app.

* Guest invitation page — opened from the personal invite link. Shows the
  event, lets the guest RSVP and displays their pass QR + code.
* Gate console — opened from a host-issued gate access link. Verifies passes
  by camera scan (where the browser supports BarcodeDetector), typed code or
  name search, and records check-in / check-out.

No build step, no third-party scripts: the gate console handles a credential,
so nothing is loaded from anywhere but this origin. Every server string is
written with textContent; the only HTML injected is the server-generated QR
SVG. The token lives in the URL fragment and is sent as a header, so it never
appears in access logs. A per-response CSP nonce pins the inline script.
"""

from __future__ import annotations

import secrets

from fastapi.responses import HTMLResponse

_BASE_CSS = """
:root{--paper:#F6F1E8;--surface:#fff;--ink:#2A2018;--ink2:#6B5D50;--ink3:#A99C8C;--line:rgba(42,32,24,.1);
--accent:#C96E1A;--accent-soft:#FBE7CC;--ok:#2F7A4B;--ok-soft:#E3F2E8;--warn:#9A6A00;--warn-soft:#FBF0D6;
--bad:#B3354F;--bad-soft:#F8E1E6;color-scheme:light dark}
@media (prefers-color-scheme:dark){:root{--paper:#2B0A14;--surface:#3D1420;--ink:#F4EBDC;--ink2:#C6B2C0;
--ink3:#8A7588;--line:rgba(244,235,220,.12);--accent:#F0A93C;--accent-soft:rgba(240,169,60,.16);--ok:#7FC9A7;
--ok-soft:rgba(127,201,167,.14);--warn:#E8C46A;--warn-soft:rgba(232,196,106,.14);--bad:#EC6E92;--bad-soft:rgba(236,110,146,.14)}}
*{box-sizing:border-box}html,body{margin:0}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:var(--paper);color:var(--ink);
padding:20px 16px 40px;line-height:1.45;-webkit-text-size-adjust:100%}
.wrap{max-width:440px;margin:0 auto}
.card{background:var(--surface);border:1px solid var(--line);border-radius:22px;padding:22px 20px;margin-bottom:14px}
.eyebrow{font-size:11px;letter-spacing:1.6px;text-transform:uppercase;font-weight:700;color:var(--accent)}
h1{font-size:23px;margin:6px 0 4px;line-height:1.2}h2{font-size:16px;margin:0 0 12px}
.muted{color:var(--ink2);font-size:14px}.small{font-size:12.5px;color:var(--ink3)}
.row{display:flex;gap:10px;align-items:flex-start;margin-top:12px}.row .k{width:22px;flex:none;text-align:center}
.pill{display:inline-block;padding:5px 12px;border-radius:999px;font-size:12px;font-weight:700}
.ok{background:var(--ok-soft);color:var(--ok)}.warn{background:var(--warn-soft);color:var(--warn)}
.bad{background:var(--bad-soft);color:var(--bad)}.info{background:var(--accent-soft);color:var(--accent)}
button,.btn{font:inherit;font-weight:700;font-size:15px;border-radius:14px;padding:13px 16px;border:1.5px solid var(--line);
background:var(--surface);color:var(--ink);cursor:pointer;min-height:48px;width:100%}
button.primary{background:var(--accent);border-color:var(--accent);color:#fff}
button:disabled{opacity:.55;cursor:default}button.sel{border-color:var(--accent);background:var(--accent-soft);color:var(--accent)}
.stack{display:grid;gap:10px}.grid3{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}
input,textarea{font:inherit;width:100%;padding:12px 14px;border-radius:12px;border:1.5px solid var(--line);
background:var(--paper);color:var(--ink)}textarea{min-height:72px;resize:vertical}
label{font-size:13px;font-weight:600;color:var(--ink2);display:block;margin:12px 0 6px}
.center{text-align:center}.hidden{display:none!important}
.err{color:var(--bad);font-size:13.5px;margin-top:10px}
"""


def _page(title: str, body: str, script: str) -> HTMLResponse:
    nonce = secrets.token_urlsafe(16)
    html = (
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1, viewport-fit=cover\">"
        "<meta name=\"robots\" content=\"noindex, nofollow\">"
        "<meta name=\"referrer\" content=\"no-referrer\">"
        f"<title>{title}</title><style>{_BASE_CSS}</style></head><body>"
        f"{body}<script nonce=\"{nonce}\">{script}</script></body></html>"
    )
    return HTMLResponse(
        html,
        headers={
            "Content-Security-Policy": (
                "default-src 'none'; "
                f"script-src 'nonce-{nonce}'; "
                "style-src 'unsafe-inline'; img-src 'self' data:; "
                "connect-src 'self'; media-src 'self' blob:; "
                "base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
            ),
            "Cache-Control": "no-store",
        },
    )


# ── Guest invitation ──────────────────────────────────────────────────────────

_INVITE_BODY = """
<div class="wrap" id="app">
  <div class="card center" id="loading"><p class="muted">Opening your invitation…</p></div>

  <div class="card hidden" id="problem"><div class="eyebrow">Tyohaar</div>
    <h1 id="problem-title">Invitation unavailable</h1><p class="muted" id="problem-text"></p>
    <button id="retry" class="hidden">Try again</button></div>

  <div id="content" class="hidden">
    <div class="card" id="event-card">
      <div class="eyebrow">You're invited</div>
      <h1 id="title"></h1>
      <p class="muted" id="host"></p>
      <div class="row"><span class="k">📅</span><div id="when"></div></div>
      <div class="row hidden" id="venue-row"><span class="k">📍</span><div><div id="venue"></div>
        <a id="map" class="small hidden" target="_blank" rel="noopener noreferrer">Open in Maps</a></div></div>
      <div class="row"><span class="k">🎟</span><div id="allowance"></div></div>
      <div class="row hidden" id="arrival-row"><span class="k">⏰</span><div id="arrival"></div></div>
    </div>

    <div class="card center" id="state-card"><span class="pill" id="state-pill"></span>
      <p class="muted" id="state-text" style="margin:10px 0 0"></p></div>

    <div class="card hidden" id="pass-card">
      <h2>Your entry pass</h2>
      <div class="center" id="qr" aria-label="Entry QR code" role="img"></div>
      <p class="center" style="font:700 24px ui-monospace,Menlo,monospace;letter-spacing:3px;margin:12px 0 4px" id="code"></p>
      <p class="small center">Show this at the entrance. It's personal to you — please don't share it.</p>
    </div>

    <div class="card hidden" id="rsvp-card">
      <h2>Will you be there?</h2>
      <div class="grid3">
        <button data-s="attending">Yes</button><button data-s="maybe">Maybe</button><button data-s="declined">Can't come</button>
      </div>
      <div id="party-wrap" class="hidden"><label for="party">How many people, including you?</label>
        <input id="party" type="number" inputmode="numeric" min="1"></div>
      <label for="note">Note for the host (optional)</label>
      <textarea id="note" maxlength="1000" placeholder="Dietary needs, arrival time…"></textarea>
      <button class="primary" id="send" style="margin-top:12px" disabled>Send response</button>
      <div class="err hidden" id="rsvp-err" role="alert"></div>
      <p class="small" id="rsvp-saved" style="margin-top:10px"></p>
    </div>
  </div>
</div>
"""

_INVITE_SCRIPT = r"""
(function(){
  var token = decodeURIComponent((location.hash || '').slice(1));
  var $ = function(id){ return document.getElementById(id); };
  var data = null, choice = null;
  var STATES = {
    valid: ['ok', 'Pass active', 'Your pass is ready for the event.'],
    not_yet_valid: ['info', 'Pass ready', 'Your pass will work at the entrance on the day of the event.'],
    checked_in: ['ok', 'Checked in', 'You have been checked in. Enjoy the celebration!'],
    checked_out: ['info', 'Checked out', 'You checked out earlier. Re-entry is allowed with the same pass.'],
    used: ['warn', 'Pass used', 'This pass has already been used.'],
    expired: ['warn', 'Pass expired', 'This event has ended, so the pass is no longer valid.'],
    revoked: ['bad', 'Invitation cancelled', 'The host has cancelled this invitation.'],
    event_cancelled: ['bad', 'Event cancelled', 'The host has cancelled this event.'],
    postponed: ['warn', 'Event postponed', 'The event has been postponed. Check back for the new date.']
  };
  function show(id, on){ $(id).classList.toggle('hidden', !on); }
  function problem(title, text, retry){
    show('loading', false); show('content', false); show('problem', true);
    $('problem-title').textContent = title; $('problem-text').textContent = text; show('retry', !!retry);
  }
  function fmtTime(t){ if(!t) return null; var p = t.split(':'); var h = +p[0], m = p[1];
    return ((h % 12) || 12) + ':' + m + (h < 12 ? ' AM' : ' PM'); }
  function fmtDate(d){ var x = new Date(d + 'T00:00:00');
    return x.toLocaleDateString(undefined, {weekday:'long', day:'numeric', month:'long', year:'numeric'}); }
  function api(method, path, body){
    return fetch(path, {method: method, headers: Object.assign({'X-Invite-Token': token},
      body ? {'Content-Type':'application/json'} : {}), body: body ? JSON.stringify(body) : undefined,
      cache: 'no-store', credentials: 'omit'})
      .then(function(r){ return r.json().catch(function(){ return {}; }).then(function(j){ return {status:r.status, body:j}; }); });
  }
  function applyTheme(c){ if(!c) return; var p = c.primary || c.accent;
    if(typeof p === 'string' && /^#[0-9a-f]{6}$/i.test(p)) document.documentElement.style.setProperty('--accent', p); }
  function render(d){
    data = d; applyTheme(d.theme_colors);
    show('loading', false); show('problem', false); show('content', true);
    $('title').textContent = d.celebration_title;
    $('host').textContent = d.host_first_name ? ('Hosted by ' + d.host_first_name) : '';
    $('host').classList.toggle('hidden', !d.host_first_name);
    var when = fmtDate(d.celebration_date), s = fmtTime(d.start_time), e = fmtTime(d.end_time);
    if(s) when += ' · ' + s + (e ? ' – ' + e : '');
    $('when').textContent = when;
    var venue = [d.venue_name, d.venue_address].filter(Boolean).join(', ');
    show('venue-row', !!venue); $('venue').textContent = venue;
    if(d.map_url){ $('map').href = d.map_url; show('map', true); }
    $('allowance').textContent = 'For ' + d.guest_name + (d.plus_ones_allowed > 0 ?
      ' + ' + d.plus_ones_allowed + (d.plus_ones_allowed === 1 ? ' guest' : ' guests') : '');
    var a = fmtTime(d.arrival_window_start), b = fmtTime(d.arrival_window_end);
    show('arrival-row', !!a); if(a) $('arrival').textContent = 'Please arrive between ' + a + ' and ' + b;
    var st = STATES[d.pass_state] || ['info', d.pass_state, ''];
    $('state-pill').className = 'pill ' + st[0]; $('state-pill').textContent = st[1]; $('state-text').textContent = st[2];
    show('pass-card', !!d.entry_code);
    if(d.entry_code){ $('qr').innerHTML = d.qr_svg || ''; $('code').textContent = d.entry_code; }
    show('rsvp-card', d.can_respond);
    if(d.can_respond){
      choice = d.rsvp_status === 'pending' || d.rsvp_status === 'no_response' ? null : d.rsvp_status;
      $('party').max = 1 + d.plus_ones_allowed; $('party').value = d.rsvp_party_size || 1;
      paint();
      $('rsvp-saved').textContent = choice ? 'Your current response: ' + label(choice) + '. You can change it until the day before.' : '';
    }
  }
  function label(s){ return {attending:'Coming', maybe:'Maybe', declined:"Can't come"}[s] || s; }
  function paint(){
    Array.prototype.forEach.call(document.querySelectorAll('[data-s]'), function(b){ b.classList.toggle('sel', b.dataset.s === choice); });
    show('party-wrap', choice === 'attending' && data.plus_ones_allowed > 0);
    $('send').disabled = !choice;
  }
  Array.prototype.forEach.call(document.querySelectorAll('[data-s]'), function(b){
    b.addEventListener('click', function(){ choice = b.dataset.s; paint(); });
  });
  $('send').addEventListener('click', function(){
    var btn = $('send'); btn.disabled = true; btn.textContent = 'Sending…'; show('rsvp-err', false);
    var party = parseInt($('party').value, 10);
    api('POST', 'rsvp', {rsvp_status: choice, party_size: choice === 'attending' ? (party || 1) : null,
      note: $('note').value.trim() || null})
      .then(function(r){
        if(r.status === 200){ render(r.body.data); $('rsvp-saved').textContent = 'Thanks! Your response was sent to the host.'; }
        else { $('rsvp-err').textContent = (r.body.error && r.body.error.message) || 'Could not send your response.'; show('rsvp-err', true); }
      })
      .catch(function(){ $('rsvp-err').textContent = 'No connection. Your response was not sent — please try again.'; show('rsvp-err', true); })
      .then(function(){ btn.textContent = 'Send response'; btn.disabled = !choice; });
  });
  function load(){
    if(!token){ problem('Invitation link incomplete', 'Open the full link exactly as you received it.'); return; }
    show('problem', false); show('loading', true);
    api('GET', 'view').then(function(r){
      if(r.status === 200) render(r.body.data);
      else if(r.status === 404) problem('Invitation not found', 'This link is not valid. It may have been replaced by a newer one — ask your host to share it again.');
      else if(r.status === 429) problem('Please wait a moment', 'Too many attempts. Try again in a minute.', true);
      else problem('Something went wrong', 'We could not load this invitation.', true);
    }).catch(function(){ problem('No connection', 'Check your internet connection and try again.', true); });
  }
  $('retry').addEventListener('click', load);
  load();
})();
"""


def invite_page() -> HTMLResponse:
    return _page("Your invitation — Tyohaar", _INVITE_BODY, _INVITE_SCRIPT)


# ── Gate console ──────────────────────────────────────────────────────────────

_GATE_BODY = """
<div class="wrap">
  <div class="card" id="head"><div class="eyebrow">Tyohaar · Gate</div>
    <h1 id="ev">Loading…</h1><p class="muted" id="op"></p>
    <div class="grid3 center" style="margin-top:12px">
      <div><b id="c-in">–</b><div class="small">Arrived</div></div>
      <div><b id="c-people">–</b><div class="small">People in</div></div>
      <div><b id="c-exp">–</b><div class="small">Expected</div></div>
    </div></div>

  <div class="card hidden" id="denied"><h1>Gate link unavailable</h1>
    <p class="muted">This gate link is invalid, has expired or was revoked by the host. Ask the host for a new one.</p></div>

  <div id="console" class="hidden">
    <div class="card">
      <button class="primary" id="scan">Scan QR code</button>
      <video id="video" class="hidden" playsinline muted style="width:100%;border-radius:14px;margin-top:10px;background:#000"></video>
      <p class="small hidden" id="scan-note" style="margin-top:8px"></p>
      <label for="code">Or enter the pass code</label>
      <div style="display:flex;gap:8px"><input id="code" autocomplete="off" autocapitalize="characters" spellcheck="false"
        placeholder="K7QM-3XPD" style="font-family:ui-monospace,Menlo,monospace;letter-spacing:2px;text-transform:uppercase">
        <button id="verify" style="width:auto;padding:0 18px">Check</button></div>
      <label for="q">Or find a guest by name / last 4 phone digits</label>
      <input id="q" autocomplete="off" placeholder="Type at least 2 letters">
      <div class="stack" id="results" style="margin-top:8px"></div>
    </div>

    <div class="card hidden" id="result" aria-live="assertive">
      <span class="pill" id="r-pill"></span>
      <h1 id="r-name" style="margin-top:10px"></h1>
      <p class="muted" id="r-msg"></p>
      <div id="r-details" class="small"></div>
      <div id="r-warn" class="warn pill hidden" style="margin-top:10px"></div>
      <div id="party-box" class="hidden"><label for="party">People entering (incl. guest)</label>
        <input id="party" type="number" inputmode="numeric" min="1" value="1"></div>
      <div class="stack" style="margin-top:12px">
        <button class="primary hidden" id="checkin">Check in</button>
        <button class="hidden" id="checkout">Check out</button>
        <button id="next">Next guest</button>
      </div>
      <div class="err hidden" id="r-err" role="alert"></div>
    </div>
  </div>
</div>
"""

_GATE_SCRIPT = r"""
(function(){
  var token = decodeURIComponent((location.hash || '').slice(1));
  var $ = function(id){ return document.getElementById(id); };
  var current = null, pending = null, stream = null, scanTimer = null, busy = false;
  function show(id, on){ $(id).classList.toggle('hidden', !on); }
  function uuid(){ return (crypto.randomUUID ? crypto.randomUUID() :
    'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c){ var r = crypto.getRandomValues(new Uint8Array(1))[0] % 16;
      return (c === 'x' ? r : (r & 3 | 8)).toString(16); })); }
  function api(method, path, body){
    return fetch(path, {method: method, cache: 'no-store', credentials: 'omit',
      headers: Object.assign({'X-Gate-Token': token}, body ? {'Content-Type': 'application/json'} : {}),
      body: body ? JSON.stringify(body) : undefined})
      .then(function(r){ return r.json().catch(function(){ return {}; }).then(function(j){
        if(r.status === 401){ deny(); throw new Error('denied'); } return {status: r.status, body: j}; }); });
  }
  function deny(){ show('console', false); show('denied', true); stopScan(); }
  function fmtTime(t){ if(!t) return ''; var p = t.split(':'), h = +p[0]; return ((h % 12) || 12) + ':' + p[1] + (h < 12 ? ' AM' : ' PM'); }
  var TONE = {valid:'ok', checked_in:'ok', checked_out:'ok', already_checked_in:'warn', already_used:'warn',
    not_checked_in:'warn', not_yet_valid:'warn', party_size_exceeded:'warn', invalid:'bad', expired:'bad',
    revoked:'bad', event_cancelled:'bad', denied:'bad'};
  var TITLE = {valid:'Valid pass', checked_in:'Checked in', checked_out:'Checked out', already_checked_in:'Already checked in',
    already_used:'Pass already used', not_checked_in:'Not checked in', not_yet_valid:'Not valid yet',
    party_size_exceeded:'Too many people', invalid:'Invalid pass', expired:'Expired', revoked:'Revoked',
    event_cancelled:'Event cancelled', denied:'Entry denied'};
  function session(){
    api('GET', 'session').then(function(r){
      if(r.status !== 200) return;
      var s = r.body.data; $('ev').textContent = s.celebration_title;
      $('op').textContent = s.operator_label + (s.expires_at ? ' · access until ' + new Date(s.expires_at).toLocaleString() : '');
      $('c-in').textContent = s.arrived_guests; $('c-people').textContent = s.arrived_people; $('c-exp').textContent = s.still_expected;
      show('console', true);
    }).catch(function(e){ if(e.message !== 'denied'){ $('ev').textContent = 'No connection'; $('op').textContent = 'Retrying…'; setTimeout(session, 4000); } });
  }
  function renderResult(res){
    current = res; show('result', true); show('r-err', false);
    $('r-pill').className = 'pill ' + (TONE[res.result] || 'info');
    $('r-pill').textContent = (TITLE[res.result] || res.result) + (res.replayed ? ' (already recorded)' : '');
    $('r-name').textContent = res.guest ? res.guest.name : '—';
    $('r-msg').textContent = res.message;
    var g = res.guest, lines = [];
    if(g){
      lines.push('Admits ' + (1 + g.plus_ones_allowed) + (g.plus_ones_allowed ? ' (guest + ' + g.plus_ones_allowed + ')' : ' (guest only)'));
      if(g.rsvp_party_size) lines.push('RSVP: ' + g.rsvp_party_size + ' coming');
      if(g.arrival_window_start) lines.push('Expected ' + fmtTime(g.arrival_window_start) + ' – ' + fmtTime(g.arrival_window_end));
      if(g.vehicle_number) lines.push('Vehicle ' + g.vehicle_number);
      if(g.phone_masked) lines.push('Phone ' + g.phone_masked);
      if(g.checked_in_at) lines.push('Checked in ' + new Date(g.checked_in_at).toLocaleTimeString() + (g.checked_in_party_size ? ' · ' + g.checked_in_party_size + ' people' : ''));
    }
    $('r-details').textContent = ''; lines.forEach(function(l){ var d = document.createElement('div'); d.textContent = l; $('r-details').appendChild(d); });
    var warn = (res.warnings || []).map(function(w){ return {rsvp_declined:'Guest had declined the RSVP', reentry:'Re-entry'}[w] || w; }).join(' · ');
    $('r-warn').textContent = warn; show('r-warn', !!warn);
    var canIn = res.result === 'valid', canOut = g && g.entry_status === 'checked_in';
    show('checkin', canIn); show('party-box', canIn && g.plus_ones_allowed > 0);
    if(canIn){ $('party').max = 1 + g.plus_ones_allowed; $('party').value = Math.min(g.rsvp_party_size || 1, 1 + g.plus_ones_allowed); }
    show('checkout', !!canOut && res.result !== 'checked_in');
    if(navigator.vibrate) navigator.vibrate(TONE[res.result] === 'ok' ? 60 : [80, 60, 80]);
    $('result').scrollIntoView({behavior: 'smooth', block: 'start'});
  }
  function lookup(body){
    if(busy) return; busy = true; show('r-err', false);
    pending = Object.assign({client_scan_id: uuid()}, body);
    api('POST', 'verify', pending).then(function(r){
      if(r.status === 200) renderResult(r.body.data);
      else showErr((r.body.error && r.body.error.message) || 'Could not check this pass.');
    }).catch(function(e){ if(e.message !== 'denied') showErr('No connection — nothing was checked. Try again.'); })
      .then(function(){ busy = false; });
  }
  function act(path, extra){
    if(busy || !pending) return; busy = true; show('r-err', false);
    var btn = path === 'check-in' ? $('checkin') : $('checkout'); var label = btn.textContent; btn.disabled = true; btn.textContent = 'Saving…';
    // Same client_scan_id on every retry: the server records it once.
    api('POST', path, Object.assign({}, pending, extra || {})).then(function(r){
      if(r.status === 200){ renderResult(r.body.data); if(r.body.data.recorded) session(); }
      else showErr((r.body.error && r.body.error.message) || 'Not recorded.');
    }).catch(function(e){ if(e.message !== 'denied') showErr('No connection — entry NOT recorded. Tap again to retry.'); })
      .then(function(){ busy = false; btn.disabled = false; btn.textContent = label; });
  }
  function showErr(m){ $('r-err').textContent = m; show('r-err', true); show('result', true); }
  $('verify').addEventListener('click', function(){ var v = $('code').value.trim(); if(v) lookup({code: v, method: 'manual'}); });
  $('code').addEventListener('keydown', function(e){ if(e.key === 'Enter') $('verify').click(); });
  $('checkin').addEventListener('click', function(){ act('check-in', {party_size: parseInt($('party').value, 10) || 1}); });
  $('checkout').addEventListener('click', function(){ pending.client_scan_id = uuid(); act('check-out'); });
  $('next').addEventListener('click', function(){ current = pending = null; show('result', false); $('code').value = ''; $('q').value = '';
    $('results').textContent = ''; window.scrollTo({top: 0, behavior: 'smooth'}); });
  var qTimer = null;
  $('q').addEventListener('input', function(){ clearTimeout(qTimer); var q = $('q').value.trim();
    if(q.length < 2){ $('results').textContent = ''; return; }
    qTimer = setTimeout(function(){ api('GET', 'search?q=' + encodeURIComponent(q)).then(function(r){
      $('results').textContent = '';
      ((r.body && r.body.data) || []).forEach(function(g){ var b = document.createElement('button');
        b.textContent = g.name + (g.phone_masked ? '  ' + g.phone_masked : '') + (g.entry_status === 'checked_in' ? '  · inside' : '');
        b.addEventListener('click', function(){ lookup({guest_id: g.id, method: 'search'}); }); $('results').appendChild(b); });
      if(!r.body.data || !r.body.data.length){ var p = document.createElement('p'); p.className = 'small'; p.textContent = 'No matching guests.'; $('results').appendChild(p); }
    }).catch(function(){}); }, 300); });
  function stopScan(){ clearInterval(scanTimer); scanTimer = null; if(stream){ stream.getTracks().forEach(function(t){ t.stop(); }); stream = null; }
    show('video', false); $('scan').textContent = 'Scan QR code'; }
  $('scan').addEventListener('click', function(){
    if(stream){ stopScan(); return; }
    if(!('BarcodeDetector' in window) || !navigator.mediaDevices){
      $('scan-note').textContent = 'Camera scanning is not supported in this browser. Type the code shown under the QR instead.';
      show('scan-note', true); return; }
    var detector = new BarcodeDetector({formats: ['qr_code']});
    navigator.mediaDevices.getUserMedia({video: {facingMode: 'environment'}}).then(function(s){
      stream = s; var v = $('video'); v.srcObject = s; show('video', true); v.play(); $('scan').textContent = 'Stop camera'; show('scan-note', false);
      scanTimer = setInterval(function(){ if(busy || v.readyState < 2) return;
        detector.detect(v).then(function(codes){ if(codes && codes.length){ stopScan(); lookup({code: codes[0].rawValue, method: 'qr'}); } }).catch(function(){}); }, 250);
    }).catch(function(){ $('scan-note').textContent = 'Camera permission was denied. Type the code instead.'; show('scan-note', true); });
  });
  if(!token){ deny(); return; }
  session();
})();
"""


def gate_page() -> HTMLResponse:
    return _page("Gate console — Tyohaar", _GATE_BODY, _GATE_SCRIPT)
