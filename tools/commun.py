"""Fonctions communes : typographie française, glossaire (bulles), échappement.
À importer depuis le dossier de l’édition (blocks.json est lu dans le dossier courant)."""
import json,re,html,sys,os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from glossary import G
blocks=json.load(open('blocks.json'))
NB=' '
MONTHS='janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre'
def typo(t):
    t=t.replace("'","’")
    t=re.sub(r'\s+([;:!?»])',NB+r'\1',t)
    t=re.sub(r'(«)\s+',r'\1'+NB,t)
    t=re.sub(r'(\d) (?=\d{3}(?!\d))',r'\1'+NB,t)
    t=re.sub(r'(\d) (?=(?:%|€|h\b|M€|Md€|Md\b|M\b))',r'\1'+NB,t)
    t=re.sub(r'(\b(?:\d{1,2}|1er)) (?=(?:'+MONTHS+r')\b)',r'\1'+NB,t)
    t=re.sub(r'\b('+MONTHS+r') (?=\d{4}\b)',r'\1'+NB,t)
    t=re.sub(r'\b(article|articles|art\.|annexe|phase|décret|n°|version|règlement|directive|paquet|\(UE\)) (?=[\d(])',r'\1'+NB,t)
    t=re.sub(r'(?<![\w’])(à|y|de|du|la|le|en|un|ou|et|au|se|ne|ce|si|on|l|d) (?=\S)',r'\1'+NB,t)
    return t
def esc(s,quote=False): return html.escape(s,quote=quote)
def E(s): return re.sub(r'\b(\d+)(er|e)\b',r'\1<sup style="font-size:70%;line-height:0;">\2</sup>',esc(s))
pats=[(i,re.compile(r'(?<![\w-])('+g[0].replace(' ','[  ]')+r')(?![\w])')) for i,g in enumerate(G)]
used=[];seen=set()
def term(shown,i,web):
    d=typo(G[i][2]);u=G[i][3];tip=esc(d,True)
    st="border-bottom:1px dotted #1f4e8c;color:#1f4e8c;text-decoration:none;"
    if web:
        return f'<a class="t" data-tip="{tip}"'+(f' href="{u}" target="_blank" rel="noopener"' if u else '')+f'>{E(shown)}</a>'
    if u: return f'<a href="{u}" title="{tip}" style="{st}">{E(shown)}</a>'
    return f'<abbr title="{tip}" style="{st}">{E(shown)}</abbr>'
def mark(text,web):
    text=typo(text)
    hits=[]
    for i,p in pats:
        if i in seen: continue
        m=p.search(text)
        if m: hits.append((m.start(),m.end(),i))
    hits.sort(key=lambda h:(h[0],-(h[1]-h[0])))
    out=[];pos=0
    for s,e,i in hits:
        if s<pos or i in seen: continue
        seen.add(i);used.append(i)
        out.append(E(text[pos:s]));out.append(term(text[s:e],i,web));pos=e
    out.append(E(text[pos:]));return ''.join(out)
SANS="'Segoe UI',Arial,sans-serif";SERIF="Georgia,serif"
def _post(h): return re.sub(r'>([^<>]+)<',lambda m:'>'+typo(m.group(1))+'<',h)
