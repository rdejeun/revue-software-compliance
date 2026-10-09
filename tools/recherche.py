"""Recherche dans les éditions : index (docs.json) construit à la publication, recherche dans le navigateur (MiniSearch).
Aucune donnée n'est envoyée : la requête ne quitte pas le navigateur. Page : /recherche/ (README, § 17)."""
import hashlib, json, os, re, shutil

TOOLS = os.path.dirname(os.path.abspath(__file__))
MINISEARCH_SHA256 = 'e66b5b61b7a48fa87c18f38802a96520cc37a766a2e08089ef906a6f018ea432'
SUIVI_MATOMO = False   # True : chaque recherche est comptée dans Matomo (« Recherches sur le site ») ; décision du propriétaire (vie privée)
# synonymes ajoutés à la main (en plus des sigles du glossaire) : (terme, équivalent)
SYNONYMES = [('SBOM', 'nomenclature logicielle'), ('SBOM', 'nomenclature des logiciels'), ('supply chain', 'chaîne d’approvisionnement'),
             ('SCA', 'analyse de composition logicielle'), ('dual-use', 'double usage'), ('IA', 'intelligence artificielle'),
             ('export', 'exportation'), ('open source', 'logiciel libre'), ('CVE', 'vulnérabilité')]


def texte(segs):
    t = ''.join(s.get('t', '') for s in (segs or []))
    t = re.sub(r'\*\{[a-z]{2,3}\}|\*|==', '', t)
    return re.sub(r'\s+', ' ', t.replace(' ', ' ')).strip()


def synonymes(G):
    paires = [list(p) for p in SYNONYMES]
    for g in G:
        sigle, libelle = g[0], g[1]
        if re.fullmatch(r'[A-Za-z0-9]{2,10}', sigle) and libelle.lower() != sigle.lower() and len(libelle) > len(sigle) + 3 and ' ' in libelle:
            paires.append([sigle, libelle])
    vus = set(); out = []
    for a, b in paires:
        if (a.lower(), b.lower()) not in vus: vus.add((a.lower(), b.lower())); out.append([a, b])
    return out


def construire(infos, themes, G):
    editions, secs, docs = [], [], []
    for i in infos:
        if i['meta'].get('demo'): continue
        d = i['d']
        editions.append({'d': d, 'n': i['meta']['n'], 'date': i['meta'].get('date_long') or i['meta'].get('date') or d})
        for it in i['items']:
            sm = it.get('sum') or {}
            sec = re.split(r' : ', it.get('sec') or '')[0].strip()
            if sec not in secs: secs.append(sec)
            acc = texte(it.get('segs'))
            syn = ' '.join(filter(None, [sm.get('statut', ''), sm.get('essentiel', ''), sm.get('contexte', ''), sm.get('impact_avere', ''), sm.get('impact_potentiel', ''),
                                         ' '.join(sm.get('a_verifier') or [])]))
            syn = texte([{'t': syn}])
            if it.get('kind') == 'agenda' and it.get('label'): acc = f"{it.get('date') or it['label']} : {acc}"
            titre = texte([{'t': sm.get('titre', '')}]) or acc[:90]
            docs.append({'e': d, 's': it['sid'], 'r': secs.index(sec), 't': titre, 'a': acc, 'y': syn, 'h': it.get('themes') or [], 'p': 1 if it.get('rappel') else 0})
    return {'editions': editions, 'secs': secs, 'themes': {k: [v['court'], v.get('recherche') or v['court']] for k, v in themes.items() if any(k in x['h'] for x in docs)},
            'syn': synonymes(G), 'docs': docs}


JS = r'''(function(){
var D=null,MS=null,champ=document.getElementById('q'),selD=document.getElementById('f-d'),selE=document.getElementById('f-e'),res=document.getElementById('res'),cpt=document.getElementById('cpt');
var MIN=3;   /* pas de résultat sous 3 caractères (lettres et chiffres, hors opérateurs et espaces) */
var STOP=new Set('a à au aux avec ce ces cet cette d dans de des du elle elles en est et il ils j l la le les leur leurs ne ni nous on ou par pas plus pour qu que qui s sa se ses si son sont sur un une vous y'.split(' '));
function pli(c){var f=c.normalize('NFD').replace(/[̀-ͯ]/g,'').toLowerCase();return f.length===1?f:c.toLowerCase().slice(0,1)}
function plier(s){var o='';for(var i=0;i<s.length;i++)o+=pli(s[i]);return o}   /* même longueur que s : pour surligner dans le texte d'origine */
function jetons(s){return s.split(/[^\p{L}\p{N}]+/u).filter(Boolean)}
function terme(t){t=plier(t);if(STOP.has(t))return null;if(t.length>3)t=t.replace(/aux$/,'al').replace(/[sx]$/,'');return t}
function esc(s){return s.replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
function charger(){if(D)return Promise.resolve();return fetch('/recherche/docs.json').then(function(r){return r.json()}).then(function(j){D=j;
 MS=new MiniSearch({fields:['t','a','y'],storeFields:[],idField:'id',tokenize:jetons,processTerm:terme,searchOptions:{boost:{t:3,a:2},prefix:true,fuzzy:function(t){return t.length>5?0.15:0}}});
 D.docs.forEach(function(d,i){d.id=i});MS.addAll(D.docs);
 D.themes&&Object.keys(D.themes).forEach(function(k){var o=document.createElement('option');o.value=k;selD.appendChild(o)});libelles();if(window.matchMedia)matchMedia('(min-width:661px)').addEventListener('change',libelles);
 if(D.editions.length>1){D.editions.slice().reverse().forEach(function(e){var o=document.createElement('option');o.value=e.d;o.textContent='N° '+e.n+' · '+e.date;selE.appendChild(o)})}else selE.parentNode.hidden=true})}
function libelles(){var long=window.matchMedia&&matchMedia('(min-width:661px)').matches;[].forEach.call(selD.options,function(o){if(o.value&&D.themes[o.value])o.textContent=D.themes[o.value][long?1:0]})}   /* intitulés longs quand la place le permet */
function variantes(q){var f=plier(q),v=[q];D.syn.forEach(function(p){var a=plier(p[0]),b=plier(p[1]);
 var ra=new RegExp('(^|[^\\p{L}\\p{N}])'+a.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+'(?=$|[^\\p{L}\\p{N}])','u'),rb=new RegExp('(^|[^\\p{L}\\p{N}])'+b.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+'(?=$|[^\\p{L}\\p{N}])','u');
 if(ra.test(f))v.push(f.replace(ra,'$1'+b));else if(rb.test(f))v.push(f.replace(rb,'$1'+a))});return v}
function filtre(r){var d=D.docs[r.id];return(!selD.value||d.h.indexOf(selD.value)>=0)&&(!selE.value||d.e===selE.value)}
function classer(m){var ids=Object.keys(m).map(Number);ids.sort(function(a,b){return m[b]-m[a]||(D.docs[b].e>D.docs[a].e?1:-1)});return ids}
function chercher(q){var m={};variantes(q).forEach(function(v,k){[['AND',1],['OR',.35]].forEach(function(c){if(k&&c[0]==='OR')return;MS.search(v,{combineWith:c[0],filter:filtre}).forEach(function(r){var s=r.score*c[1]*(k?.45:1);if(!(r.id in m)||m[r.id]<s)m[r.id]=s})})});return m}
/* syntaxe : "phrase exacte" ; +mot (obligatoire, AND) ; -mot (exclu, AND_NOT) ; -"phrase" exclue ; les autres mots : tous d'abord, puis l'un d'eux */
function analyser(q){var o={R:[],P:[],X:[],PH:[],XPH:[]},re=/([+-]?)"([^"]*)"|([+-]?)([^\s"]+)/g,m;
 while((m=re.exec(q))){var s=m[1]||m[3]||'',ph=m[2]!==undefined,t=ph?m[2]:m[4];
  if(ph){var tk=jetons(t).map(plier);if(tk.length)(s==='-'?o.XPH:o.PH).push(tk)}
  else if(jetons(t).length)(s==='-'?o.X:s==='+'?o.R:o.P).push(t)}
 return o}
function ensemble(mot){var s={};MS.search(mot,{prefix:true,fuzzy:false,combineWith:'AND'}).forEach(function(r){s[r.id]=1});return s}
function avecPhrase(d,tk){if(!d._f)d._f=' '+jetons(d.t+' '+d.a+' '+d.y).map(plier).join(' ')+' ';return d._f.indexOf(' '+tk.join(' ')+' ')>=0}
function recherche(q){var a=analyser(q),pos=a.R.concat(a.P).concat(a.PH.map(function(t){return t.join(' ')})).join(' ').trim(),m;
 if(!pos&&!a.X.length&&!a.XPH.length)return{ids:[],tt:[]};
 if(pos)m=chercher(pos);else{m={};MS.search(MiniSearch.wildcard,{filter:filtre}).forEach(function(r){m[r.id]=1})}
 var ids=classer(m);
 a.R.forEach(function(w){var s=ensemble(w);ids=ids.filter(function(i){return s[i]})});
 a.PH.forEach(function(tk){ids=ids.filter(function(i){return avecPhrase(D.docs[i],tk)})});
 a.X.forEach(function(w){var s=ensemble(w);ids=ids.filter(function(i){return !s[i]})});
 a.XPH.forEach(function(tk){ids=ids.filter(function(i){return !avecPhrase(D.docs[i],tk)})});
 return{ids:ids,tt:jetons(pos).map(terme).filter(Boolean)}}
function extrait(d,tt){var t=d.a+' '+d.y,f=plier(t),pos=-1;for(var i=0;i<tt.length&&pos<0;i++){var p=f.search(new RegExp('(^|[^\\p{L}\\p{N}])'+tt[i].replace(/[.*+?^${}()|[\]\\]/g,'\\$&'),'u'));if(p>=0)pos=p}
 var deb=Math.max(0,pos-70);if(pos<0)deb=0;var s=t.slice(deb,deb+230);return(deb>0?'… ':'')+surligne(s,tt)+(deb+230<t.length?' …':'')}
function surligne(s,tt){var f=plier(s),out='',i=0,re=tt.length?new RegExp('(^|[^\\p{L}\\p{N}])('+tt.map(function(x){return x.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')}).join('|')+')[\\p{L}\\p{N}]*','gu'):null;
 if(!re)return esc(s);var m;while((m=re.exec(f))){var a=m.index+m[1].length,b=m.index+m[0].length;out+=esc(s.slice(i,a))+'<mark>'+esc(s.slice(a,b))+'</mark>';i=b}return out+esc(s.slice(i))}
function afficher(q,ids,tt){var h='',n=ids.length;cpt.textContent=q?(n?n+' résultat'+(n>1?'s':''):'Aucun résultat'):'';
 ids.slice(0,60).forEach(function(i){var d=D.docs[i],e=D.editions.filter(function(x){return x.d===d.e})[0];
  h+='<li><a class="rs" href="/'+d.e+'/#'+d.s+'"><span class="rm">'+esc(D.secs[d.r])+' · N° '+e.n+(d.p?' · rappel':'')+'</span><span class="rt">'+surligne(d.t,tt)+'</span><span class="rx">'+extrait(d,tt)+'</span></a></li>'});
 res.innerHTML=h+(n>60?'<li class="rm">Affinez la recherche : '+(n-60)+' autres résultats.</li>':'')}
var tempo;function lancer(maj){var q=champ.value.trim();return charger().then(function(){
 if(!q||jetons(q).join('').length<MIN){res.innerHTML='';cpt.textContent=q?'Saisissez au moins '+MIN+' caractères.':''}else{var rr=recherche(q);afficher(q,rr.ids,rr.tt)}
 if(maj!==false){var u=new URLSearchParams();if(q)u.set('q',q);if(selD.value)u.set('d',selD.value);if(selE.value)u.set('e',selE.value);history.replaceState(null,'',u.toString()?'?'+u:location.pathname)}
 /*SUIVI*/})}
champ.addEventListener('input',function(){clearTimeout(tempo);tempo=setTimeout(lancer,120)});selD.addEventListener('change',lancer);selE.addEventListener('change',lancer);
document.getElementById('rech').addEventListener('submit',function(e){e.preventDefault();clearTimeout(tempo);lancer().then(function(){var a=res.querySelector('a.rs');if(a){champ.blur();a.focus()}})});   /* Entrée : le focus passe au premier résultat */
var p=new URLSearchParams(location.search);champ.value=p.get('q')||'';
charger().then(function(){if(p.get('d'))selD.value=p.get('d');if(p.get('e'))selE.value=p.get('e');lancer(false)});
/* flèches : du champ au premier résultat, d'un résultat à l'autre, retour au champ (Échap ou flèche haut depuis le premier) */
function liens(){return[].slice.call(res.querySelectorAll('a.rs'))}
function allerA(a){if(a){champ.blur();a.focus()}}
champ.addEventListener('keydown',function(e){if(e.key==='ArrowDown'&&!e.altKey&&!e.ctrlKey&&!e.metaKey&&!e.shiftKey){var l=liens();if(l.length){e.preventDefault();allerA(l[0])}}});
res.addEventListener('keydown',function(e){var a=e.target.closest&&e.target.closest('a.rs');if(!a||e.altKey||e.ctrlKey||e.metaKey||e.shiftKey)return;var l=liens(),i=l.indexOf(a),k=e.key;
 if(k==='ArrowDown'){e.preventDefault();if(l[i+1])l[i+1].focus()}
 else if(k==='ArrowUp'){e.preventDefault();if(i>0)l[i-1].focus();else{champ.focus();champ.select()}}
 else if(k==='Home'){e.preventDefault();l[0].focus()}
 else if(k==='End'){e.preventDefault();l[l.length-1].focus()}
 else if(k==='Escape'){e.preventDefault();champ.focus();champ.select()}});
document.addEventListener('keydown',function(e){if(e.key!=='/'||e.ctrlKey||e.metaKey||e.altKey)return;var n=(e.target&&e.target.tagName)||'';if(n==='INPUT'||n==='TEXTAREA'||n==='SELECT')return;e.preventDefault();champ.focus();champ.select()});   /* « / » : saisir une recherche */
champ.focus()})();'''

CSS = '''<style>
.rch{margin:8px 0 0}
.rch form{display:flex;flex-wrap:wrap;gap:10px;align-items:flex-start;margin:0 0 6px}
.rch .fq{flex:1 1 300px}
.rch label{display:block;font:600 12px/16px 'Segoe UI',Arial,sans-serif;letter-spacing:.08em;text-transform:uppercase;color:#6b7280;margin:0 0 4px}
.rch input,.rch select{box-sizing:border-box;width:100%;height:44px;font:17px/24px Georgia,serif;color:#0f2a4a;background:#fff;border:1px solid #d9cdb8;border-radius:6px;padding:8px 12px}
.rch input:focus,.rch select:focus{outline:2px solid #c2410c;outline-offset:1px}
.ic{position:relative}
.ic .ico{position:absolute;left:12px;top:50%;transform:translateY(-50%);pointer-events:none;color:#c2410c}
.rch .ic input,.rch .ic select{padding-left:39px}
.rch .fs{flex:0 1 220px}
@media(min-width:661px){.rch .fs{flex-basis:250px}}
.rch .fs select{font-size:15px;line-height:22px;padding:9px 10px 9px 39px}
#aide{margin:5px 0 0;font:12px/18px 'Segoe UI',Arial,sans-serif;color:#8a8f98;white-space:nowrap;text-align:center}
@media(max-width:380px){#aide{white-space:normal}}
#aide b{font-weight:600;color:#6b7280}
#cpt{min-height:24px;font:13px/24px 'Segoe UI',Arial,sans-serif;color:#6b7280;margin:0 0 6px}
#res{list-style:none;margin:0;padding:0}
#res li{margin:0 0 10px}
a.rs{display:block;padding:12px 16px;border-radius:6px;background:#f7f4ee;color:inherit;text-decoration:none}
a.rs:hover,a.rs:focus-visible{background:#f1ebdf;outline:none}
.rm{display:block;font:12px/18px 'Segoe UI',Arial,sans-serif;letter-spacing:.04em;color:#6b7280}
.rt{display:block;font:600 18px/26px 'Segoe UI',Arial,sans-serif;color:#0f2a4a;margin:2px 0 4px}
.rx{display:block;font:16px/24px Georgia,serif;color:#374151}
mark{background:none;color:#9a3412;font-weight:700}
</style>'''


def ecrire(infos, themes, G, page, write, SITE, TOOLS_DIR):
    """Écrit /recherche/ (page et docs.json) et copie MiniSearch sous /assets/ (somme SHA-256 vérifiée)."""
    src = os.path.join(TOOLS_DIR, 'vendor', 'minisearch', 'minisearch.min.js')
    if hashlib.sha256(open(src, 'rb').read()).hexdigest() != MINISEARCH_SHA256: raise SystemExit('MiniSearch : somme SHA-256 inattendue (tools/vendor/minisearch)')
    os.makedirs(os.path.join(SITE, 'assets'), exist_ok=True)
    shutil.copyfile(src, os.path.join(SITE, 'assets', 'minisearch.min.js'))
    shutil.copyfile(os.path.join(TOOLS_DIR, 'vendor', 'minisearch', 'LICENSE'), os.path.join(SITE, 'assets', 'minisearch.LICENSE.txt'))
    data = construire(infos, themes, G)
    write(os.path.join(SITE, 'recherche', 'docs.json'), json.dumps(data, ensure_ascii=False, separators=(',', ':')))
    suivi = "if(q&&window._paq)window._paq.push(['trackSiteSearch',q,selD.value||false,D?recherche(q).ids.length:0]);" if SUIVI_MATOMO else ''
    corps = (CSS + '<div class="rch"><form id="rech" role="search" autocomplete="off"><div class="fq"><label for="q">Rechercher dans les articles</label>'
             '<div class="ic"><svg class="ico" viewBox="0 0 16 16" width="18" height="18" aria-hidden="true"><circle cx="6.8" cy="6.8" r="4.6" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M10.3 10.3 14 14" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg><input id="q" type="search" placeholder="CRA, SBOM, licence GPL, classement ECCN…" enterkeyhint="search" aria-describedby="aide"></div><p id="aide">Astuces : <b>"phrase exacte"</b> · <b>+mot</b> obligatoire · <b>-mot</b> exclu</p></div>'
             '<div class="fs"><label for="f-d">Limiter au dossier</label><div class="ic ic-d"><svg class="ico" viewBox="0 0 16 16" width="18" height="18" aria-hidden="true"><path d="M1.75 4.25a1 1 0 0 1 1-1h3.1l1.4 1.5h6a1 1 0 0 1 1 1v6.5a1 1 0 0 1-1 1h-10.5a1 1 0 0 1-1-1z" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/></svg><select id="f-d"><option value="">Tous</option></select></div></div>'
             '<div class="fs"><label for="f-e">Édition</label><select id="f-e"><option value="">Toutes</option></select></div></form>'
             '<div id="cpt" role="status" aria-live="polite"></div><ul id="res"></ul>'
             '<noscript><p>La recherche demande JavaScript. Vous pouvez parcourir les <a href="/archives/">archives</a> et les <a href="/dossiers/">dossiers</a>.</p></noscript></div>'
             '<script src="/assets/minisearch.min.js"></script><script>' + JS.replace('/*SUIVI*/', suivi) + '</script>')
    write(os.path.join(SITE, 'recherche', 'index.html'), page('Recherche – Software Compliance', 'Revue de presse hebdomadaire',
          '<i>Recherche</i> <span>dans la revue</span>', '<a href="/">Dernière édition</a> · <a href="/archives/">Archives</a> · <a href="/dossiers/">Dossiers</a>', corps, raccourci=False))   # « / » y met le focus dans le champ (script de la page)
    return len(data['docs'])
