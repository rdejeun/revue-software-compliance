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
def ecoute(web,ed_url):
    """Lien « Écouter » dans l'en-tête : vers le lecteur de la page web (e-mail) ou l'ancre locale (web)."""
    if not EP: return ''
    m=max(1,round(EP['duree_s']/60)); href='#ecouter' if web else (ed_url+'#ecouter' if ed_url else '')
    if not href: return ''
    return f' &nbsp;·&nbsp; <a href="{href}" style="color:{ACC};font-weight:600;text-decoration:none;">Écouter l’épisode ({m}&nbsp;min)&nbsp;▶</a>'
def lecteur(diso):
    """Lecteur audio et transcription, en tête de la version web."""
    if not EP or not diso: return ''
    m=max(1,round(EP['duree_s']/60))
    noms={k:v['nom'] for k,v in (EP.get('voix') or {}).items()}
    tr=''.join(f'<p style="margin:0 0 8px;"><b style="font:600 13px {SANS};color:{NAVY};">{esc(noms.get(r["v"],r["v"]))}</b> — {esc(typo(r["t"]))}</p>' for r in (POD or {}).get('repliques',[]))
    trans=f'<details style="margin-top:10px;"><summary style="cursor:pointer;font:600 13px/20px {SANS};color:#4b5563;">Lire la transcription</summary><div style="margin-top:10px;font:15px/22px {SERIF};color:#1f2937;">{tr}</div></details>' if tr else ''
    return (f'<div id="ecouter" style="margin:0 0 26px;padding:16px 18px;background:#f7f4ee;border-left:4px solid {ACC};">'
            f'<div style="font:600 12px/16px {SANS};letter-spacing:.14em;text-transform:uppercase;color:{ACC};">L’épisode audio · {m}&nbsp;min</div>'
            f'<div style="margin:4px 0 10px;font:600 17px/24px {SANS};color:{NAVY};">{esc(typo((POD or {}).get("titre","")))}</div>'
            f'<audio controls preload="none" src="/{diso}/episode.mp3" style="width:100%;"></audio>'
            f'<div style="margin-top:6px;font:12px/18px {SANS};color:#6b7280;">Dialogue à deux voix de synthèse, écrit à partir de cette édition · <a href="/{diso}/episode.mp3" download style="color:#6b7280;">Télécharger le MP3</a> · <a href="/podcast.xml" style="color:#6b7280;">S’abonner (RSS)</a></div>'
            f'{trans}</div>')
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
    SYNB='<button type="button" class="sy-b" data-syn="{0}" aria-haspopup="dialog" title="Afficher la synthèse"><svg viewBox="0 0 16 16" width="13" height="13" aria-hidden="true"><circle cx="8" cy="8" r="7" fill="none" stroke="currentColor" stroke-width="1.4"/><path d="M8 4.6v6.8M4.6 8h6.8" stroke="currentColor" stroke-width="1.4"/></svg>En savoir plus</button>'

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
    ESS=[(a,b,'#s%d'%k) for a,b,k in META['ess']]
    rows=''.join(f'<tr><td width="104" align="center" valign="top" style="padding:11px 0;border-top:1px solid #e3ddd0;font:400 26px/30px {SERIF};color:{ACC};white-space:nowrap;">{a}</td><td valign="top" style="padding:13px 0 11px 8px;border-top:1px solid #e3ddd0;font:15px/23px {SERIF};color:#1f2937;"><a href="{h}" style="color:#1f2937;text-decoration:none;">{b}</a></td></tr>' for a,b,h in ESS)
    ess=f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:26px 0 20px;background:#f7f4ee;background-image:linear-gradient(45deg,#f4efe4 0%,#faf8f3 100%);border:3px dotted #c4b28a;"><tr><td style="padding:18px 22px 10px;"><table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td colspan="2" style="padding:0 0 8px;font:600 12px/16px {SANS};letter-spacing:.14em;text-transform:uppercase;color:{ACC};">L’essentiel en 60 secondes</td></tr>{rows}</table></td></tr></table>'
    out=B._post(''.join(body).replace('@@TOC@@',ess+tocb))
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
.sy-b{{display:inline-block;box-sizing:border-box;height:20px;margin:0 0 0 4px;padding:0 9px 0 6px;border:1px solid #e1c6b4;border-radius:10px;background:#fff;color:{ACC};font:600 11px/18px {SANS};letter-spacing:.02em;vertical-align:1px;cursor:pointer;white-space:nowrap}}
.sy-b svg{{display:inline-block;vertical-align:-2px;margin-right:4px}}
.sy-b:hover,.sy-b:focus-visible{{background:{ACC};border-color:{ACC};color:#fff;outline:none}}
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
<body style="margin:0;background:#ecebe6;">{'<div style="background:#0f2a4a;color:#fff;font:13px/20px '+SANS+';text-align:center;padding:8px 16px;">Édition de démonstration : contenu de l’édition de référence, avec des synthèses d’exemple.</div>' if web and META.get('demo') else ''}<span style="display:none;max-height:0;overflow:hidden;">Les points clés de la semaine en 60 secondes, puis le détail.</span>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#ecebe6;"><tr><td align="center" style="padding:24px 8px;">
<table role="presentation" width="720" cellpadding="0" cellspacing="0" style="width:100%;max-width:720px;background:#fff;">
<tr><td style="height:6px;background:{ACC};font-size:0;line-height:6px;">&nbsp;</td></tr>
<tr><td class="w" style="padding:38px 52px 0;"><div style="font:600 12px/16px {SANS};letter-spacing:.16em;text-transform:uppercase;color:{ACC};">Revue de presse hebdomadaire</div><div style="font:700 46px/52px {SERIF};color:{NAVY};margin:8px 0 14px;letter-spacing:-.01em;"><i style="font-weight:400;color:{ACC};">Software</i> <span style="font:500 44px/52px {SANS};color:{NAVY};letter-spacing:-.025em;">Compliance</span></div><div style="font:13px/20px {SANS};color:#6b7280;padding-bottom:14px;border-bottom:2px solid {NAVY};">N°&nbsp;{META['n']} &nbsp;·&nbsp; {META['date_long'].replace(' ','&nbsp;')} &nbsp;·&nbsp; Lecture ≈&nbsp;{mins}&nbsp;min{ecoute(web,ED_URL)}{(' &nbsp;·&nbsp; <a href="/archives/" style="color:#6b7280;">Archives</a> &nbsp;·&nbsp; <a href="/dossiers/" style="color:#6b7280;">Dossiers</a>' if web else (f' &nbsp;·&nbsp; <a href="{ED_URL}" style="color:{ACC};font-weight:600;text-decoration:none;">Lire la version enrichie&nbsp;↗</a>' if ED_URL else ''))}</div></td></tr>
<tr><td class="w" style="padding:30px 52px 40px;">{lecteur(DISO) if web else ''}{out}
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:44px 0 0;border-top:2px solid {NAVY};"><tr><td style="padding:16px 0 0;font:12px/19px {SANS};color:#6b7280;"><b style="font-weight:600;color:#4b5563;">Comment lire cette revue.</b> Chaque nom ou sigle est expliqué à sa première occurrence (survol, avec lien vers la page officielle). Les informations qui n’ont pas pu être recoupées sont écartées. Dernière mise à jour : {META['date'].replace(' ','&nbsp;')}.</td></tr></table>
</td></tr></table></td></tr></table>{''.join(syns)+JS if web and syns else ''}</body></html>''',len(used)
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
