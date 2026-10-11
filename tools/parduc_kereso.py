#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
parduc_kereso.py — Kigyűjti a Perplexity-exportból mindent, ami a FEKETE PÁRDUCRA
(a kiskunhalasi / kelet-európai melanisztikus nagymacska-észlelésekre) vonatkozik.

Használat:
    python3 tools/parduc_kereso.py

Kimenet (a `fekete_parduc/` mappába):
    FEKETE_PARDUC_MINDEN.md   – fő jelentés: időrend, teljes szó szerinti idézetek, témakörök
    teljes_szovegek/<id>.md   – az érintett beszélgetések TELJES, csonkítatlan szövege
    parduc_index.json         – géppel olvasható index (fájl, uuid, dátum, entry-k)
    parduc_kereses.html       – offline, böngészőben kereshető nézet
"""

import json
import os
import re
import html
import datetime
from collections import OrderedDict, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "user_data_export_extracted", "conversations_split")
OUT = os.path.join(ROOT, "fekete_parduc")
FULL = os.path.join(OUT, "teljes_szovegek")

# ---------------------------------------------------------------------------
# 1. OSZTÁLYOZÁS – kézzel ellenőrzött, a tartalom alapján
# ---------------------------------------------------------------------------

# T1 – KÖZPONTI: a fekete párduc / melanisztikus nagymacska konkrét kutatása
T1 = [
    "007384",  # 32 entry – A FŐ NYOMOZÁS (farkasok Kiskunhalas, 2021 december, útvonal, fajazonosítás)
    "007238",  # kiskunhalas 1900/1800-as évek + párduc-érvek, birkák Kiskunfélegyházán
    "007040",  # Kiskunhalas sötét/történelmi események + párduc
    "007383",  # „keresd meg azt hogy szerbiaban apatinban lattak a fekete parduc ot”
    "005330",  # a fekete párduc útvonala Kiskunhalas → ... → 2025
    "005329",  # parduc lehet tigris is vagy csak leopard és jaguar?
    "005328",  # The black panther set off from Kiskunhalas... (EN)
    "005327",  # ua. + részletes dátumozott észlelés-lista
    "005326",  # ua.
    "005321",  # ua.
    "005320",  # ua.
    "005319",  # ua.
    "005287",  # kutass szeptember utáni észlelésről
    "003755",  # a párduc teljes útvonala (településlista) + black panther
    "003275",  # Kiskunhalason a párducon kívül mikor láttak egzotikus szökött állatot?
    "003274",  # Melanisztikus parduc volt vagy sima leopard? (+ hangzhoui jaguár-szökés)
    "003224",  # I live on Szegedi Road in Kiskunhalas... melanistic black panther (EN)
    "003223",  # ua.
    "003222",  # ua.
    "003221",  # ua.
    "002701",  # kiskunhalas tanya világ, szegedi út, sötét dolgok + párduc
    "002538",  # Neofelis nebulosa lehet fekete? + a halasi párduc faja
    "002443",  # Panthera pardus japonensis lehet fekete?
    "002956",  # perzsa leopárd (Panthera pardus tulliana) genetika/melanizmus
    "002966",  # black Persian/Caucasian leopard keresése
    "002967",  # kaukázusi/perzsa leopárd Magyarországon
    "002918",  # melanizmus-ellenőrzés (BLACK_MORPH_MELANISM_CHECK)
    "002919",  # ua.
    "001996",  # Ázsia: mely országokban élnek természetesen leopárdok?
    "001010",  # leopárd alfajok / országlista (Panthera pardus)
    "000314",  # nagymacskák + „Leopard jaguár hibrid?” + „Leopárd magyarországon szabadon 2020 előtt”
    "000315",  # nagymacskák felsorolása (hópárduc, ködfoltos párduc...)
    "006367",  # az összes nagymacska faj
    "005873",  # a párducok milyen fajok is lehetnek
    "003310",  # egy ügynök fekete párduc/leopárd kutatásának értékelése
]

# T2 – KONTEXTUS: a párduc mint „jel” a személyes / természetfeletti narratívában
T2 = [
    "007386", "007385", "005458", "005457", "004915", "004914",  # „szia szoval tobb ai chatbe...” (6× újrakezdve)
    "004749", "004748",            # Antikrisztus-kutatás, benne a fekete párduc mint 1. jel
    "003792",                      # élettörténet + párduc + szerbiai apatin
    "004815",                      # 5402 mellekút fehér őz + kiskunhalasi fekete párduc
]

# T3 – ÉRINTŐLEGES: nagymacskák általában, vagy a párduc csak példaként
T3 = [
    "008186", "008179", "008178", "008177",  # saját LLM építése – példa: „Kiskunhalason láttak párducot 2021ben”
    "001721",  # cápa/orca → leopárd, emberre legveszélyesebb nagymacska
    "002315",  # „medveölő” kutyák vs. nagymacskák
    "000285",  # orka utáni apex predátor
    "003738",  # ultimate apex predator
    "006104",  # mongolok (érintőleges)
]

TIERS = [("T1", "KÖZPONTI – a fekete párduc kutatása", T1),
         ("T2", "KONTEXTUS – a párduc mint jel / személyes narratíva", T2),
         ("T3", "ÉRINTŐLEGES – nagymacskák általában, példaként említve", T3)]

# Hamis találatok (kulcsszó egyezett, de NEM párduc)
FALSE_POSITIVES = [
    ("010073", "Az etalon női pankrátor", "Jaguar Yokota – pankrátor"),
    ("008582", "UI/UX design honlapok", "Panther – kiberbiztonsági platform"),
    ("008423", "LLM architektúra (Muon/MoE)", "JAGUAR Muon – optimalizáló algoritmus"),
    ("006104", "Mongol birodalom", "azték jaguár-harcosok"),
    ("003789", "Hajfestés (szőkítő+oxi)", "„párducmintás” hajszín"),
    ("004056", "LLM modell-lista", "a mistral-large belső kódneve: 'jaguar'"),
    ("003093", "Autó (BMW E60 alternatíva)", "Jaguar XF autó"),
    ("002483", "Pankrátor-fizetések", "Jacksonville Jaguars – NFL csapat"),
    ("000991", "„stop playin with 'em riot”", "PinkPantheress – előadó"),
    ("000177", "Storm xmen", "Black Panther – Marvel képregény"),
    ("000271", "Veszélyes szerződések (cikk)", "„a leopárd sosem változtatja meg a foltjait”"),
    ("005654", "Perplexity-szerű app", "példa: „Black Panther” = Marvel, nem állat"),
    ("000285", "Apex predátor", "jaguár, általános ökológia"),
]

# A párduc-témát hordozó kulcsszavak
KW = re.compile(r"p[aá]rduc|panther|pantera|leopard|leop[aá]rd|jagu[aá]r|melanis|melanistic|nagymacska|nagy macska", re.I)


# ---------------------------------------------------------------------------
# 2. BETÖLTÉS
# ---------------------------------------------------------------------------

def ts(dt):
    """20251019T19:39:45.107336Z -> 2025-10-19 19:39"""
    if not dt:
        return "?"
    for fmt, cut in (("%Y%m%dT%H:%M:%S", 17), ("%Y%m%dT%H:%M", 14)):
        try:
            return datetime.datetime.strptime(dt[:cut], fmt).strftime("%Y-%m-%d %H:%M")
        except Exception:
            continue
    return dt


def load(fid):
    p = os.path.join(SRC, fid + ".json")
    d = json.load(open(p, encoding="utf-8"))
    return d


convs = OrderedDict()   # fid -> dict
for tier_name, tier_label, files in TIERS:
    for fid in files:
        d = load(fid)
        entries = []
        for i, e in enumerate(d.get("entries", [])):
            q = e.get("query") or ""
            a = e.get("answer") or ""
            entries.append({
                "i": i,
                "uuid": e.get("entry_uuid"),
                "at": ts(e.get("created_at")),
                "raw_at": e.get("created_at"),
                "query": q,
                "answer": a,
                "kw_query": sorted(set(m.group(0).lower() for m in KW.finditer(q))),
                "kw_answer": sorted(set(m.group(0).lower() for m in KW.finditer(a))),
                "relevant": bool(KW.search(q) or KW.search(a)),
            })
        convs[fid] = {
            "file": fid + ".json",
            "uuid": d.get("context_uuid"),
            "created": ts(d.get("created_at")),
            "raw_created": d.get("created_at"),
            "updated": ts(d.get("updated_at")),
            "title": (d.get("context_title") or "").strip(),
            "mode": d.get("mode"),
            "tier": tier_name,
            "tier_label": tier_label,
            "entries": entries,
        }

order = sorted(convs.values(), key=lambda c: c["raw_created"] or "")

# ---------------------------------------------------------------------------
# 3. KIMENETI MAPPÁK
# ---------------------------------------------------------------------------
os.makedirs(FULL, exist_ok=True)


def md_escape(t):
    return t


# ---------------------------------------------------------------------------
# 4. TELJES SZÖVEGŰ BESZÉLGETÉS-DUMPOK
# ---------------------------------------------------------------------------
for c in order:
    lines = []
    lines.append(f"# {c['file']} — {c['created']}")
    lines.append("")
    lines.append(f"- **Fájl:** `user_data_export_extracted/conversations_split/{c['file']}`")
    lines.append(f"- **Beszélgetés UUID:** `{c['uuid']}`")
    lines.append(f"- **Létrehozva:** {c['created']}  |  **Utoljára frissítve:** {c['updated']}")
    lines.append(f"- **Mód:** {c['mode']}  |  **Entry-k száma:** {len(c['entries'])}")
    lines.append(f"- **Kategória:** {c['tier']} – {c['tier_label']}")
    lines.append("")
    lines.append("## Eredeti cím / első üzenet (context_title)")
    lines.append("")
    lines.append("```text")
    lines.append(c["title"])
    lines.append("```")
    lines.append("")
    for e in c["entries"]:
        mark = "⭐" if e["kw_query"] else ("·" if e["kw_answer"] else " ")
        lines.append("---")
        lines.append("")
        lines.append(f"### {mark} Entry #{e['i']} — {e['at']}  (`{e['uuid']}`)")
        if e["kw_query"]:
            lines.append(f"*Kulcsszavak a kérdésben:* {', '.join(e['kw_query'])}")
        elif e["kw_answer"]:
            lines.append(f"*Kulcsszavak a válaszban:* {', '.join(e['kw_answer'])}")
        lines.append("")
        lines.append("#### TE (kérdés)")
        lines.append("")
        lines.append("```text")
        lines.append(e["query"])
        lines.append("```")
        lines.append("")
        lines.append("#### Perplexity (válasz)")
        lines.append("")
        lines.append("```text")
        lines.append(e["answer"])
        lines.append("```")
        lines.append("")
    open(os.path.join(FULL, c["file"].replace(".json", ".md")), "w", encoding="utf-8").write("\n".join(lines))

# ---------------------------------------------------------------------------
# 5. IDŐRENDI IDÉZET-GYŰJTEMÉNY (csak a párducos entry-k)
# ---------------------------------------------------------------------------
quotes = []
for c in order:
    for e in c["entries"]:
        if e["relevant"]:
            quotes.append((c, e))
quotes.sort(key=lambda ce: ce[1]["raw_at"] or "")

# ---------------------------------------------------------------------------
# 6. FŐ JELENTÉS
# ---------------------------------------------------------------------------
L = []
w = L.append

w("# 🐆 FEKETE PÁRDUCOK — minden, amit erről írtál")
w("")
w("> A `user_data_export_extracted/conversations_split/` Perplexity-export "
  f"**{len(list(os.walk(SRC)) and [f for f in os.listdir(SRC) if f.endswith('.json')])}** beszélgetéséből "
  f"**{len(convs)}** érintettet gyűjtöttem ki, **{sum(len(c['entries']) for c in convs.values())}** entry-vel.")
w("")
w(f"**Időintervallum:** {order[0]['created']} → {order[-1]['created']}")
w("")
w("---")
w("")
w("## 1. Miről van szó röviden")
w("")
w("Egyetlen, éveken át húzódó nyomozás ez, nem szórványos említések:")
w("")
w("1. **2021 decemberében Kiskunhalason (Szegedi út / tanyavilág) fekete párducot vett fel egy kamera** "
  "— a te saját állításod szerint **a házatoktól néhány száz méterre**, és nem is a kamera volt az első: "
  "**a szomszédod / keresztapád látta először**, ő jelentette, ezért nézték meg a szomszéd kameráját.")
w("2. Utána **Kiskunfélegyháza / Bugac térségében birkanyájat mészároltak le** — te ezt időben és módszerben "
  "egybefüggőnek tartod a párduccal (koponyatörés hiánya, szájra szorított harapás = fulladás, "
  "sértetlen kerítés átugrása, túlölés/surplus killing).")
w("3. **Kb. 9–10 hónappal később Szerbiában, Apatinban (Banja Junaković)** is filmeztek fekete párducot — "
  "ezt **te magad fedezted fel**, és szerinted senki nem kötötte össze a két esetet.")
w("4. Innen egy **nemzetközi útvonalat** rekonstruáltál: Kiskunhalas → Kecskemét → Kiskunfélegyháza → Szolnok → "
  "Kerecsend → Ballószög → Kengyel → Tiszatenyő → Újszász → Apatin → Banja Junaković → Feketić → Vrbas → Zmajevo → "
  "Shumen-plató → Dupnitsa → Kraynitsi → Giurgiu → Puieni → Istru → Armentières → Solothurn.")
w("5. Végig az **azonosításon** dolgoztál: leopárd vs. jaguár vs. ködfoltos párduc, melanisztikus-e, "
  "melyik alfaj (perzsa/kaukázusi = *Panthera pardus tulliana*, japán = *P. p. japonensis*, "
  "*Neofelis nebulosa*, sőt *Panthera gombaszoegensis*), és **honnan jött** "
  "(szökött fogságban tartott egyed / illegális állatpiac / Kínából – pl. a hangzhoui három szökött jaguár).")
w("")
w("---")
w("")
w("## 2. Kategóriák")
w("")
for tier_name, tier_label, files in TIERS:
    cs = [c for c in order if c["tier"] == tier_name]
    w(f"### {tier_name} — {tier_label} ({len(cs)} beszélgetés)")
    w("")
    w("| Dátum | Fájl | UUID | Téma | Párducos entry |")
    w("|---|---|---|---|---|")
    for c in cs:
        n = sum(1 for e in c["entries"] if e["relevant"])
        w(f"| {c['created']} | [`{c['file']}`](teljes_szovegek/{c['file'].replace('.json','.md')}) | `{c['uuid'][:8]}` | "
          f"{c['title'][:70].replace(chr(10),' ').replace('|','/')} | {n}/{len(c['entries'])} |")
    w("")
w("---")
w("")
w("## 3. IDŐREND — minden párducra vonatkozó részlet, szó szerint")
w("")
w("A ⭐ azt jelöli, ha a kulcsszó a **te saját szövegedben** van; "
  "a · azt, ha csak a Perplexity válaszában fordult elő (ilyenkor a kérdésed a kontextus miatt szerepel).")
w("")
cur_date = None
for c, e in quotes:
    d = (e["at"] or "")[:10]
    if d != cur_date:
        cur_date = d
        w("")
        w(f"### 📅 {d}")
        w("")
    mark = "⭐" if e["kw_query"] else "·"
    w(f"#### {mark} {e['at']} — [`{c['file']}`](teljes_szovegek/{c['file'].replace('.json','.md')}) · entry #{e['i']}")
    w("")
    w("**TE:**")
    w("")
    w("```text")
    w(e["query"])
    w("```")
    w("")
    w(f"<details><summary>Perplexity válasza ({len(e['answer'])} karakter)</summary>")
    w("")
    w("```text")
    w(e["answer"])
    w("```")
    w("")
    w("</details>")
    w("")
w("")
w("---")
w("")
w("## 4. Témakörök szerint")
w("")

THEMES = [
    ("A személyes élmény – „itt volt a házunktól pár száz méterre”",
     lambda q: re.search(r"hazunktol|hazunk kozel|szomszed|keresztapam|par szaz meter", q, re.I)),
    ("A bizonyíték – kamera, szőr, ürülék, lábnyom",
     lambda q: re.search(r"kamera|terfigyelo|video|szoret|labnyom|szar|ürülék|nyom", q, re.I)),
    ("A Kiskunfélegyháza–Bugac-i birkák (túlölés, fulladás)",
     lambda q: re.search(r"birka|nyaj|tulol|fullad|surplus|koponya", q, re.I)),
    ("Az útvonal / vándorlás",
     lambda q: re.search(r"utvonal|indult|vandor|Apatin|Kecskemet|Szolnok|Dupnitsa|Feketic|Vrbas", q, re.I)),
    ("Fajazonosítás: leopárd vs. jaguár vs. ködfoltos",
     lambda q: re.search(r"leopard|jaguar|nebulosa|japonensis|tulliana|gombaszoegensis|melanis", q, re.I)),
    ("Honnan jött? szökés / illegális kereskedelem / Kína",
     lambda q: re.search(r"szokot|szokott|illegalis|allatpiac|kin|hangz|tartotta|fogsag", q, re.I)),
    ("Magyarországi / Kárpát-medencei leopárd a múltban",
     lambda q: re.search(r"magyarorszagon|karpat|1900|1800|2020 elott|szabadon", q, re.I)),
    ("A párduc mint „jel” az átok / természetfeletti narratívában",
     lambda q: re.search(r"atok|termeszet felett|termeszetfeletti|jel|sotet|boszorkany", q, re.I)),
]
for label, pred in THEMES:
    hits = [(c, e) for c, e in quotes if pred(e["query"])]
    if not hits:
        continue
    w(f"### {label}  ({len(hits)} entry)")
    w("")
    for c, e in hits:
        w(f"- **{e['at']}** — [`{c['file']}`](teljes_szovegek/{c['file'].replace('.json','.md')}) "
          f"entry #{e['i']}: {e['query'][:220].replace(chr(10),' ')}")
    w("")

w("")
w("---")
w("")
w("## 5. Hamis találatok (kulcsszó egyezett, de NEM párduc)")
w("")
w("| Fájl | Eredeti téma | A téves egyezés |")
w("|---|---|---|")
for fid, topic, why in FALSE_POSITIVES:
    w(f"| `{fid}.json` | {topic} | {why} |")
w("")
w("---")
w("")
w("## 6. Hivatkozás-jegyzék: fájl ↔ UUID ↔ dátum")
w("")
for c in order:
    w(f"- `{c['file']}` · `{c['uuid']}` · {c['created']} · {c['tier']} · "
      f"[teljes szöveg](teljes_szovegek/{c['file'].replace('.json','.md')})")
w("")
w("---")
w("")
w("*Generálta: `tools/parduc_kereso.py`. Minden idézet szó szerint, csonkítás nélkül származik az exportból.*")

open(os.path.join(OUT, "FEKETE_PARDUC_MINDEN.md"), "w", encoding="utf-8").write("\n".join(L))

# ---------------------------------------------------------------------------
# 7. INDEX JSON
# ---------------------------------------------------------------------------
index = {
    "generated": datetime.datetime.utcnow().isoformat() + "Z",
    "source": "user_data_export_extracted/conversations_split",
    "total_conversations_in_export": len([f for f in os.listdir(SRC) if f.endswith(".json")]),
    "matched_conversations": len(convs),
    "conversations": [
        {
            "file": c["file"], "uuid": c["uuid"], "created": c["created"],
            "updated": c["updated"], "title": c["title"], "tier": c["tier"],
            "tier_label": c["tier_label"], "mode": c["mode"],
            "full_text": f"teljes_szovegek/{c['file'].replace('.json','.md')}",
            "entries": [
                {"i": e["i"], "at": e["at"], "uuid": e["uuid"],
                 "query": e["query"], "answer": e["answer"],
                 "kw_query": e["kw_query"], "kw_answer": e["kw_answer"]}
                for e in c["entries"]
            ],
        }
        for c in order
    ],
    "false_positives": [{"file": f + ".json", "topic": t, "why": why} for f, t, why in FALSE_POSITIVES],
}
json.dump(index, open(os.path.join(OUT, "parduc_index.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

# ---------------------------------------------------------------------------
# 8. KERESHETŐ HTML
# ---------------------------------------------------------------------------
data = []
for c in order:
    for e in c["entries"]:
        data.append({
            "f": c["file"].replace(".json", ""), "u": c["uuid"], "d": e["at"],
            "i": e["i"], "q": e["query"], "a": e["answer"], "t": c["tier"],
            "star": 1 if e["kw_query"] else 0,
        })

HTML = """<!DOCTYPE html>
<html lang="hu"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Fekete párducok – keresés</title>
<style>
:root{--bg:#0d0d10;--fg:#e8e6e3;--dim:#8a8880;--acc:#e0a53c;--card:#16161b;--line:#2a2a32}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
header{position:sticky;top:0;background:#0d0d10ee;backdrop-filter:blur(8px);border-bottom:1px solid var(--line);padding:14px 18px;z-index:10}
input{width:100%;padding:12px 14px;font-size:16px;border-radius:10px;border:1px solid var(--line);background:var(--card);color:var(--fg)}
input:focus{outline:none;border-color:var(--acc)}
.meta{color:var(--dim);font-size:13px;margin-top:8px;display:flex;gap:14px;flex-wrap:wrap}
main{padding:14px 18px 80px}
.hit{border:1px solid var(--line);border-radius:12px;background:var(--card);margin:12px 0;overflow:hidden}
.hit>h3{margin:0;padding:11px 14px;font-size:13px;font-weight:600;color:var(--dim);display:flex;gap:10px;align-items:center;flex-wrap:wrap;cursor:pointer;background:#1b1b21}
.hit>h3 .t1{color:var(--acc)}
.body{padding:0 14px 14px;display:none}
.hit.open .body{display:block}
.q,.a{white-space:pre-wrap;word-break:break-word;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:13px;line-height:1.5}
.q{background:#111116;border-left:3px solid var(--acc);padding:10px 12px;border-radius:0 8px 8px 0;max-height:19em;overflow:auto}
.a{background:#101014;border-left:3px solid #33333d;padding:10px 12px;border-radius:0 8px 8px 0;max-height:22em;overflow:auto;color:#cfcdc8}
h4{margin:14px 0 6px;font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:var(--dim)}
mark{background:#e0a53c55;color:#fff;border-radius:3px;padding:0 2px}
.star{color:var(--acc)}
</style></head><body>
<header>
<input id="s" placeholder="Keresés… (pl. párduc, Apatin, melanisztikus, Kiskunfélegyháza, jaguár)">
<div class="meta"><span id="cnt"></span><span>⭐ = a kulcsszó a TE szövegedben van</span><span>T1 központi · T2 kontextus · T3 érintőleges</span></div>
</header>
<main id="m"></main>
<script>
const DATA=__DATA__;
const m=document.getElementById('m'),s=document.getElementById('s'),cnt=document.getElementById('cnt');
const esc=t=>t.replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
function hl(t,re){return re?esc(t).replace(re,g=>'<mark>'+g+'</mark>'):esc(t)}
function run(){
  const v=s.value.trim();
  let re=null;
  if(v){try{re=new RegExp('('+v.replace(/[.*+?^${}()|[\\]\\\\]/g,'\\\\$&')+')','gi')}catch(e){re=null}}
  let n=0;let out='';
  const txt=v.toLowerCase();
  for(const d of DATA){
    if(v && !((d.q||'').toLowerCase().includes(txt)||(d.a||'').toLowerCase().includes(txt))) continue;
    n++;
    out+=`<div class="hit"><h3 onclick="this.parentNode.classList.toggle('open')">
      <span>${d.star?'⭐':'·'}</span><span class="t${d.t.slice(1)}">${d.t}</span>
      <span>${esc(d.d)}</span><span>${esc(d.f)} · entry #${d.i}</span>
      <span style="margin-left:auto">kattints a kinyitáshoz</span></h3>
      <div class="body"><h4>TE</h4><div class="q">${hl(d.q,re)}</div>
      <h4>Perplexity</h4><div class="a">${hl(d.a,re)}</div></div></div>`;
    if(n>400){out+='<p style="color:#8a8880">…több találat, szűkíts a kereséssel</p>';break}
  }
  m.innerHTML=out;cnt.textContent=n+' találat ('+DATA.length+' entry-ből)';
}
s.addEventListener('input',run);run();
</script></body></html>"""
HTML = HTML.replace("__DATA__", json.dumps(data, ensure_ascii=False))
open(os.path.join(OUT, "parduc_kereses.html"), "w", encoding="utf-8").write(HTML)

print(f"KÉSZ -> {OUT}")
print(f"  FEKETE_PARDUC_MINDEN.md  {os.path.getsize(os.path.join(OUT,'FEKETE_PARDUC_MINDEN.md'))//1024} KB")
print(f"  parduc_index.json        {os.path.getsize(os.path.join(OUT,'parduc_index.json'))//1024} KB")
print(f"  parduc_kereses.html      {os.path.getsize(os.path.join(OUT,'parduc_kereses.html'))//1024} KB")
print(f"  teljes_szovegek/         {len(order)} fájl")
print(f"  érintett beszélgetés: {len(convs)}, párducos entry: {len(quotes)}")
