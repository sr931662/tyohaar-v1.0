// Screens.jsx — TyohaarApp interactive demo. ES module conversion of screens.jsx.
import React, { useState, useEffect, useRef } from 'react';
import {
  OCCASIONS, VIBES, VENDORS, PLAN_TEMPLATE, SEED_GUESTS,
  Icon, Photo, Emblem, Ring, Avatar, Btn, Chip, TINTS, priceStr, stars,
} from './TY.jsx';
import { IOSDevice } from './IOSFrame.jsx';

const WIZARD = ['occasion','details','guests','vendors','plan'];

/* ───────── shared chrome ───────── */
function ScreenRoot({ children }) {
  return <div style={{height:'100%', display:'flex', flexDirection:'column',
    background:'var(--paper)', color:'var(--ink)', fontFamily:'var(--font-sans)'}}>{children}</div>;
}
function Scroll({ children, pad=true }) {
  return <div className="ty-scroll" style={{flex:1, overflowY:'auto', overflowX:'hidden',
    padding: pad ? '0 18px 28px' : 0}}>{children}</div>;
}
function TopBar({ children, blur=true }) {
  return <div style={{paddingTop:50, paddingLeft:18, paddingRight:18, paddingBottom:12,
    position:'relative', zIndex:6,
    background: blur ? 'color-mix(in srgb, var(--paper) 82%, transparent)' : 'transparent',
    backdropFilter: blur?'blur(12px)':'none', WebkitBackdropFilter:blur?'blur(12px)':'none'}}>{children}</div>;
}
function IconBtn({ name, onClick, size=22 }) {
  return <button onClick={onClick} style={{appearance:'none',
    border:'1px solid color-mix(in srgb, var(--ink) 22%, transparent)',
    background:'var(--surface)', width:42, height:42, borderRadius:14, cursor:'pointer',
    color:'var(--ink)', display:'flex', alignItems:'center', justifyContent:'center', boxShadow:'var(--shadow-sm)'}}>
    <Icon name={name} size={size}/></button>;
}

function TabBar({ view, go, onCreate }) {
  const tabs = [['home','Home'],['plan','Plan'],['__','' ],['vendors','Vendors'],['memories','Memories']];
  return (
    <div style={{flexShrink:0, position:'relative', paddingBottom:30, paddingTop:8,
      background:'color-mix(in srgb, var(--paper) 88%, transparent)', backdropFilter:'blur(14px)',
      WebkitBackdropFilter:'blur(14px)', borderTop:'1px solid var(--line-2)'}}>
      <div style={{display:'flex', alignItems:'flex-end', justifyContent:'space-around', padding:'0 8px'}}>
        {tabs.map(([k,label]) => k==='__' ? (
          <button key="c" onClick={onCreate} aria-label="Start a celebration" style={{appearance:'none', border:'none', cursor:'pointer',
            transform:'translateY(-14px)', background:'transparent'}}>
            <div style={{width:56, height:56, borderRadius:20, background:'var(--saffron)', color:'var(--on-primary)',
              display:'flex', alignItems:'center', justifyContent:'center',
              boxShadow:'0 8px 22px color-mix(in srgb, var(--saffron) 55%, transparent)'}}>
              <Icon name="plus" size={28} sw={2.2}/></div>
          </button>
        ) : (
          <button key={k} onClick={()=>go(k)} style={{appearance:'none', border:'none', background:'transparent',
            cursor:'pointer', display:'flex', flexDirection:'column', alignItems:'center', gap:4, padding:'4px 6px',
            color: view===k ? 'var(--saffron)' : 'var(--ink-3)'}}>
            <Icon name={k==='home'?'home':k==='plan'?'plan':k==='vendors'?'vendors':'heart'} size={23}
              sw={view===k?2.1:1.7}/>
            <span style={{fontSize:10.5, fontWeight:view===k?700:600, letterSpacing:'0.01em'}}>{label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

function Celebrate({ run }) {
  if (!run) return null;
  const cols = ['var(--saffron)','var(--rose)','var(--gold)','var(--leaf)'];
  return (
    <div style={{position:'absolute', inset:0, pointerEvents:'none', overflow:'hidden', zIndex:40}}>
      {Array.from({length:26}).map((_,i)=>{
        const left = Math.random()*100, dur = 2.6+Math.random()*1.8, delay=Math.random()*0.8;
        const sz = 7+Math.random()*9;
        return <div key={i} style={{position:'absolute', top:-20, left:left+'%', width:sz, height:sz*1.4,
          borderRadius:'60% 60% 60% 0', background:cols[i%4], opacity:0.9,
          animation:`tyfall ${dur}s var(--ease) ${delay}s forwards`}}/>;
      })}
    </div>
  );
}

/* ═══════════════════════ MAIN APP ═══════════════════════ */
export default function TyohaarApp({ theme='light', initialView='home', initialStep=0, width=402, height=850 }) {
  const [view, setView] = useState(initialView);
  const [step, setStep] = useState(initialStep);
  const [occasion, setOccasion] = useState(OCCASIONS[0]);
  const [name, setName] = useState('Diya turns One');
  const [place, setPlace] = useState('The Courtyard, Jaipur');
  const [vibes, setVibes] = useState(['Intimate','Traditional']);
  const [guests, setGuests] = useState(SEED_GUESTS);
  const [chosen, setChosen] = useState(['v5','v2']);
  const [catFilter, setCatFilter] = useState('All');
  const [tasks, setTasks] = useState(() => PLAN_TEMPLATE.map(p=>({...p, items:p.items.map(it=>({...it}))})));
  const [celebrate, setCelebrate] = useState(false);
  const scrollKey = view + step;

  const totalGuests = guests.reduce((s,g)=>s+g.c,0);
  const totalTasks  = tasks.reduce((s,p)=>s+p.items.length,0);
  const doneTasks   = tasks.reduce((s,p)=>s+p.items.filter(i=>i.done).length,0);
  const planPct     = Math.round(doneTasks/totalTasks*100);
  const budget      = chosen.reduce((s,id)=>s+(VENDORS.find(v=>v.id===id)?.est||0),0);

  const dev = useRef(null);
  useEffect(()=>{
    const el = dev.current?.querySelector('.ty-scroll'); if(el) el.scrollTop=0;
  },[scrollKey]);

  const startCreate = () => { setStep(0); setView('create'); };
  const finishPlan  = () => { setView('event'); setCelebrate(true); setTimeout(()=>setCelebrate(false), 4200); };

  const toggleVendor  = id => setChosen(c => c.includes(id) ? c.filter(x=>x!==id) : [...c,id]);
  const toggleTask    = (pi,ii) => setTasks(ts => ts.map((p,a)=> a!==pi ? p : ({...p, items:p.items.map((it,b)=> b!==ii?it:({...it, done:!it.done}))})));
  const setGuestCount = (i,d) => setGuests(g => g.map((x,a)=> a!==i?x:({...x, c:Math.max(1,x.c+d)})));
  const cycleRsvp     = i => setGuests(g => g.map((x,a)=> a!==i?x:({...x, rsvp: x.rsvp==='yes'?'maybe':x.rsvp==='maybe'?'pending':'yes'})));
  const addGuest      = (n) => n.trim() && setGuests(g => [...g, {n:n.trim(), c:2, rsvp:'pending'}]);
  const toggleVibe    = v => setVibes(s => s.includes(v) ? s.filter(x=>x!==v) : [...s,v]);

  /* ───────── HOME ───────── */
  const Home = () => (
    <ScreenRoot>
      <TopBar>
        <div style={{display:'flex', alignItems:'center', justifyContent:'space-between'}}>
          <div>
            <div style={{fontSize:12, fontWeight:700, letterSpacing:'0.12em', textTransform:'uppercase', color:'var(--saffron)'}}>Tuesday · 3 June</div>
            <div style={{fontFamily:'var(--font-display)', fontSize:27, marginTop:3, color:'var(--ink)'}}>Namaste, Aarav</div>
          </div>
          <div style={{position:'relative'}}>
            <IconBtn name="bell"/>
            <div style={{position:'absolute', top:8, right:9, width:8, height:8, borderRadius:'50%', background:'var(--rose)', border:'2px solid var(--paper)'}}/>
          </div>
        </div>
      </TopBar>
      <Scroll>
        <div style={{position:'relative', borderRadius:'26px 26px 26px 26px', overflow:'hidden', boxShadow:'var(--shadow-md)', marginBottom:14}}>
          <Photo label="" tint={occasion.tint} h={300} arch={false}/>
          <div style={{position:'absolute', inset:0, background:'linear-gradient(to top, rgba(0,0,0,0.62) 0%, rgba(0,0,0,0.12) 48%, transparent 70%)'}}/>
          <div style={{position:'absolute', top:14, left:14, display:'flex', gap:8}}>
            <span style={pill}>{occasion.en}</span>
            <span style={{...pill, background:'var(--saffron)', color:'var(--on-primary)'}}>in 11 days</span>
          </div>
          <div style={{position:'absolute', left:16, right:16, bottom:16, color:'#fff'}}>
            <div style={{fontFamily:'var(--font-display)', fontSize:30, lineHeight:1.05}}>{name}</div>
            <div style={{fontSize:13.5, opacity:0.9, marginTop:6, display:'flex', alignItems:'center', gap:7}}>
              <Icon name="cal" size={15}/> Sat, 14 June · <Icon name="pin" size={15}/> Jaipur
            </div>
            <div style={{display:'flex', alignItems:'center', justifyContent:'space-between', marginTop:14}}>
              <div style={{display:'flex'}}>
                {guests.slice(0,4).map((g,i)=>(<div key={i} style={{marginLeft:i?-10:0}}><Avatar name={g.n} i={i} size={32}/></div>))}
                <div style={{marginLeft:-10, width:32, height:32, borderRadius:'50%', background:'rgba(255,255,255,0.22)', backdropFilter:'blur(6px)', border:'2px solid rgba(255,255,255,0.5)', display:'flex', alignItems:'center', justifyContent:'center', fontSize:11, fontWeight:700, color:'#fff'}}>+{totalGuests-8}</div>
              </div>
              <div style={{background:'rgba(255,255,255,0.16)', backdropFilter:'blur(8px)', borderRadius:14, padding:'8px 10px', display:'flex', alignItems:'center', gap:9}}>
                <Ring pct={planPct} size={40} sw={4}><span style={{fontSize:11, color:'#fff'}}>{planPct}%</span></Ring>
                <div style={{fontSize:11.5, color:'#fff', lineHeight:1.25}}>planned<br/><b style={{fontWeight:700}}>{totalTasks-doneTasks} to go</b></div>
              </div>
            </div>
          </div>
        </div>
        <Btn full onClick={()=>setView('event')} kind="soft" style={{marginBottom:26}}>Open this celebration <Icon name="chevR" size={18}/></Btn>

        <div style={{display:'flex', alignItems:'baseline', justifyContent:'space-between', marginBottom:12}}>
          <h3 style={hd}>Plan something new</h3>
        </div>
        <div onClick={startCreate} style={{cursor:'pointer', display:'flex', alignItems:'center', gap:14, padding:16,
          borderRadius:22, background:'var(--surface)', border:'1px solid var(--line)', boxShadow:'var(--shadow-sm)', marginBottom:26}}>
          <div style={{width:54, height:54, borderRadius:16, background:'var(--glow)', display:'flex', alignItems:'center', justifyContent:'center', color:'var(--saffron)'}}><Icon name="spark" size={26}/></div>
          <div style={{flex:1}}>
            <div style={{fontWeight:700, fontSize:16}}>Start a celebration</div>
            <div style={{fontSize:13, color:'var(--ink-2)', marginTop:2}}>Tyohaar builds the plan, you enjoy the moment</div>
          </div>
          <Icon name="chevR" size={20}/>
        </div>

        <h3 style={hd}>A year of moments</h3>
        <div style={{display:'flex', gap:12, marginTop:12}}>
          {[['Holi at home','rose'],['Dadi’s 70th','gold'],['Diwali','saffron']].map(([t,tn],i)=>(
            <div key={i} style={{flex:1}}>
              <Photo label="memory" tint={tn} h={92}/>
              <div style={{fontSize:12.5, fontWeight:600, marginTop:7, color:'var(--ink)'}}>{t}</div>
            </div>
          ))}
        </div>
      </Scroll>
      <TabBar view="home" go={setView} onCreate={startCreate}/>
    </ScreenRoot>
  );

  /* ───────── WIZARD shell ───────── */
  const Wizard = ({ title, sub, children, footer }) => (
    <ScreenRoot>
      <TopBar>
        <div style={{display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:16}}>
          <IconBtn name={step===0?'close':'chevL'} onClick={()=> step===0 ? setView('home') : setStep(step-1)}/>
          <div style={{fontSize:12.5, fontWeight:700, color:'var(--ink-2)', letterSpacing:'0.04em'}}>Step {step+1} of {WIZARD.length}</div>
          <div style={{width:42}}/>
        </div>
        <div style={{display:'flex', gap:6}}>
          {WIZARD.map((_,i)=>(<div key={i} style={{flex:1, height:5, borderRadius:3,
            background: i<=step ? 'var(--saffron)' : 'color-mix(in srgb, var(--ink) 28%, transparent)',
            transition:'background .3s var(--ease)'}}/>))}
        </div>
      </TopBar>
      <Scroll>
        <h2 style={{fontFamily:'var(--font-display)', fontSize:29, lineHeight:1.08, margin:'8px 0 6px', color:'var(--ink)'}}>{title}</h2>
        <p style={{fontSize:14.5, color:'var(--ink-2)', margin:'0 0 22px', lineHeight:1.5}}>{sub}</p>
        {children}
      </Scroll>
      <div style={{flexShrink:0, padding:'12px 18px 30px', borderTop:'1px solid var(--line-2)',
        background:'color-mix(in srgb, var(--paper) 88%, transparent)', backdropFilter:'blur(14px)'}}>
        {footer}
      </div>
    </ScreenRoot>
  );

  const OccasionStep = () => (
    <Wizard title="What shall we celebrate?" sub="Every milestone deserves to be held with care."
      footer={<Btn full onClick={()=>setStep(1)}>Continue <Icon name="chevR" size={18}/></Btn>}>
      <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:12}}>
        {OCCASIONS.map(o=>{
          const on = occasion.id===o.id; const [c]=TINTS[o.tint];
          return (
            <button key={o.id} onClick={()=>setOccasion(o)} style={{appearance:'none', cursor:'pointer', textAlign:'left',
              padding:16, borderRadius:'22px 22px 22px 22px', transition:'all .25s var(--ease)',
              background: on ? `color-mix(in srgb, ${c} 14%, var(--surface))` : 'var(--surface)',
              border: on ? `1.5px solid ${c}` : '1.5px solid var(--line)',
              transform: on ? 'translateY(-3px)' : 'none', boxShadow: on ? 'var(--shadow-md)':'var(--shadow-sm)'}}>
              <Emblem type={o.emblem} tint={o.tint} size={40}/>
              <div style={{fontWeight:700, fontSize:15.5, marginTop:12, color:'var(--ink)'}}>{o.en}</div>
              <div style={{fontSize:12.5, fontStyle:'italic', color:'var(--ink-2)', marginTop:1}}>{o.sub}</div>
            </button>
          );
        })}
      </div>
    </Wizard>
  );

  const DetailsStep = () => (
    <Wizard title={`Tell us about the ${occasion.en.toLowerCase()}`} sub="The little details help us shape your plan."
      footer={<Btn full onClick={()=>setStep(2)}>Continue <Icon name="chevR" size={18}/></Btn>}>
      <Field label="What shall we call it?">
        <input value={name} onChange={e=>setName(e.target.value)} style={inp}/>
      </Field>
      <div style={{display:'flex', gap:12}}>
        <Field label="When" style={{flex:1}}>
          <div style={{...inp, display:'flex', alignItems:'center', gap:8, color:'var(--ink)'}}><Icon name="cal" size={17}/> Sat, 14 Jun</div>
        </Field>
        <Field label="At what time" style={{flex:1}}>
          <div style={{...inp, display:'flex', alignItems:'center', gap:8, color:'var(--ink)'}}>6:30 PM</div>
        </Field>
      </div>
      <Field label="Where">
        <div style={{position:'relative'}}>
          <input value={place} onChange={e=>setPlace(e.target.value)} style={{...inp, paddingLeft:42}}/>
          <div style={{position:'absolute', left:14, top:'50%', transform:'translateY(-50%)', color:'var(--ink-2)'}}><Icon name="pin" size={18}/></div>
        </div>
      </Field>
      <Field label="The mood">
        <div style={{display:'flex', flexWrap:'wrap', gap:9}}>
          {VIBES.map(v=><Chip key={v} active={vibes.includes(v)} onClick={()=>toggleVibe(v)}>{v}</Chip>)}
        </div>
      </Field>
    </Wizard>
  );

  const GuestsStep = () => {
    const [n, setN] = useState('');
    const counts = {yes:0,maybe:0,pending:0};
    guests.forEach(g=>counts[g.rsvp]+=g.c);
    return (
    <Wizard title="Who's coming together?" sub="Group by household — the way families really gather."
      footer={<Btn full onClick={()=>setStep(3)}>Continue <Icon name="chevR" size={18}/></Btn>}>
      <div style={{background:'var(--surface)', border:'1px solid var(--line)', borderRadius:22, padding:18, boxShadow:'var(--shadow-sm)', marginBottom:18}}>
        <div style={{display:'flex', alignItems:'flex-end', gap:6}}>
          <div style={{fontFamily:'var(--font-display)', fontSize:42, lineHeight:1, color:'var(--ink)'}}>{totalGuests}</div>
          <div style={{fontSize:13, color:'var(--ink-2)', paddingBottom:6}}>guests · {guests.length} households</div>
        </div>
        <div style={{display:'flex', height:9, borderRadius:6, overflow:'hidden', marginTop:14, gap:2}}>
          <div style={{flex:counts.yes||0.001, background:'var(--leaf)'}}/>
          <div style={{flex:counts.maybe||0.001, background:'var(--saffron)'}}/>
          <div style={{flex:counts.pending||0.001, background:'var(--line)'}}/>
        </div>
        <div style={{display:'flex', gap:16, marginTop:10, fontSize:12, color:'var(--ink-2)'}}>
          <Legend c="var(--leaf)" t={`${counts.yes} coming`}/>
          <Legend c="var(--saffron)" t={`${counts.maybe} maybe`}/>
          <Legend c="var(--line)" t={`${counts.pending} pending`}/>
        </div>
      </div>
      <div style={{display:'flex', gap:10, marginBottom:16}}>
        <input value={n} onChange={e=>setN(e.target.value)} placeholder="Add a family or guest…"
          onKeyDown={e=>{if(e.key==='Enter'){addGuest(n); setN('');}}} style={{...inp, flex:1}}/>
        <Btn onClick={()=>{addGuest(n); setN('');}}><Icon name="plus" size={18}/></Btn>
      </div>
      <div style={{display:'flex', flexDirection:'column', gap:10}}>
        {guests.map((g,i)=>(
          <div key={i} style={{display:'flex', alignItems:'center', gap:12, padding:'12px 14px', borderRadius:18, background:'var(--surface)', border:'1px solid var(--line)'}}>
            <Avatar name={g.n} i={i} size={40}/>
            <div style={{flex:1, minWidth:0}}>
              <div style={{fontWeight:600, fontSize:14.5, color:'var(--ink)', whiteSpace:'nowrap', overflow:'hidden', textOverflow:'ellipsis'}}>{g.n}</div>
              <button onClick={()=>cycleRsvp(i)} style={rsvpStyle(g.rsvp)}>{g.rsvp==='yes'?'Coming':g.rsvp==='maybe'?'Maybe':'Pending'}</button>
            </div>
            <div style={{display:'flex', alignItems:'center', gap:8}}>
              <Stepper onMinus={()=>setGuestCount(i,-1)} onPlus={()=>setGuestCount(i,1)} val={g.c}/>
            </div>
          </div>
        ))}
      </div>
    </Wizard>
  );};

  const VendorsStep = () => {
    const cats = ['All', ...Array.from(new Set(VENDORS.map(v=>v.cat)))];
    const list = catFilter==='All' ? VENDORS : VENDORS.filter(v=>v.cat===catFilter);
    return (
    <Wizard title="Bring it to life" sub="Hand-picked partners, vetted for families like yours."
      footer={
        <div>
          <div style={{display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:10, fontSize:13.5}}>
            <span style={{color:'var(--ink-2)'}}>{chosen.length} added · est. budget</span>
            <span style={{fontWeight:800, fontSize:17, color:'var(--ink)'}}>₹{(budget/100000).toFixed(2)}L</span>
          </div>
          <Btn full onClick={()=>setStep(4)}>Build my plan <Icon name="chevR" size={18}/></Btn>
        </div>}>
      <div style={{display:'flex', gap:8, overflowX:'auto', marginBottom:18, paddingBottom:4, marginLeft:-2}} className="ty-scroll">
        {cats.map(c=><div key={c} style={{flexShrink:0}}><Chip active={catFilter===c} onClick={()=>setCatFilter(c)}>{c}</Chip></div>)}
      </div>
      <div style={{display:'flex', flexDirection:'column', gap:14}}>
        {list.map(v=>{
          const on = chosen.includes(v.id);
          return (
            <div key={v.id} style={{display:'flex', gap:13, padding:12, borderRadius:20, background:'var(--surface)',
              border: on?'1.5px solid var(--saffron)':'1px solid var(--line)', boxShadow:'var(--shadow-sm)', transition:'border .2s'}}>
              <div style={{width:84, flexShrink:0}}><Photo label={v.cat.toLowerCase()} tint={v.tint} h={92}/></div>
              <div style={{flex:1, minWidth:0, display:'flex', flexDirection:'column'}}>
                <div style={{fontSize:11, fontWeight:700, letterSpacing:'0.06em', textTransform:'uppercase', color:'var(--saffron)'}}>{v.cat}</div>
                <div style={{fontWeight:700, fontSize:15.5, color:'var(--ink)', marginTop:1}}>{v.name}</div>
                <div style={{fontSize:12.5, color:'var(--ink-2)', marginTop:1}}>{v.note}</div>
                <div style={{display:'flex', alignItems:'center', gap:10, marginTop:'auto', paddingTop:8}}>
                  <span style={{display:'inline-flex', alignItems:'center', gap:3, fontSize:12.5, fontWeight:700, color:'var(--ink)'}}><span style={{color:'var(--gold)'}}><Icon name="star" size={14}/></span>{stars(v.rating)}</span>
                  <span style={{fontSize:12.5, color:'var(--ink-3)'}}>{priceStr(v.price)}</span>
                  <span style={{fontSize:12.5, color:'var(--ink-2)', marginLeft:'auto'}}>{v.from}</span>
                </div>
              </div>
              <button onClick={()=>toggleVendor(v.id)} aria-label="add" style={{alignSelf:'center', appearance:'none', cursor:'pointer',
                width:38, height:38, borderRadius:12, flexShrink:0, border:'none',
                background: on?'var(--saffron)':'var(--surface-2)', color: on?'var(--on-primary)':'var(--ink-2)',
                display:'flex', alignItems:'center', justifyContent:'center', boxShadow: on?'var(--shadow-sm)':'none'}}>
                <Icon name={on?'check':'plus'} size={20} sw={2.1}/></button>
            </div>
          );
        })}
      </div>
    </Wizard>
  );};

  const PlanStep = () => (
    <Wizard title="Your celebration plan" sub="We sequenced everything. Tick along — or let family help."
      footer={<Btn full onClick={finishPlan}>Finish & open celebration <Icon name="spark" size={18}/></Btn>}>
      <div style={{display:'flex', alignItems:'center', gap:16, padding:18, borderRadius:22, background:'var(--surface)', border:'1px solid var(--line)', boxShadow:'var(--shadow-sm)', marginBottom:22}}>
        <Ring pct={planPct} size={66} sw={6}><span style={{fontSize:17}}>{planPct}%</span></Ring>
        <div>
          <div style={{fontWeight:700, fontSize:15.5, color:'var(--ink)'}}>{doneTasks} of {totalTasks} done</div>
          <div style={{fontSize:13, color:'var(--ink-2)', marginTop:2, lineHeight:1.4}}>Tyohaar keeps the timeline.<br/>You keep the joy.</div>
        </div>
      </div>
      {tasks.map((p,pi)=>(
        <div key={pi} style={{position:'relative', paddingLeft:26, marginBottom:8}}>
          <div style={{position:'absolute', left:5, top:6, bottom:-2, width:2, background:'var(--line)'}}/>
          <div style={{position:'absolute', left:0, top:6, width:12, height:12, borderRadius:'50%', background:'var(--saffron)', border:'2px solid var(--paper)'}}/>
          <div style={{fontWeight:800, fontSize:12.5, letterSpacing:'0.04em', textTransform:'uppercase', color:'var(--ink-2)', marginBottom:10}}>{p.phase}</div>
          <div style={{display:'flex', flexDirection:'column', gap:9, marginBottom:18}}>
            {p.items.map((it,ii)=>(
              <button key={ii} onClick={()=>toggleTask(pi,ii)} style={{appearance:'none', cursor:'pointer', textAlign:'left',
                display:'flex', alignItems:'center', gap:12, padding:'12px 14px', borderRadius:16,
                background:'var(--surface)', border:'1px solid var(--line)'}}>
                <div style={{width:24, height:24, borderRadius:8, flexShrink:0, transition:'all .2s var(--ease)',
                  background: it.done?'var(--leaf)':'transparent', border: it.done?'none':'2px solid var(--line)',
                  color:'#fff', display:'flex', alignItems:'center', justifyContent:'center'}}>
                  {it.done && <Icon name="check" size={15} sw={2.4}/>}</div>
                <div style={{flex:1}}>
                  <div style={{fontSize:14, fontWeight:600, color:'var(--ink)', textDecoration: it.done?'line-through':'none', opacity: it.done?0.55:1}}>{it.t}</div>
                  <div style={{fontSize:11.5, color:'var(--ink-3)', marginTop:1}}>{it.who}</div>
                </div>
              </button>
            ))}
          </div>
        </div>
      ))}
    </Wizard>
  );

  /* ───────── EVENT HUB ───────── */
  const Event = () => (
    <ScreenRoot>
      <Celebrate run={celebrate}/>
      <Scroll pad={false}>
        <div style={{position:'relative'}}>
          <Photo label="" tint={occasion.tint} h={380} arch={false}/>
          <div style={{position:'absolute', inset:0, background:'linear-gradient(to top, var(--paper) 2%, rgba(0,0,0,0.25) 40%, rgba(0,0,0,0.35) 100%)'}}/>
          <div style={{position:'absolute', top:50, left:18, right:18, display:'flex', justifyContent:'space-between'}}>
            <button onClick={()=>setView('home')} style={{appearance:'none', border:'none', cursor:'pointer', width:42, height:42, borderRadius:14, background:'rgba(255,255,255,0.18)', backdropFilter:'blur(8px)', color:'#fff', display:'flex', alignItems:'center', justifyContent:'center'}}><Icon name="chevL" size={22}/></button>
            <button style={{appearance:'none', border:'none', cursor:'pointer', width:42, height:42, borderRadius:14, background:'rgba(255,255,255,0.18)', backdropFilter:'blur(8px)', color:'#fff', display:'flex', alignItems:'center', justifyContent:'center'}}><Icon name="heart" size={20}/></button>
          </div>
          <div style={{position:'absolute', left:20, right:20, bottom:18, color:'#fff'}}>
            <span style={{...pill, background:'var(--saffron)', color:'var(--on-primary)'}}>{occasion.en} · {occasion.sub}</span>
            <div style={{fontFamily:'var(--font-display)', fontSize:38, lineHeight:1.02, marginTop:12}}>{name}</div>
            <div style={{fontSize:14, opacity:0.92, marginTop:8, display:'flex', alignItems:'center', gap:8}}><Icon name="cal" size={16}/> Sat, 14 June · 6:30 PM</div>
          </div>
        </div>
        <div style={{padding:'0 18px 28px', marginTop:-14, position:'relative'}}>
          <div style={{display:'flex', gap:10, marginBottom:22}}>
            {[['11','days'],['06','hrs'],['142','guests']].map(([n,l],i)=>(
              <div key={i} style={{flex:1, background:'var(--surface)', border:'1px solid var(--line)', borderRadius:18, padding:'14px 8px', textAlign:'center', boxShadow:'var(--shadow-sm)'}}>
                <div style={{fontFamily:'var(--font-display)', fontSize:26, color:'var(--ink)', lineHeight:1}}>{i===2?totalGuests:n}</div>
                <div style={{fontSize:11, color:'var(--ink-2)', marginTop:4, textTransform:'uppercase', letterSpacing:'0.05em'}}>{l}</div>
              </div>
            ))}
          </div>
          <SectionHead title="The plan" action="View all" onAction={()=>{setStep(4); setView('create');}}/>
          <div style={{display:'flex', alignItems:'center', gap:16, padding:16, borderRadius:20, background:'var(--surface)', border:'1px solid var(--line)', boxShadow:'var(--shadow-sm)', marginBottom:24}}>
            <Ring pct={planPct} size={56}><span style={{fontSize:14}}>{planPct}%</span></Ring>
            <div style={{flex:1}}>
              <div style={{fontWeight:700, fontSize:15, color:'var(--ink)'}}>On track</div>
              <div style={{fontSize:12.5, color:'var(--ink-2)', marginTop:2}}>Next: {tasks.flatMap(p=>p.items).find(i=>!i.done)?.t || 'All done!'}</div>
            </div>
          </div>
          <SectionHead title="Your dream team" action="Add" onAction={()=>{setStep(3); setView('create');}}/>
          <div style={{display:'flex', flexDirection:'column', gap:10, marginBottom:24}}>
            {chosen.map(id=>{const v=VENDORS.find(x=>x.id===id); return (
              <div key={id} style={{display:'flex', alignItems:'center', gap:12, padding:10, borderRadius:16, background:'var(--surface)', border:'1px solid var(--line)'}}>
                <div style={{width:48}}><Photo label="" tint={v.tint} h={48}/></div>
                <div style={{flex:1}}><div style={{fontWeight:700, fontSize:14, color:'var(--ink)'}}>{v.name}</div><div style={{fontSize:12, color:'var(--ink-2)'}}>{v.cat}</div></div>
                <span style={{display:'inline-flex', alignItems:'center', gap:3, fontSize:12.5, fontWeight:700, color:'var(--ink)'}}><span style={{color:'var(--gold)'}}><Icon name="star" size={13}/></span>{stars(v.rating)}</span>
              </div>
            );})}
          </div>
          <SectionHead title="The gathering" action="Manage" onAction={()=>{setStep(2); setView('create');}}/>
          <div style={{display:'flex', alignItems:'center', gap:14, padding:16, borderRadius:20, background:'var(--surface)', border:'1px solid var(--line)', boxShadow:'var(--shadow-sm)'}}>
            <div style={{display:'flex'}}>{guests.slice(0,5).map((g,i)=>(<div key={i} style={{marginLeft:i?-10:0}}><Avatar name={g.n} i={i} size={36}/></div>))}</div>
            <div style={{flex:1}}><div style={{fontWeight:700, fontSize:15, color:'var(--ink)'}}>{totalGuests} loved ones</div><div style={{fontSize:12.5, color:'var(--ink-2)'}}>{guests.length} households invited</div></div>
            <Icon name="chevR" size={20}/>
          </div>
        </div>
      </Scroll>
      <TabBar view="" go={setView} onCreate={startCreate}/>
    </ScreenRoot>
  );

  const AppPlaceholder = ({icon,label}) => (
    <ScreenRoot>
      <TopBar><div style={{fontFamily:'var(--font-display)', fontSize:27, paddingTop:4}}>{label}</div></TopBar>
      <div style={{flex:1, display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', gap:14, color:'var(--ink-3)', padding:40, textAlign:'center'}}>
        <div style={{color:'var(--saffron)'}}><Icon name={icon} size={40}/></div>
        <div style={{fontSize:14.5, lineHeight:1.5, color:'var(--ink-2)'}}>This space is part of the full Tyohaar app. The interactive flow here is <b style={{color:'var(--ink)'}}>Plan a celebration</b> — tap the centre button to begin.</div>
        <Btn onClick={startCreate}>Start a celebration</Btn>
      </div>
      <TabBar view={view} go={setView} onCreate={startCreate}/>
    </ScreenRoot>
  );

  let screen;
  if (view==='create') screen = [<OccasionStep/>,<DetailsStep/>,<GuestsStep/>,<VendorsStep/>,<PlanStep/>][step];
  else if (view==='event') screen = <Event/>;
  else if (view==='home') screen = <Home/>;
  else if (view==='plan') screen = <AppPlaceholder icon="plan" label="Plan"/>;
  else if (view==='vendors') screen = <AppPlaceholder icon="vendors" label="Vendors"/>;
  else screen = <AppPlaceholder icon="heart" label="Memories"/>;

  return (
    <div ref={dev} data-theme={theme}>
      <IOSDevice dark={theme==='dark'} width={width} height={height}>{screen}</IOSDevice>
    </div>
  );
}

/* ─── small helpers (module-scoped) ─── */
const pill = { fontSize:12, fontWeight:700, padding:'5px 11px', borderRadius:999, background:'rgba(255,255,255,0.9)', color:'#2A2018', backdropFilter:'blur(6px)', whiteSpace:'nowrap' };
const hd   = { fontFamily:'var(--font-sans)', fontWeight:800, fontSize:15, letterSpacing:'0.01em', color:'var(--ink)', margin:0 };
const inp  = { width:'100%', appearance:'none', fontFamily:'var(--font-sans)', fontSize:15.5, fontWeight:500, padding:'14px 16px', borderRadius:14, border:'1.5px solid color-mix(in srgb, var(--ink) 22%, transparent)', background:'var(--surface)', color:'var(--ink)', outline:'none', boxSizing:'border-box' };

function Field({ label, children, style={} }) {
  return <div style={{marginBottom:18, ...style}}>
    <div style={{fontSize:12.5, fontWeight:700, color:'var(--ink-2)', marginBottom:8, letterSpacing:'0.01em'}}>{label}</div>
    {children}</div>;
}
function Legend({c,t}){ return <span style={{display:'inline-flex', alignItems:'center', gap:6}}><span style={{width:9, height:9, borderRadius:'50%', background:c}}/>{t}</span>; }
function Stepper({onMinus,onPlus,val}){
  const b={appearance:'none', border:'1px solid var(--line)', background:'var(--surface-2)', width:30, height:30, borderRadius:9, cursor:'pointer', color:'var(--ink)', display:'flex', alignItems:'center', justifyContent:'center', fontSize:18, fontWeight:700};
  return <div style={{display:'flex', alignItems:'center', gap:8}}>
    <button onClick={onMinus} style={b}>–</button>
    <span style={{minWidth:18, textAlign:'center', fontWeight:700, fontSize:15, color:'var(--ink)'}}>{val}</span>
    <button onClick={onPlus} style={b}>+</button></div>;
}
function rsvpStyle(r){
  const map={yes:['var(--leaf)','Coming'],maybe:['var(--saffron)','Maybe'],pending:['var(--ink-3)','Pending']};
  const c=map[r][0];
  return {appearance:'none', cursor:'pointer', border:'none', marginTop:4, fontSize:11.5, fontWeight:700, padding:'3px 10px', borderRadius:999, background:`color-mix(in srgb, ${c} 16%, transparent)`, color:c};
}
function SectionHead({title,action,onAction}){
  return <div style={{display:'flex', alignItems:'baseline', justifyContent:'space-between', marginBottom:12}}>
    <h3 style={{fontFamily:'var(--font-display)', fontSize:21, fontWeight:400, color:'var(--ink)', margin:0}}>{title}</h3>
    {action && <button onClick={onAction} style={{appearance:'none', border:'none', background:'transparent', cursor:'pointer', fontSize:13, fontWeight:700, color:'var(--saffron)'}}>{action}</button>}
  </div>;
}
