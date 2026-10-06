"""Génère l'édition (e-mail et web) à partir de blocks.json et meta.json du dossier courant.
Usage : python3 gen.py DOSSIER_SORTIE   (écrit revue-email.html, revue-web.html, items.json)"""
import re,json,html
from urllib.parse import urlparse
import commun as B
from podcast import titre_episode
from pied import pied, pied_bloc, CSS_PIED, MATOMO
from commun import typo,E,esc,mark,blocks,G,used,seen,SANS,SERIF,NB
import sys,os
META=json.load(open('meta.json'))
# Épisode audio (tools/podcast.py) : présent seulement s'il a été produit pour cette édition
EP_FICHIER=next((f for f in ('episode.m4a','episode.mp3') if os.path.isfile(f)),None)   # M4A (AAC) ; MP3 pour les anciens épisodes
EP=json.load(open('episode.json')) if os.path.isfile('episode.json') and EP_FICHIER else None
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
SYNH={}    # contenu des fenêtres « En savoir plus », par sid (version web)
SYN_ASSETS={}   # styles, script et pastille de la fenêtre, pour les pages Dossiers
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
    if ':' not in t and 0<len(t.strip())<=90 and len(items)>1 and not items[1].get('href') and items[1]['t'].lstrip().startswith(':'):
        return [{'t':t.rstrip(),'b':1},{'t':' '+items[1]['t'].lstrip()}]+items[2:]   # « Lien avec le CRA » + « : … » en deux segments
    return items
JS=r'''<dialog class="sy" id="sy" aria-labelledby="sy-h"><button type="button" class="sy-x" aria-label="Fermer"><svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true"><path d="M3 3l10 10M13 3L3 13" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg></button><div class="sy-w" id="sy-c"></div></dialog>
<script>
(function(){
var dlg=document.getElementById('sy'),box=document.getElementById('sy-c');
/* Partager : lien mailto, objet = titre, corps = titre + lien vers la fenêtre dans la page datée de l'édition */
var SH='<a class="sy-sh" id="sy-sh" href="#" aria-label="Partager par e-mail"><svg viewBox="0 0 16 16" width="17" height="17" aria-hidden="true"><circle cx="12" cy="3.5" r="2" fill="currentColor"/><circle cx="4" cy="8" r="2" fill="currentColor"/><circle cx="12" cy="12.5" r="2" fill="currentColor"/><path d="M5.8 7l4.4-2.5M5.8 9l4.4 2.5" stroke="currentColor" stroke-width="1.4"/></svg>Partager</a>';
function partage(id){SEL.m='';SEL.fin=0;var l=box.querySelector('p.sy-s');if(!l){l=document.createElement('p');l.className='sy-s';box.appendChild(l)}l.insertAdjacentHTML('beforeend',SH);var a=document.getElementById('sy-sh');var t=(box.querySelector('.sy-t')||{}).textContent||document.title;
 var m=/^(\d{4}-\d{2}-\d{2})-(syn\d+)$/.exec(id),ed=m?m[1]:(dlg.getAttribute('data-ed')||''),s=m?m[2]:id;
 var base=location.origin+(ed?'/'+ed+'/':location.pathname)+'#'+s;
 function lien(q){a.href='mailto:?subject='+encodeURIComponent('📰 '+t)+'&body='+encodeURIComponent(t+'\n\n'+base+q)}
 lien('');
 /* passage sélectionné : le lien porte les numéros du premier et du dernier mot (#syn3.c-12, en hexadécimal), surlignés à l'ouverture.
    Le clic sur le bouton efface la sélection avant l'événement « click » : on la retient avant (mousedown sans
    effet par défaut ; mémoire de la dernière sélection pour les écrans tactiles). */
 a.addEventListener('mousedown',function(e){e.preventDefault()});
 a.addEventListener('click',function(){var x=selMots()||(Date.now()-SEL.fin<1500?SEL.m:'');lien(x?'.'+x:'')})}
/* mots de la fenêtre : suites de caractères sans espace dans le texte de la fenêtre (balises ignorées) */
function mots(){var S='',w=document.createTreeWalker(box,NodeFilter.SHOW_TEXT),n,N=[],B=null;
 while((n=w.nextNode())){var bl=n.parentNode.closest('p,h3,h4,li,dt,dd,div');if(B&&bl!==B)S+=' ';B=bl;N.push([n,S.length]);S+=n.nodeValue}   /* espace entre deux blocs */
 var W=[],re=/\S+/g,x;while((x=re.exec(S)))W.push([x.index,x.index+x[0].length]);return {S:S,N:N,W:W}}
/* position d'une borne de sélection dans le texte de mots() */
function pos(M,nd,off){if(nd.nodeType!==3){var c=nd.childNodes[off],w=document.createTreeWalker(box,NodeFilter.SHOW_TEXT),t,prev=null;
  while((t=w.nextNode())){if(c&&(c===t||c.contains(t)||(c.compareDocumentPosition(t)&4)))return pos(M,t,0);prev=t}
  return prev?pos(M,prev,prev.nodeValue.length):0}
 for(var k=0;k<M.N.length;k++)if(M.N[k][0]===nd)return M.N[k][1]+off;return 0}
function selMots(){var z=window.getSelection();if(!z||z.isCollapsed||!box.contains(z.anchorNode)||!box.contains(z.focusNode))return '';
 var r=z.getRangeAt(0),M=mots(),p=pos(M,r.startContainer,r.startOffset),q=pos(M,r.endContainer,r.endOffset),W=M.W,i,a=-1,b=-1;
 for(i=0;i<W.length;i++){if(a<0&&W[i][1]>p)a=i;if(W[i][0]<q)b=i}
 if(a<0||b<a)return '';return a===b?(a+1).toString(16):(a+1).toString(16)+'-'+(b+1).toString(16)}   /* numéros en hexadécimal */
var SEL={m:'',fin:0};
document.addEventListener('selectionchange',function(){var x=selMots();if(x){SEL.m=x;SEL.fin=Infinity}else if(SEL.fin===Infinity)SEL.fin=Date.now()});
/* surligne les mots a à b (numérotés à partir de 1) */
function surligne(a,b){var M=mots(),W=M.W;a=parseInt(a,16);b=parseInt(b||a.toString(16),16);if(!(a>=1&&b>=a&&b<=W.length))return;var d=W[a-1][0],f=W[b-1][1],g=[];
 for(var k=0;k<M.N.length;k++){var n=M.N[k][0],o=M.N[k][1],e=o+n.nodeValue.length,s0=Math.max(d,o),s1=Math.min(f,e);if(s1>s0)g.push([n,s0-o,s1-o])}
 for(var j=g.length-1;j>=0;j--){var r=document.createRange();r.setStart(g[j][0],g[j][1]);r.setEnd(g[j][0],g[j][2]);var mk=document.createElement('mark');mk.className='sy-hl';r.surroundContents(mk)}
 var h=box.querySelector('mark.sy-hl');if(h)requestAnimationFrame(function(){requestAnimationFrame(function(){h.scrollIntoView({block:'center'})})})}
/* chaque ouverture ajoute une entrée d'historique : le bouton Précédent (y compris celui de la souris) ferme la fenêtre */
var pushed=false,byPop=false;
/* mesure d'audience (Matomo, sans cookie) : catégorie « En savoir plus », nom = date de l'édition · titre de la synthèse */
function nomSy(id){var m=/^(\d{4}-\d{2}-\d{2})-syn\d+$/.exec(id||''),t=box.querySelector('.sy-t');return (m?m[1]:(dlg.getAttribute('data-ed')||''))+' · '+(t?t.textContent.trim():id)}
function evSy(act,nom){if(window._paq)window._paq.push(['trackEvent','En savoir plus',act,nom])}
var SYID='';
/* liens de la fenêtre : insérés à chaque ouverture, Matomo ne les surveille pas (il pose ses écouteurs au chargement) ;
   les liens vers un autre site sont donc déclarés à la main comme liens sortants (rapport « Liens sortants ») */
box.addEventListener('click',function(e){var l=e.target.closest&&e.target.closest('a[href]');if(!l)return;
 if(l.id==='sy-sh'){evSy('Partager',nomSy(SYID));return}
 if(window._paq&&/^https?:/.test(l.href)&&l.hostname!==location.hostname)window._paq.push(['trackLink',l.href,'link'])});
function open(id,push,src){var d=document.getElementById('d-'+id);if(!d)return;box.innerHTML=d.innerHTML;var h=box.querySelector('.sy-t');if(h)h.id='sy-h';
 box.querySelectorAll('a[href]').forEach(function(x){x.classList.add('matomo_ignore')});   /* pas de double comptage si Matomo rescanne la page */
 SYID=id;if(src!=='hist')evSy(src==='lien'?'Lien partagé':'Ouverture',nomSy(id));
 if(push!==false)try{if(pushed)history.replaceState({syn:id},'','#'+id);else{history.pushState({syn:id},'','#'+id);pushed=true}}catch(e){}
 partage(id);
 if(!dlg.open)dlg.showModal();
 /* remise en haut après l'affichage : fenêtre fermée, le navigateur ignore scrollTop et garde la position précédente (mobile) */
 box.scrollTop=0;dlg.scrollTop=0;requestAnimationFrame(function(){box.scrollTop=0;dlg.scrollTop=0})}
function close(){if(dlg.open)dlg.close()}
dlg.addEventListener('close',function(){if(byPop)return;if(pushed){pushed=false;try{history.back()}catch(e){}}else try{history.replaceState(null,'',location.pathname+location.search)}catch(e){}});
window.addEventListener('popstate',function(e){var s=e.state&&e.state.syn;if(s){pushed=true;open(s,false,'hist');return}pushed=false;if(dlg.open){byPop=true;dlg.close();byPop=false}});
dlg.querySelector('.sy-x').addEventListener('click',close);
/* infobulle d'un sigle : décalage horizontal qui la garde dans la fenêtre (ou la page). Elle s'accroche au début du
   premier morceau du sigle (un sigle coupé en fin de ligne, « EEE- / AELE », a deux morceaux) : on mesure ce morceau. */
function bulle(e){var t=e.target.closest&&e.target.closest('a.t');if(!t)return;var f=t.getClientRects()[0];if(!f)return;
 var z=t.closest('.sy-w')||t.closest('table.cv')||document.body,c=z.getBoundingClientRect(),m=12,
  w=Math.min(parseFloat(getComputedStyle(t,'::after').width)||290,c.width-2*m),dx=Math.min(0,c.right-m-(f.left+w));dx=Math.max(dx,c.left+m-f.left);t.style.setProperty('--dx',Math.round(dx)+'px')}
document.addEventListener('mouseover',bulle);document.addEventListener('focusin',bulle);
dlg.addEventListener('click',function(e){if(e.target===dlg)close()});
document.addEventListener('click',function(e){
 var b=e.target.closest('[data-syn]');if(!b||dlg.contains(b))return;
 var a=e.target.closest('a');
 if(a&&!a.hasAttribute('data-syn'))return; /* liens sources et glossaire : comportement normal */
 e.preventDefault();open(b.getAttribute('data-syn'));
});
document.addEventListener('keydown',function(e){var it=e.target.closest&&e.target.closest('.sy-it');if(it&&(e.key==='Enter'||e.key===' ')&&e.target===it){e.preventDefault();open(it.getAttribute('data-syn'))}});
var h=/^((?:\d{4}-\d{2}-\d{2}-)?syn\d+)(?:\.([0-9a-f]+)(?:-([0-9a-f]+))?)?$/.exec(location.hash.slice(1));if(h){open(h[1],false,'lien');if(h[2])surligne(h[2],h[3])}
})();
</script>'''
NO_EL=False   # passe à True si l'e-mail dépasse la limite de taille : liens par élément retirés
SYN_LABELS=[('contexte','Contexte'),('essentiel','Résumé')]
REDACTION_DEFAUT='Anthropic Claude Opus 5.5'   # meta.json « redaction » : <éditeur> <modèle> <version>
# Image d'en-tête facultative (version web) : tools/en-tete.(webp|png|jpg), publiée sous /assets/
_TOOLS=os.path.dirname(os.path.abspath(__file__))
FOND='/assets/fond.webp' if os.path.isfile(os.path.join(_TOOLS,'fond.webp')) else None   # fond de page répété (version web)
EN_TETE=next((f'/assets/en-tete.{x}' for x in ('webp','png','jpg') if os.path.isfile(os.path.join(_TOOLS,f'en-tete.{x}'))),None)
def duree_ep():
    return f"{max(1,round(EP['duree_s']/60))}&nbsp;min"
def libelle_ep(diso):
    """« Écouter l'épisode du 4 oct. 2026 »"""
    a,m,j=diso.split('-')
    mois=['janvier','février','mars','avril','mai','juin','juillet','août','septembre','octobre','novembre','décembre']
    return f"Écouter l’épisode du {'1er' if j=='01' else int(j)}&nbsp;{mois[int(m)-1]}&nbsp;{a}"
ICO_RSS='<svg viewBox="0 0 16 16" width="13" height="13" aria-hidden="true"><circle cx="3.2" cy="12.8" r="1.7" fill="currentColor"/><path d="M2 7.2a6.8 6.8 0 0 1 6.8 6.8M2 2.6A11.4 11.4 0 0 1 13.4 14" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"/></svg>'
ICO_VOL='<svg viewBox="0 0 16 16" width="15" height="15" aria-hidden="true"><path d="M2 6h2.5L8 3v10L4.5 10H2z" fill="currentColor"/><path class="w" d="M10.5 5.5a3.5 3.5 0 0 1 0 5M12.3 3.6a6 6 0 0 1 0 8.8" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>'
ICONES='<link rel="icon" href="/favicon.ico" sizes="any"><link rel="icon" type="image/png" sizes="512x512" href="/icon-512.png"><link rel="apple-touch-icon" href="/apple-touch-icon.png">'   # favicon (tools/favicon.ico, copié à la racine du site)
ICO_CASQUE='<svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true"><path d="M2.5 10V8a5.5 5.5 0 0 1 11 0v2" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/><rect x="1.8" y="9" width="3.4" height="5" rx="1.2" fill="currentColor"/><rect x="10.8" y="9" width="3.4" height="5" rx="1.2" fill="currentColor"/></svg>'
ICO_PLAY='<svg viewBox="0 0 16 16" width="12" height="12" aria-hidden="true"><path d="M4 2.5v11l9.5-5.5z" fill="currentColor"/></svg>'
# Outlook pour Windows : sans PixelsPerInch=96, les formes VML sont mises à l'échelle à 120 ppp et le texte du bouton est coupé
MSO_HEAD='<!--[if mso]><xml><o:OfficeDocumentSettings><o:AllowPNG/><o:PixelsPerInch>96</o:PixelsPerInch></o:OfficeDocumentSettings></xml><![endif]-->'
# sommaire latéral : section courante (lecture au défilement) ; bouton de retour au sommaire sur petit écran
# libellés abrégés là où la place manque (colonne du sommaire, signets du podcast)
ABREV={"Chaîne d'approvisionnement":"Chaîne d’appro.","Commerce international":"Export et sanctions","Outils":"Outils et services"}   # libellés propres au sommaire flottant
TOC_JS=r"""<script>(function(){var L=document.querySelector('.toc-l'),B=document.querySelector('.toc-b'),bt=B&&B.querySelector('.toc-bt'),ls=B&&B.querySelector('.toc-ls'),cur=B&&B.querySelector('.toc-c'),N=cur?cur.textContent:'';
var H=[].slice.call(document.querySelectorAll('h2[id^="s"]')),AL=L?[].slice.call(L.querySelectorAll('a')):[],AB=ls?[].slice.call(ls.querySelectorAll('a')):[];
function maj(){var y=innerHeight*0.3,k=-1;for(var i=0;i<H.length;i++)if(H[i].getBoundingClientRect().top<y)k=i;
 [AL,AB].forEach(function(A){A.forEach(function(a,i){a.classList.toggle('on',i===k);if(i===k)a.setAttribute('aria-current','true');else a.removeAttribute('aria-current')})});
 if(cur){cur.textContent=k>=0&&AB[k]?AB[k].textContent:N;cur.classList.toggle('en',k>=0)}
 if(B)B.classList.toggle('colle',B.getBoundingClientRect().top<=0.5&&scrollY>0)}
function ouvre(o){if(!B)return;ls.hidden=!o;bt.setAttribute('aria-expanded',o);B.classList.toggle('ouvert',o)}
if(bt){bt.addEventListener('click',function(){ouvre(ls.hidden)});
 ls.addEventListener('click',function(e){if(e.target.closest('a'))ouvre(false)});
 document.addEventListener('click',function(e){if(!B.contains(e.target))ouvre(false)});
 document.addEventListener('keydown',function(e){if(e.key==='Escape'&&!ls.hidden){ouvre(false);bt.focus()}})}
addEventListener('scroll',maj,{passive:true});addEventListener('resize',maj);maj()})()</script>"""
def bloc_podcast(web,diso,ed_url):
    """Barre « Écouter l'épisode » (largeur de la colonne) entre l'en-tête et la Une.
    Web : se déplie au clic (lecteur aux couleurs de la page). E-mail : lien vers la page web."""
    if not EP or not diso: return ''
    m=duree_ep()
    if not web:
        if not ed_url: return ''
        # le clic ouvre la page de l'édition, lecteur déplié (#ecouter) : l'écoute y est mesurée (Matomo)
        u=f'{ed_url}#ecouter'
        # Outlook pour Windows (moteur Word) ignore border-radius et ne rend cliquable que le texte d'un lien :
        # bouton VML arrondi, entièrement cliquable ; les autres clients reçoivent la boîte HTML
        vml=(f'<!--[if mso]><table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td align="center">'
             f'<v:roundrect xmlns:v="urn:schemas-microsoft-com:vml" xmlns:w="urn:schemas-microsoft-com:office:word" href="{u}" style="height:46px;v-text-anchor:middle;width:616px;" arcsize="50%" strokecolor="#e3d6c3" fillcolor="#f7f4ee">'
             f'<w:anchorlock/><v:textbox inset="0,0,0,0" style="mso-fit-shape-to-text:false;"><center style="color:{NAVY};font-family:Segoe UI,Arial,sans-serif;font-size:14px;line-height:22px;mso-line-height-rule:exactly;font-weight:600;"><span style="color:{ACC};">&#9654;</span>&nbsp;&nbsp;{libelle_ep(diso)}&nbsp;&nbsp;<span style="color:#6b7280;font-weight:400;">{m}</span></center></v:textbox>'
             f'</v:roundrect></td></tr></table><![endif]-->')
        html_=(f'<!--[if !mso]><!-- --><table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="width:100%;background:#f7f4ee;border:1px solid #e3d6c3;border-radius:22px;">'
               f'<tr><td style="padding:0;"><a href="{u}" style="display:block;padding:10px 18px;text-decoration:none;border-radius:22px;"><table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>'
               f'<td style="font:600 14px/22px {SANS};color:{NAVY};"><span style="color:{ACC};">&#9654;</span>&nbsp;&nbsp;{libelle_ep(diso)}</td>'
               f'<td align="right" style="font:13px/22px {SANS};color:#6b7280;white-space:nowrap;">{m}</td></tr></table></a></td></tr></table><!--<![endif]-->')
        esp='<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td height="26" style="height:26px;font-size:0;line-height:26px;">&nbsp;</td></tr></table>'
        return vml+html_+esp
    titre=esc(typo((POD or {}).get('titre','')))
    # signets : début de chaque sujet (episode.json, « chapitres ») sauf ouverture et clôture ; libellé court (avant « : »)
    ch=[c for c in EP.get('chapitres') or [] if c.get('titre') not in ('Ouverture','Clôture')]
    fm=lambda t:f'{int(t)//60}:{int(t)%60:02d}'
    signets=('<div class="pod-ch" role="group" aria-label="Sujets de l’épisode">'+''.join(
        f'<button type="button" data-t="{c["debut_s"]}" title="{fm(c["debut_s"])} · {esc(typo(c["titre"]),True)}">{esc(typo(c.get("court") or c["titre"].split(" : ")[0]))}</button>' for c in ch)+'</div>') if ch else ''
    # repères des sujets sous la barre, à leur position (la course du curseur va de 7 px à largeur − 7 px)
    frac=lambda c:f'{c["debut_s"]/max(1,EP["duree_s"]):.4f}'
    temps=('<div class="pod-tl" role="group" aria-label="Sujets de l’épisode">'+''.join(
        f'<button type="button" data-t="{c["debut_s"]}" style="left:calc(7px + (100% - 14px) * {frac(c)})" title="{fm(c["debut_s"])} · {esc(typo(c["titre"]),True)}"><span>{esc(typo(c.get("court") or c["titre"].split(" : ")[0]))}</span></button>' for c in ch)+'</div>') if ch else ''
    reperes=''
    return (f'<div class="pod" id="ecouter">'
            f'<button type="button" class="pod-h" aria-expanded="false" aria-controls="pod-b"><span class="pod-i">{ICO_PLAY}<span class="pod-eq" aria-hidden="true"><i></i><i></i><i></i></span></span><span class="pod-k">Podcast</span><span class="pod-l">{libelle_ep(diso)}</span><span class="pod-d">{ICO_CASQUE}{m}</span></button>'
            f'<div class="pod-b" id="pod-b" role="region" aria-label="Podcast"><div class="pod-in">'
            f'<div class="pod-hd"><div class="pod-t"><span class="pod-tx">{esc(typo(titre_episode(META["n"],(POD or {}).get("titre",""))))}</span></div>'
            f'<a class="pod-rss" href="/podcast.xml" title="Flux RSS du podcast, à ajouter dans votre application de podcasts">{ICO_RSS}<span>S’abonner</span></a></div>'
            +
            f'<audio preload="none" src="/{diso}/{EP_FICHIER}"></audio>'
            f'<div class="pod-p"><button type="button" class="pod-pl" aria-label="Lecture">{ICO_PLAY}</button>'
            f'<div class="pod-tw"><span class="pod-tm"><span class="pod-c">0:00</span> / {EP["duree_s"]//60}:{EP["duree_s"]%60:02d}</span>'
            f'<span class="pod-rw"><input class="pod-r" type="range" min="0" max="{EP["duree_s"]}" step="0.1" value="0" aria-label="Position dans l’épisode"{reperes}><span class="pod-th" aria-hidden="true"></span></span>'
            +temps+'</div>'+
            f'<span class="pod-vw"><button type="button" class="pod-m" aria-label="Volume" aria-expanded="false">{ICO_VOL}</button>'
            f'<span class="pod-vp"><button type="button" class="pod-mu" aria-label="Couper le son">{ICO_VOL}</button><input class="pod-v" type="range" min="0" max="1" step="0.05" value="1" aria-label="Volume"></span></span></div>'
            +signets+
            f'</div></div></div>')
POD_JS=r"""<script>
(function(){
var w=document.getElementById('ecouter');if(!w)return;
var h=w.querySelector('.pod-h'),b=w.querySelector('.pod-b'),a=w.querySelector('audio'),pl=w.querySelector('.pod-pl'),r=w.querySelector('.pod-r'),c=w.querySelector('.pod-c');
var PLAY=pl.innerHTML,PAUSE='<svg viewBox="0 0 16 16" width="12" height="12" aria-hidden="true"><path d="M4 2.5h3v11H4zM9 2.5h3v11H9z" fill="currentColor"/></svg>';
function fmt(t){t=Math.floor(t||0);return Math.floor(t/60)+':'+('0'+t%60).slice(-2)}
var TD=null;function set(o){w.classList.toggle('on',o);h.setAttribute('aria-expanded',o);b.style.maxHeight=o?b.scrollHeight+'px':'0px';clearInterval(TD);if(o){defile();TD=setInterval(defile,30000)}}
/* titre de l'épisode sur une ligne : s'il est trop long, il défile lentement à l'ouverture puis toutes les 30 s, et s'affiche sinon coupé par « … » */
function defile(){var t=w.querySelector('.pod-t'),x=t&&t.querySelector('.pod-tx');if(!x||t.classList.contains('run'))return;
 if(!x.animate||matchMedia('(prefers-reduced-motion: reduce)').matches)return;
 t.classList.add('run');var d=x.scrollWidth-t.clientWidth;if(d<=0){t.classList.remove('run');return}
 var a=x.animate([{transform:'translateX(0)'},{transform:'translateX(0)',offset:.15},{transform:'translateX('+(-d)+'px)',offset:.85},{transform:'translateX('+(-d)+'px)'}],{duration:Math.max(5000,d*45+2500),easing:'linear'});
 a.onfinish=function(){t.classList.remove('run')}}
h.addEventListener('click',function(){var o=!w.classList.contains('on');set(o);if(o){if(a.paused)a.play()}else a.pause()});   /* ouverture : lecture ; fermeture : pause */
var m=w.querySelector('.pod-m'),v=w.querySelector('.pod-v');
var mu=w.querySelector('.pod-mu');
function vol(){var x=a.muted?0:a.volume;v.value=x;v.style.setProperty('--p',(100*x)+'%');w.classList.toggle('mu',x==0);mu.setAttribute('aria-label',x==0?'Rétablir le son':'Couper le son')}
mu.addEventListener('click',function(){if(a.muted||a.volume==0){a.muted=false;if(a.volume==0)a.volume=.8}else a.muted=true;vol()});   /* haut-parleur du curseur : couper / rétablir */
v.addEventListener('input',function(){a.volume=+v.value;a.muted=(+v.value==0);vol()});
/* haut-parleur : déplie le réglage du volume ; clic ailleurs ou Échap : replie */
/* repli automatique après 3 s sans action sur le curseur */
var VT=null;function vt(){clearTimeout(VT);if(w.classList.contains('volo'))VT=setTimeout(function(){vo(false)},3000)}
function vo(o){w.classList.toggle('volo',o);m.setAttribute('aria-expanded',o);if(o)v.focus();vt()}
['input','pointerdown','pointermove','keydown','wheel'].forEach(function(t){w.querySelector('.pod-vp').addEventListener(t,vt)});
m.addEventListener('click',function(e){e.stopPropagation();vo(!w.classList.contains('volo'))});
document.addEventListener('click',function(e){if(!e.target.closest('.pod-vw'))vo(false)});
document.addEventListener('keydown',function(e){if(e.key==='Escape'&&w.classList.contains('volo')){vo(false);m.focus()}});
a.addEventListener('volumechange',vol);vol();
pl.addEventListener('click',function(){if(a.paused)a.play();else a.pause()});
/* mesure d'audience (Matomo, sans cookie) : lancement, paliers d'écoute, signets ; nom = date de l'édition */
var EPN=(a.getAttribute('src')||'').split('/')[1]||'',VU={};
function ev(act,nom){if(window._paq)window._paq.push(['trackEvent','Podcast',act,nom||EPN])}
a.addEventListener('play',function(){if(!VU.l){VU.l=1;ev('Lecture')}});
a.addEventListener('timeupdate',function(){var d=a.duration||+r.max;if(!d)return;var f=a.currentTime/d;
 [25,50,75].forEach(function(p){if(f>=p/100&&!VU[p]){VU[p]=1;ev('Écoute '+p+' %')}})});
a.addEventListener('ended',function(){if(!VU.f){VU.f=1;ev('Écoute complète')}});
a.addEventListener('play',function(){pl.innerHTML=PAUSE;pl.setAttribute('aria-label','Pause');w.classList.add('joue')});   /* joue : égaliseur dans la barre repliée */
a.addEventListener('pause',function(){pl.innerHTML=PLAY;pl.setAttribute('aria-label','Lecture');w.classList.remove('joue')});
a.addEventListener('loadedmetadata',function(){if(isFinite(a.duration))r.max=a.duration});
/* curseur dessiné : position en pixels fractionnaires (transform), mise à jour à chaque image pendant la lecture */
var th=w.querySelector('.pod-th');
function pos(f){f=Math.max(0,Math.min(1,f||0));var x=7+(r.clientWidth-14)*f;th.style.transform='translate3d('+(x-5)+'px,0,0)';r.style.setProperty('--p',x+'px')}
function boucle(){if(a.paused||r.matches(':active'))return;pos(a.currentTime/(r.max||1));requestAnimationFrame(boucle)}
a.addEventListener('play',function(){requestAnimationFrame(boucle)});
a.addEventListener('timeupdate',function(){if(!r.matches(':active')){r.value=a.currentTime;if(a.paused)pos(a.currentTime/(r.max||1))}c.textContent=fmt(a.currentTime)});
r.addEventListener('input',function(){a.currentTime=+r.value;c.textContent=fmt(r.value);pos(r.value/(r.max||1))});
r.addEventListener('change',function(){if(!a.paused)requestAnimationFrame(boucle)});
addEventListener('resize',function(){pos(+r.value/(r.max||1))});h.addEventListener('click',function(){setTimeout(function(){pos(+r.value/(r.max||1))},60)});
/* sujets : ligne de mots sous les commandes et repères cliquables sous la barre */
var S=[].slice.call(w.querySelectorAll('.pod-ch button')),TL=[].slice.call(w.querySelectorAll('.pod-tl button'));
var CH=w.querySelector('.pod-ch');function deb(){if(CH)CH.classList.toggle('deb',CH.scrollWidth>CH.clientWidth+1)}addEventListener('resize',deb);h.addEventListener('click',function(){setTimeout(deb,50)});deb();
S.concat(TL).forEach(function(s){s.addEventListener('click',function(){var t=+s.getAttribute('data-t');ev('Signet',EPN+' · '+(s.textContent||s.title||'').trim());a.currentTime=t;r.value=t;c.textContent=fmt(t);pos(t/(r.max||1));chap();if(a.paused)a.play()})});
function chap(){[S,TL].forEach(function(L){var k=-1;L.forEach(function(s,i){if(a.currentTime+0.25>=+s.getAttribute('data-t'))k=i});
 L.forEach(function(s,i){var on=i===k;if(L===S&&on&&!s.classList.contains('on')&&s.parentNode.scrollWidth>s.parentNode.clientWidth)s.parentNode.scrollTo({left:s.offsetLeft-24,behavior:'smooth'});
  s.classList.toggle('on',on)})})}
a.addEventListener('timeupdate',chap);a.addEventListener('seeked',function(){chap();pos(a.currentTime/(r.max||1))});
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
        if sm.get('fonctions'): meta.append(f'<dt>Fonctions</dt><dd>{T(sm["fonctions"])}</dd>')
        def etiq(lab,v):   # « Connecté : détail » -> intitulé et étiquette « Connecté » sur une ligne, détail dessous (README, § 6)
            m_=re.match(r'([^:;]{1,24}?)\s*:\s*(.+)$',v,re.S)
            if not m_: return f'<dt>{lab}</dt><dd>{T(v)}</dd>'
            return f'<dt>{lab} <span class="sy-k">{T(m_.group(1))}</span></dt><dd>{T(m_.group(2)[:1].upper()+m_.group(2)[1:])}</dd>'
        if sm.get('reseau'): meta.append(etiq('Réseau',sm['reseau']))   # outils et services (README, § 6)
        if sm.get('licence'): meta.append(etiq('Licence',sm['licence']))
        # encart à droite du texte sur grand écran (CSS), au-dessus sur petit écran ; ordre du DOM inchangé pour la numérotation des mots
        h.append('<div class="sy-g">'+('<dl class="sy-m">'+''.join(meta)+'</dl>' if meta else '')+'<div class="sy-c">')
        for k,lab in SYN_LABELS:
            if sm.get(k): h.append(f'<h4>{lab}</h4><p>{M(sm[k])}</p>')
        if sm.get('impact_avere') or sm.get('impact_potentiel'):
            h.append('<h4>Impact</h4>')
            for k in ('impact_avere','impact_potentiel'):
                if sm.get(k): h.append(f'<p>{M(sm[k])}</p>')
        if sm.get('a_verifier'):
            h.append('<h4>À vérifier</h4><ul class="sy-v">'+''.join(f'<li>{M(q)}</li>' for q in sm['a_verifier'])+'</ul>')
        h.append('</div></div>')
        if srcs:
            h.append('<p class="sy-s"><span class="sy-sl">'+('Sources' if len(srcs)>1 else 'Source')+'&nbsp;:</span>'+' '.join(f'<a href="{esc(u,True)}" target="_blank" rel="noopener">↗&nbsp;{T(l)}</a>' for l,u in srcs)+'</p>')
        seen.clear(); seen.update(sv_seen); used[:]=sv_used
        sid=f'syn{len(syns)+1}'
        syns.append(f'<div class="sy-d" id="d-{sid}" hidden>{"".join(h)}</div>')
        SYNH[sid]="".join(h)   # repris dans les pages Dossiers (items.json)
        return sid
    def srcs_of(items): return [(x['t'],x['href']) for x in items if x.get('href')]
    SYNB='<button type="button" class="sy-b" data-syn="{0}" aria-haspopup="dialog" aria-label="En savoir plus"><span class="sy-p"><svg viewBox="0 0 16 16" width="12" height="12" aria-hidden="true"><path d="M8 3.5v9M3.5 8h9" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg><span class="sy-l">En savoir plus</span></span></button>'

    LS="color:#6b7280;font:13px/1 %s;text-decoration:none;border-bottom:1px dotted #9ca3af;white-space:nowrap;"%SANS
    FLECHE="font-weight:400;font-family:'Segoe UI Symbol','Segoe UI',Arial,sans-serif;"
    LSO="color:#6b7280;font:13px/1 %s;text-decoration:none;border-bottom:1px dotted #9ca3af;white-space:nowrap;"%SANS
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
                if web:
                    lab=E(typo(t[2:])) if t.startswith('↗\u00a0') else E(typo(t))
                    fl='<span class="ar" aria-hidden="true">↗</span>\u00a0' if t.startswith('↗\u00a0') else ''
                    ti=' title="Source officielle"' if o_ else ''
                    r.append(f'<a class="s{" so" if o_ else ""}" href="{a}" target="_blank" rel="noopener"{ti}>{fl}{lab}</a>')
                elif o_ and t.startswith('↗\u00a0'):   # Outlook : pas de glyphe ↗ dans la police en semi-gras -> flèche en graisse normale
                    r.append(f'<a href="{a}" style="{LSO}{"font-size:12px;" if fs<16 else ""}"><span style="{FLECHE}color:{ACC};">↗&nbsp;</span>{E(typo(t[2:]))}</a>')
                else: r.append(f'<a href="{a}" style="{LSO if o_ else LS}{"font-size:12px;" if fs<16 else ""}">{E(typo(t))}</a>')
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
    def point_final(segs):
        """le point final ferme la phrase avant les sources de fin d'élément (« … financière. ↗ ANSSI · 23 sept. »)"""
        g=[dict(x) for x in segs]
        while g and not g[-1].get('href') and re.fullmatch(r'[\s).]*',g[-1]['t']): g.pop()   # « ). » ou point isolé après la dernière source
        k=len(g)
        while k>0 and (g[k-1].get('href') or re.fullmatch(r'[\s,;()]*|\s*et\s*',g[k-1]['t'])): k-=1   # sources de fin (et leurs séparateurs)
        if k==0: return g
        t=g[k-1]['t'].rstrip().rstrip('(').rstrip()
        if k<len(g): g[k:]=[x if x.get('href') else {'t':' '} for x in g[k:]]
        if not t.endswith(('.','!','?','…')): t=t+'.'
        g[k-1]['t']=t+(' ' if k<len(g) else '')
        return g
    def item(segs,sm,attrs,kind,small=False):
        sid=syn_html(sm,srcs_of(segs),cursec) if sm else None
        inner=inl(point_final(segs),fs=14 if small else 16)+tail(segs,attrs)
        if web:
            ITEMS.append({'sid':sid,'sec':cursec,'kind':kind,'rappel':bool((attrs or {}).get('rappel')),'date':(attrs or {}).get('date'),'themes':(attrs or {}).get('themes',[]),'segs':segs,'sum':sm,'html':B._post(inner)})
        if sid and web:
            m_=re.search(r'((?:<a class="s[^"]*"[^>]*>(?:[^<]|<span[^>]*>[^<]*</span>)*</a>\s*)?)(<span style="color:#8a8f98;[^"]*">(?:[^<]|<sup[^>]*>[^<]*</sup>)*</span>\.?|[^\s<>]+)$',inner)
            # dernière source, date et bouton sur une ligne ; sur petit écran, la source peut passer seule à la ligne (.nw2 : date + bouton)
            inner=(inner[:m_.start()]+'<span class="nw">'+m_.group(1)+'<span class="nw2">'+m_.group(2)+' '+SYNB.format(sid)+'</span></span>') if m_ else inner+' '+SYNB.format(sid)
        elif sid: inner+=EL(sid)
        return sid,inner
    def syattr(sid): return f' class="sy-it" data-syn="{sid}"' if (web and sid) else ''
    def row(sid,inner):
        return f'<tr{syattr(sid)}><td width="20" valign="top" style="width:20px;min-width:20px;padding:16px 0 0;font:8px/8px Arial,sans-serif;color:#dba98f;"><div style="width:20px;">&#9632;</div></td><td style="padding:8px 8px 8px 0;font:16px/24px {SERIF};color:#1f2937;">{inner}</td></tr>'
    def rcell(sid,inner):
        return f'<table class="rp" role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr{syattr(sid)}><td width="16" valign="top" style="width:16px;min-width:16px;padding:12px 0 0;font:7px/7px Arial,sans-serif;color:#dba98f;"><div style="width:16px;">&#9632;</div></td><td style="padding:5px 6px 5px 0;font:14px/20px {SERIF};color:#374151;">{inner}</td></tr></table>'
    rap=[]   # rappels de la section courante, affichés en fin de section sur deux colonnes
    def flush():
        if not rap: return
        cells=[rcell(*item(sg,sm,a,kd,small=True)) for sg,sm,a,kd in rap]
        rows_=''.join(f'<tr><td class="c2" width="50%" valign="top" style="padding:0 10px 0 0;">{cells[i]}</td><td class="c2" width="50%" valign="top" style="padding:0 0 0 10px;">{cells[i+1] if i+1<len(cells) else "&nbsp;"}</td></tr>' for i in range(0,len(cells),2))
        ln='<div style="border-top:1px solid #e3ddd0;font-size:0;line-height:0;">&nbsp;</div>'
        body.append(f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" bgcolor="#faf8f3" style="margin:6px 0 4px;background:#faf8f3;border-radius:6px;"><tr><td style="padding:10px 14px 6px;"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 8px;"><tr><td width="50%" valign="middle">{ln}</td><td valign="middle" style="padding:0 12px;font:700 11px/16px {SANS};letter-spacing:.12em;text-transform:uppercase;color:#7d6c47;white-space:nowrap;">Rappels</td><td width="50%" valign="middle">{ln}</td></tr></table><table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 6px;">{rows_}</table></td></tr></table>')
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
                body.append(f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 16px;"><tr><td style="border-left:4px solid {ACC};border-radius:6px;background:#f7f4ee;padding:16px 20px;font:17.7px/26px {SERIF};color:{NAVY};">{inl(b["i"],False)}</td></tr></table>')
                body.append('@@TOC@@');continue
            if prev_h2 and not b.get('attrs') and not b.get('sum') and not raw.startswith(('Depuis le','Défense','Lien avec')):
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
            BG=' bgcolor="#f7f4ee"'
            def agt(t):
                h=inl(t,False) if isinstance(t,list) else mark(t,web)
                return re.sub(r'<a [^>]*?(?:title|data-tip)="([^"]*)"[^>]*>(.*?)</a>',lambda m:f'<abbr title="{m.group(1)}" style="text-decoration:none;">{m.group(2)}</abbr>',h)
            def ev(e):
                txt=agt(e['det'] if e['long'] else e['t'])
                head=f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0"{"" if web else BG}><tr><td{"" if web else BG} style="font:600 13px/20px {SANS};color:{ACC};">{e["lab"]}</td><td{"" if web else BG} align="right" style="font:400 10px/14px {SANS};"><span style="background:transparent;border:1px solid #b5a37c;color:#7d6c47;font-weight:400;padding:1px 9px;border-radius:10px;letter-spacing:.05em;text-transform:uppercase;white-space:nowrap;">{e["th"]}</span></td></tr></table>'
                sid=None
                if e['sum']:
                    sid=syn_html(e['sum'],[('Page de référence',e['u'])],'Agenda')
                if web: ITEMS.append({'sid':sid,'sec':'Agenda','kind':'agenda','rappel':False,'date':e['date'],'label':e['lab'],'theme':e['th'],'themes':e['themes'],'segs':e['t'],'u':e['u'],'sum':e['sum'],'html':B._post(txt)})
                if web and e['sum']:
                    return f'<div class="sy-it sy-ev" data-syn="{sid}" style="margin:0 0 13px;">{head}<a href="#{sid}" data-syn="{sid}" style="display:block;font:14px/21px {SERIF};color:#1f2937;text-decoration:none;">{txt} {SYNB.format(sid).replace("<button","<span").replace("</button>","</span>")}</a></div>'
                return f'<div style="margin:0 0 13px;">{head}<a href="{e["u"]}" target="_blank" rel="noopener" style="display:block;font:14px/21px {SERIF};color:#1f2937;text-decoration:none;">{txt}</a></div>'
            cards=[]
            for (yr,mo),its in groups.items():
                if not web:
                    cards.append(f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" bgcolor="#f7f4ee" style="background:#f7f4ee;border-radius:6px;"><tr><td bgcolor="#f7f4ee" style="background:#f7f4ee;padding:14px 16px 4px;"><div style="font:600 12px/16px {SANS};letter-spacing:.14em;text-transform:uppercase;color:{NAVY};padding:0 0 10px;">{mo.capitalize()} {yr}</div>{"".join(ev(e) for e in its)}</td></tr></table>'); continue
                cards.append(f'<div style="background:#f7f4ee;border-radius:6px;padding:14px 16px 4px;"><div style="font:600 12px/16px {SANS};letter-spacing:.14em;text-transform:uppercase;color:{NAVY};padding:0 0 10px;">{mo.capitalize()} {yr}</div>{"".join(ev(e) for e in its)}</div>')
            sp='<div style="height:14px;font-size:0;line-height:14px;">&nbsp;</div>'
            rows=f'<tr><td class="c" width="50%" valign="top" style="padding:0 7px 0 0;">{sp.join(cards[:cut])}</td><td class="c" width="50%" valign="top" style="padding:0 0 0 7px;">{sp.join(cards[cut:])}</td></tr>'
            body.append(f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 8px;">{rows}</table>');prev_h2=False
    flush()
    SEC=META['toc']
    if web:
        # sommaire. Petits écrans : barre en haut de l'article, qui reste en haut de l'écran pendant la lecture
        # (section en cours ; liste au clic). Dès 912 px : colonne fixe dans la marge gauche, l'article se décale
        # vers la droite si la marge ne suffit pas (la colonne mord d'un tiers sur la marge intérieure de l'article).
        tocb=''
        li=''.join(f'<li><a href="#s{i}">{E(s)}</a></li>' for i,s in enumerate(SEC))
        ab=lambda x:ABREV.get(x.replace('’',"'"),x)
        lic=''.join(f'<li><a href="#s{i}" title="{E(s)}">{E(ab(s))}</a></li>' for i,s in enumerate(SEC))   # colonne étroite : libellés abrégés
        TOCBAR=('<style>@media(max-width:660px){.w.hd{padding-bottom:0!important}.toc-b{margin-top:-16px!important}}</style>'   # petit écran : pas de marge basse sous l'en-tête
                '<nav class="toc-b" id="sommaire" aria-label="Sommaire"><button type="button" class="toc-bt" aria-expanded="false" aria-controls="toc-ls">'
                '<svg viewBox="0 0 16 16" width="15" height="15" aria-hidden="true"><path d="M5 4h8M5 8h8M5 12h8" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/><circle cx="2.5" cy="4" r="1" fill="currentColor"/><circle cx="2.5" cy="8" r="1" fill="currentColor"/><circle cx="2.5" cy="12" r="1" fill="currentColor"/></svg>'
                f'<span class="toc-x"><span class="toc-t">Sommaire</span><span class="toc-c">{len(SEC)} rubriques</span></span><svg class="toc-v" viewBox="0 0 16 16" width="12" height="12" aria-hidden="true"><path d="M4 6l4 4 4-4" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg></button>'
                f'<ol class="toc-ls" id="toc-ls" hidden>{li}</ol></nav>')
        TOCNAV=f'<nav class="toc-l" aria-label="Sommaire"><span class="toc-t">Sommaire</span><ol>{lic}</ol></nav>'+TOC_JS
    else:
        toc=' <span style="color:#c3cad5;">·</span> '.join(f'<a href="#s{i}" style="color:#4b5563;text-decoration:none;border-bottom:1px solid #d5dbe5;">{E(s)}</a>' for i,s in enumerate(SEC))
        tocb=f'<p style="margin:0 0 4px;font:13px/24px {SANS};color:#6b7280;"><b style="font-weight:600;color:#4b5563;">Dans ce numéro</b>&nbsp; {toc}</p>'
        TOCNAV=TOCBAR=''
    out=B._post(''.join(body).replace('@@TOC@@',tocb))
    import re as _re
    mins=max(1,round(len(_re.sub(r'<[^>]+>',' ',out).split())/220))
    css=''
    if web:
        css=f'''body{{font-variant-numeric:lining-nums}}
table.cv{{overflow:clip;box-shadow:0 1px 2px rgba(15,42,74,.05),0 8px 28px rgba(15,42,74,.07)}}
a.t{{border-bottom:1px dotted #9ca3af;color:inherit;text-decoration:none;position:relative;cursor:help}}
a.t:hover,a.t:focus{{border-bottom-color:{NAVY}}}
a.t[href]{{cursor:pointer}}   /* sigle avec lien : main ; sans lien : flèche et point d'interrogation (cursor:help) */
a.t:hover::after,a.t:focus::after{{content:attr(data-tip);position:absolute;left:var(--dx,0px);top:1.7em;z-index:9;width:290px;max-width:calc(100vw - 24px);box-sizing:border-box;background:#0f2a4a;color:#fff;font:400 13px/1.45 {SANS};padding:9px 11px;border-radius:6px;box-shadow:0 4px 14px rgba(0,0,0,.25)}}
a.rss{{display:inline-flex;vertical-align:-2px;color:{ACC}}}a.rss:hover,a.rss:focus-visible{{color:{NAVY}}}
a.s{{color:#6b7280;font:14px {SANS};text-decoration:none;border-bottom:1px dotted #9ca3af;white-space:nowrap}}
.nw,.nw2{{white-space:nowrap}}
@media(max-width:660px){{.nw{{white-space:normal}}}}
a.s .ar{{color:#9ca3af}}
a.s.so .ar{{color:{ACC}}}
h2[id^='s']{{scroll-margin-top:56px}}
.toc-b{{position:sticky;top:0;z-index:30;margin:-24px 0 18px;background:#fff;border-bottom:1px solid #ece7dc}}
.toc-b.colle{{box-shadow:0 6px 10px -8px rgba(15,42,74,.25)}}
.toc-bt{{display:flex;align-items:center;gap:8px;width:100%;height:40px;padding:0 2px;border:0;background:none;color:{NAVY};font:13px/1 {SANS};text-align:left;cursor:pointer}}
.toc-x{{display:flex;align-items:baseline;gap:8px;flex:1;min-width:0}}
.toc-bt svg{{flex:none}}
.toc-bt .toc-t{{font:400 11px/1 {SANS};letter-spacing:.14em;text-transform:uppercase;color:#6f675a}}
.toc-c{{flex:1;min-width:0;overflow:hidden;white-space:nowrap;text-overflow:ellipsis;color:#9ca3af}}
.toc-c.en{{color:#4b5563}}
.toc-v{{flex:none;color:#6f675a;transition:transform .15s}}
.toc-b.ouvert .toc-v{{transform:rotate(180deg)}}
.toc-ls{{position:absolute;left:0;right:0;top:100%;margin:0;padding:6px 0;list-style:none;background:#fff;border:1px solid #ece7dc;border-top:0;border-radius:0 0 6px 6px;box-shadow:0 10px 18px -10px rgba(15,42,74,.3)}}
.toc-ls a{{display:block;padding:8px 14px;border-left:2px solid transparent;color:#4b5563;font:14px/20px {SANS};text-decoration:none}}
.toc-ls a.on{{border-left-color:{ACC};color:{NAVY}}}
.toc-ls a:hover,.toc-ls a:focus-visible{{background:#faf8f3;color:{NAVY};outline:none}}
.toc-l{{display:none}}
@media(min-width:912px){{
.toc-b{{display:none}}
table.cv{{margin-left:max(175px,calc((100% - 720px) / 2))!important;margin-right:auto!important}}
.toc-l{{display:block;position:fixed;z-index:30;top:120px;left:calc(8px + max(175px,(100% - 736px) / 2) - 167px);width:184px;box-sizing:border-box;padding:14px 16px 12px;background:#fcfbf8;border:1px solid rgba(194,65,12,.5);border-radius:8px;box-shadow:0 1px 3px rgba(15,42,74,.08),0 6px 18px rgba(15,42,74,.10);font:13px/18px {SANS}}}
.toc-l .toc-t{{display:block;margin:0 0 8px;font:400 11px/16px {SANS};letter-spacing:.14em;text-transform:uppercase;color:#6f675a}}
.toc-l ol{{margin:0;padding:0;list-style:none;border-left:2px solid #ece7dc}}
.toc-l a{{display:block;margin-left:-2px;padding:4px 0 4px 12px;border-left:2px solid transparent;color:#6b7280;text-decoration:none}}
.toc-l a:hover,.toc-l a:focus-visible{{color:{NAVY};outline:none}}
.toc-l a.on{{border-left-color:{ACC};color:{NAVY};font-weight:600}}}}
td[style*='font:14px/20px'] a.s{{font-size:12px}}
.sy-it{{cursor:pointer;transition:background .15s}}
.sy-it:hover{{background:#faf7f0}}
p.sy-it,div.sy-it{{border-radius:6px}}
tr.sy-it:hover{{background:none}}
tr.sy-it>td{{transition:background .15s}}
tr.sy-it:hover>td{{background:#faf7f0}}
tr.sy-it:hover>td:first-child{{color:transparent!important}}
.rp tr.sy-it:hover>td:first-child{{color:#dba98f!important}}
tr.sy-it>td:first-child{{border-radius:6px 0 0 6px}}
tr.sy-it>td:last-child{{border-radius:0 6px 6px 0}}
.sy-b{{display:inline-block;position:relative;width:20px;height:20px;margin:0 0 0 5px;padding:0;border:0;background:none;vertical-align:-4px;cursor:pointer}}
.sy-p{{position:absolute;left:0;top:0;z-index:1;display:flex;align-items:center;box-sizing:border-box;height:20px;min-width:20px;padding:0 3px;border:1px solid #e1c6b4;border-radius:10px;background:#fff;color:{ACC};white-space:nowrap;transition:left .18s ease,background .15s,color .15s,border-color .15s}}
.sy-p svg{{flex:none;display:block}}
.sy-l{{display:inline-block;max-width:0;overflow:hidden;opacity:0;font:600 11px/1 {SANS};letter-spacing:.02em;transition:max-width .18s ease,opacity .15s,margin .18s,padding .18s}}
.sy-b:hover .sy-p,.sy-b:focus-visible .sy-p{{z-index:5;background:{ACC};border-color:{ACC};color:#fff;box-shadow:0 2px 8px rgba(15,42,74,.18)}}
.sy-b:hover .sy-l,.sy-b:focus-visible .sy-l{{max-width:9em;opacity:1;margin-left:4px;padding-right:6px}}
.sy-b:focus-visible{{outline:none}}
.pod{{width:100%;box-sizing:border-box;margin:0 0 24px;background:#f7f4ee;border:1px solid #e3d6c3;border-radius:22px;overflow:hidden}}
.pod-h{{display:flex;align-items:center;gap:10px;width:100%;padding:10px 18px;border:0;background:none;color:{NAVY};font:600 14px/22px {SANS};text-align:left;cursor:pointer}}
.pod-h:hover,.pod-h:focus-visible{{background:#f1ebdf;outline:none}}
.pod-i{{display:inline-flex;align-items:center;justify-content:center;width:24px;height:24px;border-radius:50%;background:{ACC};color:#fff;flex:none}}
.pod-i svg{{margin-left:2px}}
.pod-l{{flex:1}}
.pod-d{{display:inline-flex;align-items:center;gap:6px;font:400 13px/22px {SANS};color:#6b7280;white-space:nowrap}}
.pod-d svg{{flex:none;color:#8a8f98}}
.pod-ch{{display:flex;justify-content:space-between;gap:4px;width:0;min-width:100%;margin:12px 0 0;overflow-x:auto;white-space:nowrap;scrollbar-width:none;}}
.pod-ch.deb{{-webkit-mask-image:linear-gradient(to right,#000 calc(100% - 24px),transparent);mask-image:linear-gradient(to right,#000 calc(100% - 24px),transparent)}}
.pod-ch::-webkit-scrollbar{{display:none}}
.pod-ch button{{flex:none;padding:2px 8px;border:0;border-radius:11px;background:none;color:#8a8f98;font:12px/18px {SANS};cursor:pointer}}
.pod-ch button:hover,.pod-ch button:focus-visible{{color:{NAVY};outline:none}}
.pod-ch button.on{{background:#fff;color:{ACC}}}
.pod-b{{max-height:0;overflow:hidden;transition:max-height .28s ease}}
.pod-in{{padding:4px 22px 16px;border-top:1px solid #e3d6c3}}
.pod-hd{{display:flex;align-items:center;gap:14px;margin:12px 0 10px}}
.pod-hd .pod-rss{{flex:none}}
.pod-k{{flex:none;padding-right:10px;border-right:1px solid #e3d6c3;font:600 12px/16px {SANS};letter-spacing:.16em;text-transform:uppercase;color:{ACC}}}
@media(max-width:560px){{.pod-k{{display:none}}.pod-hd .pod-rss{{width:28px;height:28px;padding:0;justify-content:center;border-radius:50%}}.pod-hd .pod-rss span{{display:none}}}}
.pod-eb{{margin:0;font:600 12px/16px {SANS};letter-spacing:.16em;text-transform:uppercase;color:{ACC}}}
.pod-t{{flex:1;width:0;min-width:0;margin:0;font:600 16px/23px {SANS};color:{NAVY};white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.pod-t.run{{text-overflow:clip}}
.pod-t.run .pod-tx{{display:inline-block}}
.pod-p{{display:flex;align-items:center;gap:12px}}
.pod-pl{{display:inline-flex;align-items:center;justify-content:center;flex:none;width:40px;height:40px;border:0;border-radius:50%;background:{NAVY};color:#fff;cursor:pointer}}
.pod-pl:hover,.pod-pl:focus-visible{{background:{ACC};outline:none}}
.pod-pl svg{{width:14px;height:14px}}
.pod-r{{--p:0%;flex:1;width:0;min-width:0;height:4px;margin:0;border-radius:2px;background:var(--rk,none),linear-gradient(to right,{ACC} var(--p),#dccfb9 var(--p));-webkit-appearance:none;appearance:none;cursor:pointer}}
.pod-r::-webkit-slider-thumb{{-webkit-appearance:none;width:14px;height:14px;border-radius:50%;opacity:0}}
.pod-rw{{position:relative;flex:1;width:0;min-width:0;display:flex;align-items:center}}
.pod-th{{position:absolute;left:0;top:50%;width:10px;height:10px;margin-top:-5px;border-radius:50%;background:{ACC};box-shadow:0 0 0 2px #fff,0 0 0 3px {ACC};pointer-events:none;will-change:transform;transform:translate3d(2px,0,0)}}
.pod-r:focus-visible{{outline:none}}
.pod-r:focus-visible+.pod-th{{box-shadow:0 0 0 2px #fff,0 0 0 3px {ACC},0 0 0 6px rgba(194,65,12,.25)}}
.pod-r::-moz-range-thumb{{width:14px;height:14px;border:0;border-radius:50%;opacity:0}}
.pod-tw{{flex:1;min-width:0;display:flex;flex-direction:column}}
.pod-tm{{align-self:flex-end;margin:0 0 3px;font:11px/14px {SANS};color:#8a8f98;white-space:nowrap;font-variant-numeric:tabular-nums}}
.pod-tw .pod-rw{{flex:none;width:100%;height:14px}}
.pod-tl{{position:relative;height:9px;margin-top:3px}}
.pod-tl button{{position:absolute;top:0;width:9px;height:9px;margin-left:-4px;padding:0;border:0;background:linear-gradient(#c9bba3,#c9bba3) center/1px 6px no-repeat;color:transparent;font-size:0;cursor:pointer}}
.pod-tl button span{{display:none}}
.pod-tl button:hover,.pod-tl button:focus-visible,.pod-tl button.on{{background-image:linear-gradient({ACC},{ACC});background-size:2px 7px;outline:none}}
.pod-p{{align-items:flex-start}}
.pod-p .pod-pl{{margin-top:4px}}
.pod-p .pod-vw{{margin-top:10px}}
.pod-vw{{position:relative;flex:none}}
.pod-vp{{position:absolute;right:0;top:50%;z-index:3;display:flex;align-items:center;gap:6px;height:30px;padding:0 12px 0 4px;box-sizing:border-box;border:1px solid #e3d6c3;border-radius:15px;background:#fff;box-shadow:0 4px 12px rgba(15,42,74,.12);opacity:0;visibility:hidden;transform:translate(6px,-50%);transition:opacity .15s,transform .15s,visibility .15s}}
.pod.volo .pod-vp{{opacity:1;visibility:visible;transform:translate(0,-50%)}}
.pod.volo .pod-m{{color:{ACC}}}
.pod-eq{{display:none;align-items:flex-end;gap:2px;height:11px}}
.pod-eq i{{display:block;width:3px;height:100%;border-radius:1px;background:#fff;transform-origin:bottom}}
.pod.joue .pod-i svg{{display:none}}
.pod.joue .pod-eq{{display:inline-flex}}
@media (prefers-reduced-motion:no-preference){{.pod.joue .pod-eq i{{animation:eq .9s ease-in-out infinite alternate}}.pod.joue .pod-eq i:nth-child(2){{animation-delay:-.45s;animation-duration:.7s}}.pod.joue .pod-eq i:nth-child(3){{animation-delay:-.2s;animation-duration:1.1s}}}}
@keyframes eq{{from{{transform:scaleY(.35)}}to{{transform:scaleY(1)}}}}
.pod-m{{display:inline-flex;align-items:center;justify-content:center;flex:none;width:28px;height:28px;padding:0;border:0;border-radius:50%;background:none;color:{NAVY};cursor:pointer}}
.pod-m:hover,.pod-m:focus-visible{{color:{ACC};outline:none}}
.pod.mu .pod-m .w,.pod.mu .pod-mu .w{{display:none}}
.pod-mu{{display:inline-flex;align-items:center;justify-content:center;flex:none;width:24px;height:24px;padding:0;border:0;border-radius:50%;background:none;color:{NAVY};cursor:pointer}}
.pod-mu:hover,.pod-mu:focus-visible{{color:{ACC};outline:none}}
.pod-v{{--p:100%;flex:none;width:96px;height:4px;margin:0;border-radius:2px;background:linear-gradient(to right,{NAVY} var(--p),#dccfb9 var(--p));-webkit-appearance:none;appearance:none;cursor:pointer}}
.pod-v::-webkit-slider-thumb{{-webkit-appearance:none;width:12px;height:12px;border-radius:50%;background:{NAVY};border:2px solid #fff;box-shadow:0 0 0 1px {NAVY}}}
.pod-v::-moz-range-thumb{{width:10px;height:10px;border-radius:50%;background:{NAVY};border:2px solid #fff}}
.pod-rss{{display:inline-flex;align-items:center;gap:5px;height:24px;box-sizing:border-box;padding:0 11px 0 8px;border:1px solid #e1c6b4;border-radius:12px;background:#fff;color:{ACC};font:600 12px/1 {SANS};text-decoration:none;transition:background .15s,color .15s,border-color .15s}}
.pod-rss svg{{flex:none}}
.pod-rss:hover,.pod-rss:focus-visible{{background:{ACC};border-color:{ACC};color:#fff;outline:none}}
@media(max-width:660px){{.pod{{width:100%}}table.cv{{background-size:60% auto!important}}}}
dialog.sy{{width:min(860px,calc(100vw - 32px));max-height:min(92vh,1200px);padding:0;border:0;border-top:6px solid {ACC};border-radius:8px;overflow:hidden;background:#fff;color:#1f2937;box-shadow:0 18px 50px rgba(15,42,74,.28)}}
dialog.sy::backdrop{{background:rgba(15,42,74,.42);backdrop-filter:blur(2px)}}
dialog.sy[open]{{display:flex;flex-direction:column}}
.sy-w{{flex:1 1 auto;min-height:0;padding:28px 40px 24px;overflow:auto;box-sizing:border-box}}
.sy-w p.sy-s{{display:flex;flex-wrap:wrap;align-items:center;row-gap:6px}}
.sy-w p.sy-s a:not(.sy-sh){{line-height:20px}}
mark.sy-hl{{background:#fff3a3;color:inherit;padding:0;border-radius:2px}}
.sy-w a.sy-sh{{margin:0 0 0 auto;display:inline-flex;align-items:center;gap:6px;padding:3px 11px 3px 9px;border:1px solid #d6d3cc;border-radius:14px;color:#6b7280;font:400 12px/18px {SANS};text-decoration:none;align-self:center;position:relative;top:4px}}
.sy-w a.sy-sh:hover,.sy-w a.sy-sh:focus-visible{{background:{ACC};border-color:{ACC};color:#fff;outline:none}}
.sy-x{{position:absolute;top:12px;right:14px;display:flex;align-items:center;justify-content:center;width:32px;height:32px;padding:0;border:0;border-radius:50%;background:rgba(255,255,255,.94);color:#6b7280;cursor:pointer;z-index:2}}
.sy-x svg{{display:block}}
.sy-x:hover,.sy-x:focus-visible{{color:{NAVY};outline:2px solid #d5dbe5}}
.sy-w{{scrollbar-width:thin;scrollbar-color:#cdd1d8 transparent}}
.sy-w::-webkit-scrollbar{{width:8px}}.sy-w::-webkit-scrollbar-thumb{{background:#cdd1d8;border-radius:4px}}.sy-w::-webkit-scrollbar-track{{background:transparent}}
.sy-w p.sy-eb{{margin:0 0 6px;font:600 11px/16px {SANS};letter-spacing:.14em;text-transform:uppercase;color:{ACC}}}
.sy-t{{margin:0 36px 14px 0;font:600 21px/28px {SANS};color:{NAVY};text-wrap:balance}}
.sy-m{{display:grid;grid-template-columns:max-content 1fr;gap:4px 16px;margin:0 0 16px;padding:10px 14px;background:#f7f4ee;border-radius:6px;font:13px/17px {SANS};color:#374151}}
.sy-m dt{{color:#6f675a;font:400 11px/16px {SANS};letter-spacing:.14em;text-transform:uppercase}}
.sy-m dt,.sy-m dd{{align-self:first baseline}}
.sy-m dt:has(.sy-k){{display:flex;align-items:center;gap:8px}}
.sy-k{{display:inline-flex;align-items:center;box-sizing:border-box;height:17px;padding:0 7px;border:1px solid #d9cfbd;border-radius:9px;background:#fff;font:400 11.5px/1 {SANS};letter-spacing:0;text-transform:none;color:#6b6356;white-space:nowrap}}
@supports (text-box:trim-both cap alphabetic){{.sy-k{{display:inline-block;height:auto;line-height:1;padding:4px 7px;text-box:trim-both cap alphabetic}}}}
.sy-m dd{{margin:0;min-width:0}}
.sy-w h4{{margin:18px 0 6px;font:400 13px/18px {SANS};letter-spacing:.16em;text-transform:uppercase;color:#6f675a}}
.sy-w h4::before{{content:'';display:inline-block;width:12px;height:2px;margin:0 8px 0 0;background:{ACC};vertical-align:.32em}}
.sy-w{{overflow-x:hidden}}
.sy-w a.t{{color:inherit;border-bottom-color:#9ca3af}}
.sy-w a.t:hover,.sy-w a.t:focus{{border-bottom-color:{NAVY}}}
.sy-w a.t:hover::after,.sy-w a.t:focus::after{{width:min(290px,60vw)}}
.sy-w p,.sy-v li{{margin:0 0 10px;font:16px/24px {SERIF};text-wrap:pretty}}
.sy-w{{font-variant-numeric:lining-nums}}
.sy-m dd{{text-wrap:pretty}}
.sy-w p:not(.sy-s),.sy-v li,.sy-m dd{{-webkit-hyphens:auto;hyphens:auto;hyphenate-limit-chars:9 4 4;-webkit-hyphenate-limit-before:4;-webkit-hyphenate-limit-after:4}}
.sy-v{{margin:0;padding-left:12px;list-style:none}}
.sy-w h4~p:not(.sy-s){{padding-left:12px}}
.sy-v li{{margin:0 0 4px;padding-left:2px;line-height:24px}}
.sy-v li{{position:relative;padding-left:16px}}
.sy-v li::before{{content:'';position:absolute;left:0;top:10px;width:6px;height:6px;background:#c9bfae}}
.sy-w p.sy-s{{margin-top:18px!important;padding-top:12px;border-top:1px solid #e5e7eb}}
.sy-s .sy-sl{{margin-right:8px;font:13px/20px {SANS};color:#8a8f98}}
.sy-s a{{margin-right:10px;color:#6b7280;font:13px {SANS};text-decoration:none;border-bottom:1px dotted #9ca3af}}
@media (prefers-reduced-motion:no-preference){{dialog.sy[open]{{animation:syin .18s ease-out}}@keyframes syin{{from{{opacity:0;transform:translateY(8px)}}to{{opacity:1;transform:none}}}}}}
@media(min-width:661px){{.sy-m{{column-gap:36px;padding:12px 20px}}}}
@media(min-width:860px){{.sy-g{{display:flow-root}}.sy-g>.sy-m{{float:right;width:236px;box-sizing:border-box;display:block;margin:4px 0 16px 28px;padding:12px 16px 14px}}.sy-g>.sy-m dd{{margin:2px 0 12px}}.sy-g>.sy-m dd:last-child{{margin-bottom:0}}.sy-c>h4:first-child{{margin-top:4px}}}}
@media(max-width:660px){{.sy-w{{padding:22px 18px 22px}}.sy-m{{grid-template-columns:1fr;gap:0}}.sy-m dd{{margin-bottom:6px}}}}'''
    if web: SYN_ASSETS.update(css='\n'.join(l for l in css.split('\n') if 'sy' in l and not l.startswith(('a.t','a.s'))), js=JS, pill=PILL_JS, synb=SYNB)
    return f'''<!doctype html><html lang="fr"{'' if web else ' xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office"'}><head><meta charset="utf-8">{ICONES if web else MSO_HEAD}<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light">{'<meta name="robots" content="noindex">' if web else ''}<title>{esc(('Revue de presse du '+META.get('date','')+' – Software Compliance') if web else title)}</title>{'<link rel="alternate" type="application/rss+xml" title="Software Compliance" href="/feed.xml">' if web else ''}{'<link rel="alternate" type="application/rss+xml" title="Software Compliance, le podcast" href="/podcast.xml">' if (web and EP) else ''}<style>{css}{CSS_PIED}@media(max-width:660px){{.w{{padding:22px 18px 20px!important}}td.c{{display:block!important;width:100%!important;padding:0 0 12px!important;box-sizing:border-box}}td.c2{{display:block!important;width:100%!important;padding:0!important}}}}</style>{MATOMO if web else ''}</head>
<body style="margin:0;background:#ecebe6;{'background-image:url('+FOND+');background-size:512px 512px;' if (web and FOND) else ''}">{'<div style="background:#0f2a4a;color:#fff;font:13px/20px '+SANS+';text-align:center;padding:8px 16px;">Édition de démonstration : contenu de l’édition de référence, avec des synthèses d’exemple.</div>' if web and META.get('demo') else ''}<span style="display:none;max-height:0;overflow:hidden;">La revue de la semaine : conformité logicielle des produits, export et sanctions, licences.</span>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{'transparent' if (web and FOND) else '#ecebe6'};"><tr><td align="center" style="padding:24px 8px;">
<table class="cv" role="presentation" width="720" cellpadding="0" cellspacing="0" style="width:100%;max-width:720px;background:#fff;border-radius:8px;{('background-image:url('+EN_TETE+');background-repeat:no-repeat;background-position:right 6px;background-size:67.5% auto;') if (web and EN_TETE) else ''}">
<tr><td style="height:6px;background:{ACC};font-size:0;line-height:6px;">&nbsp;</td></tr>
<tr><td class="w hd" style="padding:38px 52px 0;"><div style="font:600 12px/16px {SANS};letter-spacing:.16em;text-transform:uppercase;color:{ACC};">Revue de presse hebdomadaire</div><div style="font:700 46px/52px {SERIF};color:{NAVY};margin:8px 0 14px;letter-spacing:-.01em;"><i style="font-weight:400;color:{ACC};">Software</i> <span style="font:500 44px/52px {SANS};color:{NAVY};letter-spacing:-.025em;">Compliance</span></div><table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-bottom:2px solid {NAVY};"><tr><td style="padding:0 0 14px;font:13px/20px {SANS};color:#6b7280;">N°&nbsp;{META['n']} &nbsp;·&nbsp; {META['date_long'].replace(' ','&nbsp;')} &nbsp;·&nbsp; {'<a href="/archives/" style="color:#6b7280;">Archives</a> &nbsp;·&nbsp; <a href="/dossiers/" style="color:#6b7280;">Dossiers</a> &nbsp;·&nbsp; <a class="rss" href="/feed.xml" title="S’abonner au flux RSS de la revue" aria-label="Flux RSS de la revue">'+ICO_RSS+'</a>' if web else f'<a href="{ED_URL}" style="color:#6b7280;">Afficher dans le navigateur</a>'}</td><td align="right" valign="top" style="padding:0 0 14px 12px;font:13px/20px {SANS};color:#6b7280;white-space:nowrap;"><span style="background:rgba(255,255,255,.5);border-radius:3px;padding:1px 4px;margin-right:-4px;">Lecture ≈&nbsp;{mins}&nbsp;min</span></td></tr></table></td></tr>
<tr><td class="w" style="padding:30px 52px 28px;">{TOCBAR}{bloc_podcast(web,DISO,ED_URL)}{out}
{pied_bloc(META.get("redaction") or REDACTION_DEFAUT,(META.get("date_iso") or "2026")[:4],absolu=not web)}
</td></tr></table></td></tr></table>{''.join(syns)+JS.replace('id="sy" ',f'id="sy" data-ed="{DISO}" ',1)+PILL_JS if web and syns else ''}{POD_JS if web and EP else ''}{TOCNAV}</body></html>''',len(used)
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
    for it in ITEMS: it['syn']=SYNH.get(it.get('sid'))
    json.dump(ITEMS,open(os.path.join(OUT,'items.json'),'w'),ensure_ascii=False)
    json.dump(SYN_ASSETS,open(os.path.join(OUT,'syn.json'),'w'),ensure_ascii=False)
