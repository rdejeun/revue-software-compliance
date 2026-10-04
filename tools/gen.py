"""Génère l'édition (e-mail et web) à partir de blocks.json et meta.json du dossier courant.
Usage : python3 gen.py DOSSIER_SORTIE   (écrit revue-email.html, revue-web.html, items.json)"""
import re,json,html
from urllib.parse import urlparse
import commun as B
from commun import typo,E,esc,mark,blocks,G,used,seen,SANS,SERIF,NB
import sys,os
META=json.load(open('meta.json'))
# Épisode audio (tools/podcast.py) : présent seulement s'il a été produit pour cette édition
EP=json.load(open('episode.json')) if os.path.isfile('episode.json') and os.path.isfile('episode.mp3') else None
POD=json.load(open('podcast.json')) if EP and os.path.isfile('podcast.json') else None
PHR={"Une déclaration CRA ne remplace pas":None,"Chainguard":None,"déclarer les vulnérabilités activement exploitées et les incidents graves":None}
NAVY='#0f2a4a'
ACC='#c2410c'
# Sources « officielles » (texte juridique, autorité publique, organisme de normalisation) : mises en relief
OFFICIEL=('europa.eu','federalregister.gov','ecfr.gov','govinfo.gov','bis.gov','bis.doc.gov','treasury.gov','state.gov','cisa.gov','nist.gov','defense.gov','gouv.fr','assemblee-nationale.fr','senat.fr','gov.uk','iso.org','etsi.org','cencenelec.eu')
def officiel(u):
    h=(urlparse(u).hostname or '').lower()
    return any(h==d or h.endswith('.'+d) for d in OFFICIEL)
MOIS=['janv.','févr.','mars','avr.','mai','juin','juil.','août','sept.','oct.','nov.','déc.']
def fdate(iso):
    """'2026-10-01' -> '1er oct.' ; '2026-12' -> 'déc. 2026' ; année affichée si différente de celle de l'édition"""
    if not iso: return ''
    p=iso.split('-'); y=p[0]; m=int(p[1])
    s_=MOIS[m-1]
    if len(p)>2: d=int(p[2]); s_=('1er' if d==1 else str(d))+'\u00a0'+s_
    if y!=str(META.get('date_iso',''))[:4] or len(p)==2: s_+='\u00a0'+y
    return s_
ITEMS=[]   # éléments rendus (version web), exportés dans items.json pour le site (dossiers, Markdown)
def lead(items):
    """découpe le 1er segment texte en [pré, GRAS, reste]"""
    if not items or items[0].get('href'): return items
    t=items[0]['t']
    for ph in PHR:
        i=t.find(ph)
        if i>=0 and (ph!='Chainguard' or i==0):
            return [{'t':t[:i]},{'t':ph,'b':1},{'t':t[i+len(ph):]}]+items[1:]
    m=re.match(r'^([^:]{1,90}?)(\s:)',t)
    if m: return [{'t':m.group(1),'b':1},{'t':t[m.end(1):]}]+items[1:]
    return items
JS=r'''<dialog class="sy" id="sy" aria-labelledby="sy-h"><button type="button" class="sy-x" aria-label="Fermer">×</button><div class="sy-w" id="sy-c"></div></dialog>
<script>
(function(){
var dlg=document.getElementById('sy'),box=document.getElementById('sy-c');
function open(id,push){var d=document.getElementById('d-'+id);if(!d)return;box.innerHTML=d.innerHTML;var h=box.querySelector('.sy-t');if(h)h.id='sy-h';box.scrollTop=0;if(!dlg.open)dlg.showModal();if(push!==false)try{history.replaceState(null,'','#'+id)}catch(e){}}
function close(){if(dlg.open)dlg.close()}
dlg.addEventListener('close',function(){try{history.replaceState(null,'',location.pathname+location.search)}catch(e){}});
dlg.querySelector('.sy-x').addEventListener('click',close);
box.addEventListener('mouseover',function(e){var t=e.target.closest&&e.target.closest('a.t');if(!t)return;var r=t.getBoundingClientRect(),c=box.getBoundingClientRect();t.classList.toggle('r',r.left-c.left>c.width/2)});
dlg.addEventListener('click',function(e){if(e.target===dlg)close()});
document.addEventListener('click',function(e){
 var b=e.target.closest('[data-syn]');if(!b||dlg.contains(b))return;
 var a=e.target.closest('a');
 if(a&&!a.hasAttribute('data-syn'))return; /* liens sources et glossaire : comportement normal */
 e.preventDefault();open(b.getAttribute('data-syn'));
});
document.addEventListener('keydown',function(e){var it=e.target.closest&&e.target.closest('.sy-it');if(it&&(e.key==='Enter'||e.key===' ')&&e.target===it){e.preventDefault();open(it.getAttribute('data-syn'))}});
var h=location.hash.slice(1);if(/^syn\d+$/.test(h))open(h,false);
})();
</script>'''
NO_EL=False   # passe à True si l'e-mail dépasse la limite de taille : liens par élément retirés
SYN_LABELS=[('essentiel','L’essentiel'),('contexte','Contexte')]
REDACTION_DEFAUT='Anthropic Claude Opus 5.5'   # meta.json « redaction » : <éditeur> <modèle> <version>
# Image d'en-tête facultative (version web) : tools/en-tete.(webp|png|jpg), publiée sous /assets/
_TOOLS=os.path.dirname(os.path.abspath(__file__))
EN_TETE=next((f'/assets/en-tete.{x}' for x in ('webp','png','jpg') if os.path.isfile(os.path.join(_TOOLS,f'en-tete.{x}'))),None)
def duree_ep():
    d=EP['duree_s']
    return f'{d}&nbsp;s' if d<60 else f'{round(d/60)}&nbsp;min'
ICO_PLAY='<svg viewBox="0 0 16 16" width="12" height="12" aria-hidden="true"><path d="M4 2.5v11l9.5-5.5z" fill="currentColor"/></svg>'
def bloc_podcast(web,diso,ed_url):
    """Barre « Écouter l'épisode » (80 %, centrée) entre l'en-tête et la Une.
    Web : se déplie au clic (lecteur aux couleurs de la page). E-mail : lien vers la page web."""
    if not EP or not diso: return ''
    m=duree_ep()
    if not web:
        if not ed_url: return ''
        return (f'<table role="presentation" width="80%" align="center" cellpadding="0" cellspacing="0" style="width:80%;margin:0 auto 26px;background:#f7f4ee;border:1px solid #e3d6c3;border-radius:22px;">'
                f'<tr><td style="padding:10px 18px;"><a href="{ed_url}#ecouter" style="display:block;text-decoration:none;"><table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>'
                f'<td style="font:600 14px/22px {SANS};color:{NAVY};"><span style="color:{ACC};">&#9654;</span>&nbsp;&nbsp;Écouter l’épisode</td>'
                f'<td align="right" style="font:13px/22px {SANS};color:#6b7280;white-space:nowrap;">{m}</td></tr></table></a></td></tr></table>')
    titre=esc(typo((POD or {}).get('titre','')))
    return (f'<div class="pod" id="ecouter">'
            f'<button type="button" class="pod-h" aria-expanded="false" aria-controls="pod-b"><span class="pod-i">{ICO_PLAY}</span><span class="pod-l">Écouter l’épisode</span><span class="pod-d">{m}</span></button>'
            f'<div class="pod-b" id="pod-b" role="region" aria-label="Podcast"><div class="pod-in">'
            f'<div class="pod-eb">Podcast</div>'
            + (f'<div class="pod-t">{titre}</div>' if titre else '') +
            f'<audio preload="none" src="/{diso}/episode.mp3"></audio>'
            f'<div class="pod-p"><button type="button" class="pod-pl" aria-label="Lecture">{ICO_PLAY}</button>'
            f'<input class="pod-r" type="range" min="0" max="{EP["duree_s"]}" step="0.1" value="0" aria-label="Position dans l’épisode">'
            f'<span class="pod-tm"><span class="pod-c">0:00</span> / {EP["duree_s"]//60}:{EP["duree_s"]%60:02d}</span></div>'
            f'<p class="pod-n">Ce dialogue a été produit par une intelligence artificielle.</p>'
            f'</div></div></div>')
POD_JS=r"""<script>
(function(){
var w=document.getElementById('ecouter');if(!w)return;
var h=w.querySelector('.pod-h'),b=w.querySelector('.pod-b'),a=w.querySelector('audio'),pl=w.querySelector('.pod-pl'),r=w.querySelector('.pod-r'),c=w.querySelector('.pod-c');
var PLAY=pl.innerHTML,PAUSE='<svg viewBox="0 0 16 16" width="12" height="12" aria-hidden="true"><path d="M4 2.5h3v11H4zM9 2.5h3v11H9z" fill="currentColor"/></svg>';
function fmt(t){t=Math.floor(t||0);return Math.floor(t/60)+':'+('0'+t%60).slice(-2)}
function set(o){w.classList.toggle('on',o);h.setAttribute('aria-expanded',o);b.style.maxHeight=o?b.scrollHeight+'px':'0px'}
h.addEventListener('click',function(){set(!w.classList.contains('on'))});
pl.addEventListener('click',function(){if(a.paused)a.play();else a.pause()});
a.addEventListener('play',function(){pl.innerHTML=PAUSE;pl.setAttribute('aria-label','Pause')});
a.addEventListener('pause',function(){pl.innerHTML=PLAY;pl.setAttribute('aria-label','Lecture')});
a.addEventListener('loadedmetadata',function(){if(isFinite(a.duration))r.max=a.duration});
a.addEventListener('timeupdate',function(){if(!r.matches(':active'))r.value=a.currentTime;c.textContent=fmt(a.currentTime);r.style.setProperty('--p',(100*a.currentTime/(r.max||1))+'%')});
r.addEventListener('input',function(){a.currentTime=+r.value;c.textContent=fmt(r.value);r.style.setProperty('--p',(100*r.value/(r.max||1))+'%')});
if(location.hash==='#ecouter')set(true);
})();
</script>"""
PILL_JS=r"""<script>
(function(){
/* Pastille « En savoir plus » : se déploie vers la droite ; si elle dépasse la marge droite du texte, elle se décale d'autant vers la gauche. */
function grow(e){var b=e.target.closest&&e.target.closest('.sy-b');if(!b)return;var p=b.querySelector('.sy-p'),l=b.querySelector('.sy-l');if(!p||!l)return;
 var col=b.closest('td,p,.sy-ev')||b.parentNode,lim=col.getBoundingClientRect().right,cs=getComputedStyle(col),pr=parseFloat(cs.paddingRight)||0;
 var W=b.offsetWidth+l.scrollWidth+10,L=b.getBoundingClientRect().left;p.style.left=(-Math.max(0,L+W-(lim-pr)))+'px'}
function shrink(e){var b=e.target.closest&&e.target.closest('.sy-b');if(!b||b.contains(e.relatedTarget))return;var p=b.querySelector('.sy-p');if(p)p.style.left='0px'}
document.addEventListener('mouseover',grow);document.addEventListener('focusin',grow);
document.addEventListener('mouseout',shrink);document.addEventListener('focusout',shrink);
})();
</script>"""
def render(web):
    seen.clear();used.clear()
    if web: ITEMS.clear()
    syns=[]
    SITE=(META.get('site') or '').rstrip('/'); DISO=META.get('date_iso') or ''
    ED_URL=f'{SITE}/{DISO}/' if SITE and DISO else ''
    def EL(sid): return '' if NO_EL else f' <a href="{ED_URL}#{sid}" style="color:{ACC};font-size:14px;text-decoration:none;white-space:nowrap">En savoir plus&nbsp;↗</a>' if ED_URL else ''
    def syn_html(sm,srcs,sec):
        """fiche de synthèse (version web) ; en version e-mail, réserve seulement le numéro pour les liens"""
        if not web:
            syns.append(None); return f'syn{len(syns)}'
        T=lambda x:E(typo(x))
        sv_seen=set(seen); sv_used=list(used); seen.clear()
        M=lambda x:mark(x,True)
        h=[f'<p class="sy-eb">{T(sec)}</p><h3 class="sy-t">{T(sm.get("titre",""))}</h3>']
        meta=[]
        if sm.get('statut'): meta.append(f'<dt>Statut</dt><dd>{T(sm["statut"])}</dd>')
        if sm.get('fonctions'): meta.append(f'<dt>Fonctions concernées</dt><dd>{T(sm["fonctions"])}</dd>')
        if meta: h.append('<dl class="sy-m">'+''.join(meta)+'</dl>')
        for k,lab in SYN_LABELS:
            if sm.get(k): h.append(f'<h4>{lab}</h4><p>{M(sm[k])}</p>')
        if sm.get('impact_avere') or sm.get('impact_potentiel'):
            h.append('<h4>Impact</h4>')
            for k in ('impact_avere','impact_potentiel'):
                if sm.get(k): h.append(f'<p>{M(sm[k])}</p>')
        if sm.get('a_verifier'):
            h.append('<h4>À vérifier</h4><ul class="sy-v">'+''.join(f'<li>{M(q)}</li>' for q in sm['a_verifier'])+'</ul>')
        if srcs:
            h.append('<p class="sy-s">'+' '.join(f'<a href="{esc(u,True)}" target="_blank" rel="noopener">↗&nbsp;{T(l)}</a>' for l,u in srcs)+'</p>')
        seen.clear(); seen.update(sv_seen); used[:]=sv_used
        sid=f'syn{len(syns)+1}'
        syns.append(f'<div class="sy-d" id="d-{sid}" hidden>{"".join(h)}</div>')
        return sid
    def srcs_of(items): return [(x['t'],x['href']) for x in items if x.get('href')]
    SYNB='<button type="button" class="sy-b" data-syn="{0}" aria-haspopup="dialog" aria-label="En savoir plus"><span class="sy-p"><svg viewBox="0 0 16 16" width="12" height="12" aria-hidden="true"><path d="M8 3.5v9M3.5 8h9" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg><span class="sy-l">En savoir plus</span></span></button>'

    LS="color:#6b7280;font:13px/1 %s;text-decoration:none;border-bottom:1px dotted #9ca3af;white-space:nowrap;"%SANS
    LSO="color:#454e5c;font:600 13px/1 %s;text-decoration:none;border-bottom:1px solid #9aa1ab;white-space:nowrap;"%SANS
    def srcfix(items):
        o=[];n=len(items)
        for k,x in enumerate(items):
            x=dict(x);t=x['t']
            nx=items[k+1] if k+1<n else None
            pv=items[k-1] if k>0 else None
            if not x.get('href'):
                if pv and pv.get('href') and t.startswith(')'): t=t[1:]
                if nx and nx.get('href') and t.rstrip().endswith('('): t=t.rstrip()[:-1].rstrip()+' '
                elif pv and nx and pv.get('href') and nx.get('href') and t.strip()==',': t=' '
                x['t']=t
            else: x['t']='↗\u00a0'+x['t']
            o.append(x)
        return o
    def inl(items,bold=True,fs=16):
        if bold: items=lead(items)
        items=srcfix(items)
        r=[]
        for x in items:
            t=x['t']
            if not t and not x.get('href'): continue
            if x.get('href'):
                a=esc(x['href'],True)
                o_=officiel(x['href'])
                r.append(f'<a class="s{" so" if o_ else ""}" href="{a}" target="_blank" rel="noopener">{E(typo(t))}</a>' if web else f'<a href="{a}" style="{LSO if o_ else LS}{"font-size:12px;" if fs<16 else ""}">{E(typo(t))}</a>')
            elif x.get('b'):
                r.append(f'<b style="font:600 {fs}px/1 {SANS};color:{NAVY};">{mark(t,web)}</b>')
            else: r.append(mark(t,web))
        return ''.join(r)
    BODY=f"margin:0 0 16px;font:16px/24px {SERIF};color:#1f2937;"
    def tail(segs,attrs):
        """mention « source commerciale » et date de l'information, après les sources"""
        hs=[x for x in segs if x.get('href')]
        t=[]
        if hs and all(x.get('type')=='editeur' for x in hs): t.append('source commerciale')
        d=fdate((attrs or {}).get('date'))
        if d: t.append(d)
        return f' <span style="color:#8a8f98;font:12px/16px {SANS};">· {E(typo(" · ".join(t)))}</span>' if t else ''
    def item(segs,sm,attrs,kind,small=False):
        sid=syn_html(sm,srcs_of(segs),cursec) if sm else None
        inner=inl(segs,fs=14 if small else 16); tl=tail(segs,attrs)
        fin='' if tl.endswith('.</span>') else '.'
        inner=inner[:-1]+tl+fin if (tl and inner.endswith('.')) else inner+tl
        if web:
            ITEMS.append({'sid':sid,'sec':cursec,'kind':kind,'rappel':bool((attrs or {}).get('rappel')),'date':(attrs or {}).get('date'),'themes':(attrs or {}).get('themes',[]),'segs':segs,'sum':sm,'html':B._post(inner)})
        if sid: inner+=(' '+SYNB.format(sid)) if web else EL(sid)
        return sid,inner
    def syattr(sid): return f' class="sy-it" data-syn="{sid}"' if (web and sid) else ''
    def row(sid,inner):
        return f'<tr{syattr(sid)}><td width="20" valign="top" style="padding:8px 0 0;font:8px/8px Arial,sans-serif;color:#dba98f;">&#9632;</td><td style="padding:0 0 12px;font:16px/24px {SERIF};color:#1f2937;">{inner}</td></tr>'
    def rcell(sid,inner):
        return f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr{syattr(sid)}><td width="16" valign="top" style="padding:7px 0 0;font:7px/7px Arial,sans-serif;color:#dba98f;">&#9632;</td><td style="padding:0 0 10px;font:14px/20px {SERIF};color:#374151;">{inner}</td></tr></table>'
    rap=[]   # rappels de la section courante, affichés en fin de section sur deux colonnes
    def flush():
        if not rap: return
        cells=[rcell(*item(sg,sm,a,kd,small=True)) for sg,sm,a,kd in rap]
        rows_=''.join(f'<tr><td class="c2" width="50%" valign="top" style="padding:0 10px 0 0;">{cells[i]}</td><td class="c2" width="50%" valign="top" style="padding:0 0 0 10px;">{cells[i+1] if i+1<len(cells) else "&nbsp;"}</td></tr>' for i in range(0,len(cells),2))
        ln='<div style="border-top:1px solid #e3ddd0;font-size:0;line-height:0;">&nbsp;</div>'
        body.append(f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:4px 0 10px;"><tr><td width="50%" valign="middle">{ln}</td><td valign="middle" style="padding:0 12px;font:700 11px/16px {SANS};letter-spacing:.12em;text-transform:uppercase;color:#7d6c47;white-space:nowrap;">Rappels</td><td width="50%" valign="middle">{ln}</td></tr></table><table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 6px;">{rows_}</table>')
        rap.clear()
    CHAPO=f"margin:0 0 20px;font:17px/24px {SERIF};color:#4b5563;"
    body=[];title='';h2n=-1;first_p=True;prev_h2=False;cursec=''
    for b in blocks:
        k=b['k']
        if k=='h1': title=''.join(x['t'] for x in b['i']);continue
        if k=='h2':
            t=''.join(x['t'] for x in b['i']).strip()
            flush()
            if t.startswith(('Audit','Sources')): break
            h2n+=1;cursec=t
            body.append(f'<div style="margin:{50 if h2n else 38}px 0 14px;"><div style="width:30px;height:3px;background:{ACC};font-size:0;line-height:3px;">&nbsp;</div><h2 id="s{h2n}" style="margin:12px 0 0;font:600 22px/30px {SANS};color:{NAVY};">{E(typo(t))}</h2></div>')
            prev_h2=True;continue
        if k=='p':
            raw=''.join(x['t'] for x in b['i']).strip(' ·')
            if not raw: continue
            if raw.startswith(('Cette section ne retient','Les échéances d')) or cursec.startswith('Agenda'): continue
            if first_p:
                first_p=False
                body.append(f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 16px;"><tr><td style="border-left:4px solid #1f4e8c;background:#eef2f8;background-image:linear-gradient(45deg,#e4ecf7 0%,#f6f9fd 100%);padding:16px 20px;font:17.7px/26px {SERIF};color:{NAVY};">{inl(b["i"],False)}</td></tr></table>')
                body.append('@@TOC@@');continue
            if prev_h2 and not raw.startswith(('Depuis le','Défense','Lien avec')) and ':' not in raw[:60]:
                body.append(f'<p style="{CHAPO}">{inl(b["i"],False)}</p>')
            else:
                a=b.get('attrs') or {}
                if a.get('rappel'): rap.append((b['i'],b.get('sum'),a,'p'))
                else:
                    sid,inner=item(b['i'],b.get('sum'),a,'p')
                    body.append(f'<p{syattr(sid)} style="{BODY}">{inner}</p>')
            prev_h2=False
        elif k=='ul':
            sums=b.get('sum') or []; ats=b.get('attrs') or []
            rows_=[]
            for j_,it in enumerate(b['items']):
                sm=sums[j_] if j_<len(sums) else None; a=(ats[j_] if j_<len(ats) else None) or {}
                if a.get('rappel'): rap.append((it,sm,a,'ul')); continue
                rows_.append(row(*item(it,sm,a,'ul')))
            li=''.join(rows_)
            prev_h2=False
            if not li: continue
            body.append(f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 10px;">{li}</table>');prev_h2=False
        elif k=='table':
            if 'Date' not in ''.join(x['t'] for x in b['rows'][0][0]): continue
            MO={'janvier':'janv.','février':'févr.','mars':'mars','avril':'avr.','mai':'mai','juin':'juin','juillet':'juil.','août':'août','septembre':'sept.','octobre':'oct.','novembre':'nov.','décembre':'déc.'}
            import math
            CPL=40; CAP=39   # caractères par ligne ; hauteur max d'une colonne (en lignes, réf. édition du 4 octobre 2026)
            det=b.get('detail') or []; asum=b.get('sum') or []; aat=b.get('attrs') or []
            groups={}
            for ri_,r in enumerate(b['rows'][1:]):
                d=''.join(x['t'] for x in r[0]).strip()
                m=re.match(r'^(?:(\d+)(?: au (\d+))? )?(\w+) (\d{4})$',d)
                a,z,mo,yr=m.groups(); mo=mo.lower()
                lab='%s – %s %s'%(a,z,MO[mo]) if z else ('%s %s'%(a if a!='1' else '1er',MO[mo]) if a else 'Attendu')
                u=(''.join(x.get('href','') for x in r[1]) or META['agenda_refs'][ri_])
                dt=det[ri_] if ri_<len(det) else None
                sm=asum[ri_] if ri_<len(asum) else None
                groups.setdefault((yr,mo),[]).append({'lab':lab,'t':r[1],'th':''.join(x['t'] for x in r[2]).strip(),'u':u,'det':dt,'sum':sm,'long':False,'date':d,'themes':((aat[ri_] if ri_<len(aat) else None) or {}).get('themes',[])})
            def tlen(e): return len(e['det']) if e['long'] else len(''.join(x['t'] for x in e['t']))
            def ecost(e): return 1.9+math.ceil(tlen(e)/CPL)
            def gcost(its): return 2.5+sum(ecost(e) for e in its)
            def colcost(gs): return sum(gcost(g) for g in gs)+max(0,len(gs)-1)
            G_=list(groups.values())
            cut=min(range(1,len(G_)),key=lambda c:abs(colcost(G_[:c])-colcost(G_[c:]))) if len(G_)>1 else len(G_)
            # allonger les événements de la colonne la plus courte, sans dépasser la plus haute
            L,R=G_[:cut],G_[cut:]
            short,tall=(L,R) if colcost(L)<colcost(R) else (R,L)
            for g in short:
                for e in g:
                    if e['det'] and colcost(short)<colcost(tall):
                        e['long']=True
                        if colcost(short)>colcost(tall): e['long']=False
            hmax=max(colcost(L),colcost(R))
            if hmax>CAP: print(f'ATTENTION agenda trop haut : {hmax:.1f} lignes estimées > {CAP} ; raccourcir ou retirer des événements', file=sys.stderr)
            def agt(t):
                h=inl(t,False) if isinstance(t,list) else mark(t,web)
                return re.sub(r'<a [^>]*?(?:title|data-tip)="([^"]*)"[^>]*>(.*?)</a>',lambda m:f'<abbr title="{m.group(1)}" style="text-decoration:none;">{m.group(2)}</abbr>',h)
            def ev(e):
                txt=agt(e['det'] if e['long'] else e['t'])
                head=f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td style="font:600 13px/20px {SANS};color:{ACC};">{e["lab"]}</td><td align="right" style="font:400 10px/14px {SANS};"><span style="background:transparent;border:1px solid #b5a37c;color:#7d6c47;font-weight:400;padding:1px 9px;border-radius:10px;letter-spacing:.05em;text-transform:uppercase;white-space:nowrap;">{e["th"]}</span></td></tr></table>'
                sid=None
                if e['sum']:
                    sid=syn_html(e['sum'],[('Page de référence',e['u'])],'Agenda')
                if web: ITEMS.append({'sid':sid,'sec':'Agenda','kind':'agenda','rappel':False,'date':e['date'],'label':e['lab'],'theme':e['th'],'themes':e['themes'],'segs':e['t'],'u':e['u'],'sum':e['sum'],'html':B._post(txt)})
                if web and e['sum']:
                    return f'<div class="sy-it sy-ev" data-syn="{sid}" style="margin:0 0 13px;">{head}<a href="#{sid}" data-syn="{sid}" style="display:block;font:14px/21px {SERIF};color:#1f2937;text-decoration:none;">{txt} {SYNB.format(sid).replace("<button","<span").replace("</button>","</span>")}</a></div>'
                return f'<div style="margin:0 0 13px;">{head}<a href="{e["u"]}" target="_blank" rel="noopener" style="display:block;font:14px/21px {SERIF};color:#1f2937;text-decoration:none;">{txt}</a></div>'
            cards=[]
            for (yr,mo),its in groups.items():
                cards.append(f'<div style="background:#f7f4ee;padding:14px 16px 4px;"><div style="font:600 12px/16px {SANS};letter-spacing:.14em;text-transform:uppercase;color:{NAVY};padding:0 0 10px;">{mo.capitalize()} {yr}</div>{"".join(ev(e) for e in its)}</div>')
            sp='<div style="height:14px;font-size:0;line-height:14px;">&nbsp;</div>'
            rows=f'<tr><td class="c" width="50%" valign="top" style="padding:0 7px 0 0;">{sp.join(cards[:cut])}</td><td class="c" width="50%" valign="top" style="padding:0 0 0 7px;">{sp.join(cards[cut:])}</td></tr>'
            body.append(f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 8px;">{rows}</table>');prev_h2=False
    flush()
    SEC=META['toc']
    toc=' <span style="color:#c3cad5;">·</span> '.join(f'<a href="#s{i}" style="color:#4b5563;text-decoration:none;border-bottom:1px solid #d5dbe5;">{E(s)}</a>' for i,s in enumerate(SEC))
    tocb=f'<p style="margin:0 0 4px;font:13px/24px {SANS};color:#6b7280;"><b style="font-weight:600;color:#4b5563;">Dans ce numéro</b>&nbsp; {toc}</p>'
    out=B._post(''.join(body).replace('@@TOC@@',tocb))
    import re as _re
    mins=max(1,round(len(_re.sub(r'<[^>]+>',' ',out).split())/220))
    css=''
    if web:
        css=f'''a.t{{border-bottom:1px dotted #1f4e8c;color:#1f4e8c;text-decoration:none;position:relative;cursor:help}}
a.t:hover::after,a.t:focus::after{{content:attr(data-tip);position:absolute;left:0;top:1.7em;z-index:9;width:290px;background:#0f2a4a;color:#fff;font:400 13px/1.45 {SANS};padding:9px 11px;border-radius:6px;box-shadow:0 4px 14px rgba(0,0,0,.25)}}
a.s{{color:#6b7280;font:14px {SANS};text-decoration:none;border-bottom:1px dotted #9ca3af}}
a.s.so{{color:#454e5c;font-weight:600;border-bottom:1px solid #9aa1ab}}
td[style*='font:14px/20px'] a.s{{font-size:12px}}
.sy-it{{cursor:pointer;transition:background .15s}}
.sy-it:hover{{background:#faf7f0}}
.sy-b{{display:inline-block;position:relative;width:20px;height:20px;margin:0 0 0 5px;padding:0;border:0;background:none;vertical-align:-4px;cursor:pointer}}
.sy-p{{position:absolute;left:0;top:0;z-index:1;display:flex;align-items:center;box-sizing:border-box;height:20px;min-width:20px;padding:0 3px;border:1px solid #e1c6b4;border-radius:10px;background:#fff;color:{ACC};white-space:nowrap;transition:left .18s ease,background .15s,color .15s,border-color .15s}}
.sy-p svg{{flex:none;display:block}}
.sy-l{{display:inline-block;max-width:0;overflow:hidden;opacity:0;font:600 11px/18px {SANS};letter-spacing:.02em;transition:max-width .18s ease,opacity .15s,margin .18s,padding .18s}}
.sy-b:hover .sy-p,.sy-b:focus-visible .sy-p{{z-index:5;background:{ACC};border-color:{ACC};color:#fff;box-shadow:0 2px 8px rgba(15,42,74,.18)}}
.sy-b:hover .sy-l,.sy-b:focus-visible .sy-l{{max-width:9em;opacity:1;margin-left:4px;padding-right:6px}}
.sy-b:focus-visible{{outline:none}}
.pod{{width:80%;margin:0 auto 28px;background:#f7f4ee;border:1px solid #e3d6c3;border-radius:22px;overflow:hidden}}
.pod-h{{display:flex;align-items:center;gap:10px;width:100%;padding:10px 18px;border:0;background:none;color:{NAVY};font:600 14px/22px {SANS};text-align:left;cursor:pointer}}
.pod-h:hover,.pod-h:focus-visible{{background:#f1ebdf;outline:none}}
.pod-i{{display:inline-flex;align-items:center;justify-content:center;width:24px;height:24px;border-radius:50%;background:{ACC};color:#fff;flex:none}}
.pod-i svg{{margin-left:2px}}
.pod-l{{flex:1}}
.pod-d{{font:400 13px/22px {SANS};color:#6b7280;white-space:nowrap}}
.pod-b{{max-height:0;overflow:hidden;transition:max-height .28s ease}}
.pod-in{{padding:4px 22px 16px;border-top:1px solid #e3d6c3}}
.pod-eb{{margin:12px 0 2px;font:600 12px/16px {SANS};letter-spacing:.16em;text-transform:uppercase;color:{ACC}}}
.pod-t{{margin:0 0 12px;font:600 16px/23px {SANS};color:{NAVY};text-wrap:balance}}
.pod-p{{display:flex;align-items:center;gap:12px}}
.pod-pl{{display:inline-flex;align-items:center;justify-content:center;flex:none;width:38px;height:38px;border:0;border-radius:50%;background:{NAVY};color:#fff;cursor:pointer}}
.pod-pl:hover,.pod-pl:focus-visible{{background:{ACC};outline:none}}
.pod-pl svg{{width:14px;height:14px}}
.pod-r{{--p:0%;flex:1;min-width:0;height:4px;margin:0;border-radius:2px;background:linear-gradient(to right,{ACC} var(--p),#dccfb9 var(--p));-webkit-appearance:none;appearance:none;cursor:pointer}}
.pod-r::-webkit-slider-thumb{{-webkit-appearance:none;width:14px;height:14px;border-radius:50%;background:{ACC};border:2px solid #fff;box-shadow:0 0 0 1px {ACC}}}
.pod-r::-moz-range-thumb{{width:12px;height:12px;border-radius:50%;background:{ACC};border:2px solid #fff}}
.pod-tm{{font:12px/16px {SANS};color:#6b7280;white-space:nowrap;font-variant-numeric:tabular-nums}}
.pod-n{{margin:12px 0 0;font:italic 13px/19px {SERIF};color:#6b7280}}
@media(max-width:660px){{.pod{{width:100%}}}}
dialog.sy{{width:min(640px,calc(100vw - 32px));max-height:min(86vh,900px);padding:0;border:0;border-top:6px solid {ACC};background:#fff;color:#1f2937;box-shadow:0 18px 50px rgba(15,42,74,.28)}}
dialog.sy::backdrop{{background:rgba(15,42,74,.42);backdrop-filter:blur(2px)}}
.sy-w{{padding:26px 34px 28px;overflow:auto;max-height:calc(min(86vh,900px) - 6px);box-sizing:border-box}}
.sy-x{{position:absolute;top:12px;right:14px;width:32px;height:32px;border:0;background:transparent;color:#6b7280;font:22px/32px {SANS};cursor:pointer}}
.sy-x:hover,.sy-x:focus-visible{{color:{NAVY};outline:2px solid #d5dbe5}}
.sy-w p.sy-eb{{margin:0 0 6px;font:600 11px/16px {SANS};letter-spacing:.14em;text-transform:uppercase;color:{ACC}}}
.sy-t{{margin:0 36px 14px 0;font:600 21px/28px {SANS};color:{NAVY};text-wrap:balance}}
.sy-m{{display:grid;grid-template-columns:max-content 1fr;gap:4px 16px;margin:0 0 16px;padding:10px 14px;background:#f7f4ee;font:13px/19px {SANS};color:#374151}}
.sy-m dt{{color:#7d6c47;font-weight:600}}
.sy-m dd{{margin:0;min-width:0}}
.sy-w h4{{margin:16px 0 5px;font:700 11.5px/16px {SANS};letter-spacing:.12em;text-transform:uppercase;color:#7d6c47}}
.sy-w{{overflow-x:hidden}}
.sy-w a.t:hover::after,.sy-w a.t:focus::after{{width:min(290px,60vw)}}
.sy-w a.t.r:hover::after,.sy-w a.t.r:focus::after{{left:auto;right:0}}
.sy-w p,.sy-v li{{margin:0 0 8px;font:15px/21px {SERIF}}}
.sy-v{{margin:0;padding-left:18px}}
.sy-v li{{margin:0 0 2px;padding-left:2px;line-height:20px}}
.sy-v li::marker{{color:#dba98f;content:'■  ';font-size:9px}}
.sy-w p.sy-s{{margin-top:18px!important;padding-top:12px;border-top:1px solid #e5e7eb}}
.sy-s a{{margin-right:10px;color:#6b7280;font:13px {SANS};text-decoration:none;border-bottom:1px dotted #9ca3af}}
@media (prefers-reduced-motion:no-preference){{dialog.sy[open]{{animation:syin .18s ease-out}}@keyframes syin{{from{{opacity:0;transform:translateY(8px)}}to{{opacity:1;transform:none}}}}}}
@media(max-width:660px){{.sy-w{{padding:22px 18px 22px}}.sy-m{{grid-template-columns:1fr;gap:0}}.sy-m dd{{margin-bottom:6px}}}}'''
    return f'''<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light">{'<meta name="robots" content="noindex">' if web else ''}<title>{esc(title)}</title><style>{css}@media(max-width:660px){{.w{{padding:22px 18px 28px!important}}td.c{{display:block!important;width:100%!important;padding:0 0 12px!important;box-sizing:border-box}}td.c2{{display:block!important;width:100%!important;padding:0!important}}}}</style></head>
<body style="margin:0;background:#ecebe6;">{'<div style="background:#0f2a4a;color:#fff;font:13px/20px '+SANS+';text-align:center;padding:8px 16px;">Édition de démonstration : contenu de l’édition de référence, avec des synthèses d’exemple.</div>' if web and META.get('demo') else ''}<span style="display:none;max-height:0;overflow:hidden;">La revue de la semaine : conformité logicielle des produits, export et sanctions, licences.</span>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#ecebe6;"><tr><td align="center" style="padding:24px 8px;">
<table role="presentation" width="720" cellpadding="0" cellspacing="0" style="width:100%;max-width:720px;background:#fff;{('background-image:url('+EN_TETE+');background-repeat:no-repeat;background-position:0 6px;background-size:100% auto;') if (web and EN_TETE) else ''}">
<tr><td style="height:6px;background:{ACC};font-size:0;line-height:6px;">&nbsp;</td></tr>
<tr><td class="w hd" style="padding:38px 52px 0;"><div style="font:600 12px/16px {SANS};letter-spacing:.16em;text-transform:uppercase;color:{ACC};">Revue de presse hebdomadaire</div><div style="font:700 46px/52px {SERIF};color:{NAVY};margin:8px 0 14px;letter-spacing:-.01em;"><i style="font-weight:400;color:{ACC};">Software</i> <span style="font:500 44px/52px {SANS};color:{NAVY};letter-spacing:-.025em;">Compliance</span></div><table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-bottom:2px solid {NAVY};"><tr><td style="padding:0 0 14px;font:13px/20px {SANS};color:#6b7280;">N°&nbsp;{META['n']} &nbsp;·&nbsp; {META['date_long'].replace(' ','&nbsp;')} &nbsp;·&nbsp; <a href="{SITE if not web else ''}/archives/" style="color:#6b7280;">Archives</a> &nbsp;·&nbsp; <a href="{SITE if not web else ''}/dossiers/" style="color:#6b7280;">Dossiers</a></td><td align="right" valign="top" style="padding:0 0 14px 12px;font:13px/20px {SANS};color:#6b7280;white-space:nowrap;"><span style="background:rgba(255,255,255,.5);border-radius:3px;padding:1px 4px;margin-right:-4px;">Lecture ≈&nbsp;{mins}&nbsp;min</span></td></tr></table></td></tr>
<tr><td class="w" style="padding:30px 52px 40px;">{bloc_podcast(web,DISO,ED_URL)}{out}
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:44px 0 0;border-top:2px solid {NAVY};"><tr><td style="padding:16px 0 0;font:12px/19px {SANS};color:#6b7280;">Ce document a été rédigé par une intelligence artificielle ({esc(META.get('redaction') or REDACTION_DEFAUT)}). Des erreurs sont possibles.</td></tr></table>
</td></tr></table></td></tr></table>{''.join(syns)+JS+PILL_JS if web and syns else ''}{POD_JS if web and EP else ''}</body></html>''',len(used)
def compact_email(h):
    """Allège l'e-mail : chaque style répété (4 fois ou plus) passe dans une classe déclarée dans <head>.
    Couleur et marges restent en ligne, pour les clients qui ignorent les styles de <head>."""
    from collections import Counter
    st=Counter(re.findall(r' style="([^"]{40,})"',h))
    rep_=[x for x,c in st.items() if c>=4]
    css=[]
    for k,x in enumerate(sorted(rep_,key=lambda x:-st[x]*len(x))):
        cl=f'k{k}'
        keep=';'.join(d for d in x.split(';') if d.strip().startswith(('color:','padding')))
        css.append(f'.{cl}{{{x}}}')
        h=h.replace(f' style="{x}"',f' class="{cl}"'+(f' style="{keep}"' if keep else ''))
    return h.replace('<style>','<style>'+''.join(css),1)
IGNORE_SIGLES={'UE','IA','AI','I','II','III','IV','V','VI','VII','VIII','IX','X','T1','T2','T3','T4'}
def sigles_sans_definition():
    """sigles présents dans la partie publiée mais absents du glossaire"""
    txt=[]
    for x in blocks:
        if x['k']=='h2' and ''.join(s_['t'] for s_ in x['i']).startswith(('Audit','Sources')): break
        if x['k'] in('p','h1','h2'): segs=x['i']
        elif x['k']=='ul': segs=[s_ for it in x['items'] for s_ in it]
        elif x['k']=='table': segs=[s_ for r in x['rows'] for c in r for s_ in c]
        else: segs=[]
        txt.append(' '.join(s_['t'] for s_ in segs if not s_.get('href')))
        if x['k']=='table': txt+= [d for d in (x.get('detail') or []) if d]
    T_=' '.join(txt).replace('\u00a0',' ')
    cov=[]
    for g in G:
        for m in re.finditer(r'(?<![\w-])('+g[0].replace(' ','[ \u00a0]')+r')(?![\w])',T_): cov.append(m.span())
    miss=set()
    for m in re.finditer(r'(?<![\w-])([A-Z][A-Z0-9]+(?:[-/][A-Z0-9]+)*)(?![\w])',T_):
        if m.group(1) in IGNORE_SIGLES: continue
        if any(a<=m.start() and m.end()<=b_ for a,b_ in cov): continue
        pos=m.start()
        for part in m.group(1).split('/'):
            if part not in IGNORE_SIGLES and not any(a<=pos and pos+len(part)<=b_ for a,b_ in cov): miss.add(part)
            pos+=len(part)+1
    return sorted(miss)
if __name__=='__main__':
    _m=sigles_sans_definition()
    if _m: print('ATTENTION sigles sans définition dans glossary.py : '+', '.join(_m),file=sys.stderr)
    OUT=sys.argv[1] if len(sys.argv)>1 else '.'
    os.makedirs(OUT,exist_ok=True)
    for web,name in((False,'revue-email.html'),(True,'revue-web.html')):
        h,n=render(web)
        if not web: h=compact_email(h)
        if not web and len(h.encode())>97000:
            NO_EL=True; h,n=render(web); h=compact_email(h); NO_EL=False
            print('Note : e-mail trop lourd, liens « En savoir plus » par élément retirés (lien général conservé)',file=sys.stderr)
        open(os.path.join(OUT,name),'w').write(h);print(name,len(h.encode()),n,'octets/termes')
    json.dump(ITEMS,open(os.path.join(OUT,'items.json'),'w'),ensure_ascii=False)
