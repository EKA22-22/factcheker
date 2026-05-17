"""
fact_checker.py — VERSION RAPIDE + SOURCES COMPLÈTES
 
Optimisations de vitesse :
- Toutes les affirmations sont vérifiées EN PARALLÈLE (ThreadPoolExecutor)
- Wikipedia FR + EN et Google News sont recherchés en parallèle pour chaque claim
- Résumés Wikipedia récupérés uniquement pour l'article le plus pertinent
- Timeout réduit à 5s pour ne pas bloquer

Qualité :
- Wikipedia et Google News toujours affichés dans les sources
- Groq utilise sa connaissance + résumés complets Wikipedia
- Prompt optimisé pour éviter les faux négatifs
"""

import re
import json
import requests
import feedparser
from groq import Groq
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Tuple


# ─────────────────────────────────────────────
# Utilitaires
# ─────────────────────────────────────────────

def safe_parse_json(text: str) -> dict:
    """Parse JSON robuste avec 3 fallbacks."""
    text = re.sub(r"```json\s*|\s*```|```", "", text).strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    match = re.search(r'\{.*?\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except Exception:
            pass
    result = {}
    m = re.search(r'"score"\s*:\s*(\d+)', text)
    if m: result["score"] = int(m.group(1))
    m = re.search(r'"verdict"\s*:\s*"([^"]+)"', text)
    if m: result["verdict"] = m.group(1)
    m = re.search(r'"explanation"\s*:\s*"([^"]+)"', text)
    if m: result["explanation"] = m.group(1)
    return result


# ─────────────────────────────────────────────
# Recherche Wikipedia
# ─────────────────────────────────────────────

WIKI_HEADERS = {
    "User-Agent": "FactCheckerApp/1.0 (educational; contact@factchecker.local)",
    "Accept": "application/json",
}

def wiki_search(query: str, lang: str = "fr", max_results: int = 2) -> List[Dict]:
    """Recherche Wikipedia avec User-Agent valide."""
    params = {
        "action": "query", "list": "search",
        "srsearch": query, "srlimit": max_results,
        "format": "json", "utf8": 1,
        "srprop": "snippet",
    }
    try:
        resp = requests.get(
            f"https://{lang}.wikipedia.org/w/api.php",
            params=params, headers=WIKI_HEADERS, timeout=5
        )
        items = resp.json().get("query", {}).get("search", [])
        results = []
        for item in items:
            title = item["title"]
            snippet = re.sub(r"<[^>]+>", "", item.get("snippet", ""))
            results.append({
                "title": title,
                "snippet": snippet,
                "url": f"https://{lang}.wikipedia.org/wiki/{title.replace(' ', '_')}",
                "source": f"Wikipedia {lang.upper()}",
            })
        print(f"  [Wiki {lang.upper()}] {len(results)} résultat(s) pour '{query[:35]}'")
        return results
    except Exception as e:
        print(f"  [Wiki {lang.upper()}] ERREUR : {e}")
        return []


def wiki_summary(title: str, lang: str = "fr") -> str:
    """Récupère le résumé complet d'un article Wikipedia."""
    try:
        url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{requests.utils.quote(title)}"
        resp = requests.get(url, headers=WIKI_HEADERS, timeout=5)
        extract = resp.json().get("extract", "")
        print(f"  [Wiki résumé] '{title}' → {len(extract)} car.")
        return extract[:1200]
    except Exception:
        return ""


# ─────────────────────────────────────────────
# Recherche Google News
# ─────────────────────────────────────────────

def news_search(query: str, max_results: int = 3) -> List[Dict]:
    """Recherche Google News via RSS."""
    try:
        url = f"https://news.google.com/rss/search?q={requests.utils.quote(query)}&hl=fr&gl=FR&ceid=FR:fr"
        feed = feedparser.parse(url)
        results = []
        for entry in feed.entries[:max_results]:
            results.append({
                "title": entry.get("title", ""),
                "snippet": entry.get("summary", "")[:250],
                "url": entry.get("link", ""),
                "source": "Google News",
            })
        print(f"  [News] {len(results)} article(s) pour '{query[:35]}'")
        return results
    except Exception as e:
        print(f"  [News] ERREUR : {e}")
        return []


# ─────────────────────────────────────────────
# Moteur principal
# ─────────────────────────────────────────────

class FactChecker:
    MODEL = "llama-3.3-70b-versatile"

    def __init__(self):
        self.client = Groq()

    def _groq(self, prompt: str, max_tokens: int = 400) -> str:
        """Appel Groq avec system prompt strict JSON."""
        try:
            r = self.client.chat.completions.create(
                model=self.MODEL,
                max_tokens=max_tokens,
                temperature=0.1,
                messages=[
                    {"role": "system", "content": "Tu es un fact-checker expert. Réponds UNIQUEMENT en JSON valide, sans texte avant ni après, sans balises markdown."},
                    {"role": "user", "content": prompt},
                ],
            )
            return r.choices[0].message.content.strip()
        except Exception as e:
            print(f"  [Groq ERREUR] {e}")
            return "{}"

    # ── Extraction des affirmations ──────────────────────────

    def extract_claims(self, text: str) -> List[str]:
        """Extrait jusqu'à 8 affirmations vérifiables depuis le texte."""
        # Limiter à 4000 caractères pour la vitesse
        prompt = f"""Extrais les affirmations factuelles vérifiables de ce texte (chiffres, dates, statistiques, noms + faits précis).

TEXTE :
{text[:4000]}

JSON uniquement :
{{"claims": ["affirmation 1", "affirmation 2", "affirmation 3"]}}

Maximum 8 affirmations."""

        raw = self._groq(prompt, max_tokens=500)
        data = safe_parse_json(raw)
        claims = [c for c in data.get("claims", []) if isinstance(c, str) and len(c) > 10]
        print(f"\n[CLAIMS] {len(claims)} affirmation(s) extraite(s)")
        for i, c in enumerate(claims, 1):
            print(f"  {i}. {c}")
        return claims[:8]

    # ── Vérification d'une affirmation ──────────────────────

    def _fetch_sources(self, claim: str) -> Tuple[List, List, List, List]:
        """
        Récupère Wikipedia FR, Wikipedia EN, News EN PARALLÈLE.
        Retourne (wiki_fr, wiki_en, news, summaries)
        """
        with ThreadPoolExecutor(max_workers=4) as ex:
            f_wfr  = ex.submit(wiki_search, claim, "fr", 2)
            f_wen  = ex.submit(wiki_search, claim, "en", 2)
            f_news = ex.submit(news_search, claim, 3)
            
            wiki_fr = f_wfr.result()
            wiki_en = f_wen.result()
            news    = f_news.result()

        # Résumés Wikipedia (en parallèle aussi)
        to_summarize = []
        if wiki_fr: to_summarize.append((wiki_fr[0]["title"], "fr"))
        if wiki_en: to_summarize.append((wiki_en[0]["title"], "en"))

        summaries = []
        if to_summarize:
            with ThreadPoolExecutor(max_workers=2) as ex:
                futures = {ex.submit(wiki_summary, t, l): (t, l) for t, l in to_summarize}
                for f in as_completed(futures):
                    title, lang = futures[f]
                    s = f.result()
                    if s:
                        summaries.append(f"[Wikipedia {lang.upper()} — {title}]\n{s}")

        return wiki_fr, wiki_en, news, summaries

    def verify_claim(self, claim: str) -> Dict[str, Any]:
        """Vérifie une affirmation. Wikipedia + News toujours affichés."""
        print(f"\n[VERIFY] {claim[:60]}")

        wiki_fr, wiki_en, news, summaries = self._fetch_sources(claim)

        # Contexte pour Groq
        wiki_ctx = "\n\n".join(summaries) if summaries else "Aucun résumé Wikipedia disponible."
        news_ctx = ""
        for n in news:
            news_ctx += f"• {n['title']} — {n['snippet'][:200]}\n"
        if not news_ctx:
            news_ctx = "Aucun article de presse trouvé."

        prompt = f"""Tu es un fact-checker rigoureux.

AFFIRMATION : "{claim}"

WIKIPEDIA (résumés encyclopédiques fiables) :
{wiki_ctx}

GOOGLE NEWS (presse récente) :
{news_ctx}

RÈGLES :
1. Utilise EN PRIORITÉ ta propre connaissance factuelle
2. Les résumés Wikipedia sont fiables pour les faits établis
3. Google News est fiable pour les événements récents
4. Si Wikipedia et News se contredisent → préfère ta connaissance + News pour les faits récents
5. Un snippet court ou hors contexte NE suffit PAS à invalider un fait connu
6. Ne marque JAMAIS "Faux" un fait que tu sais être vrai

JSON sur une seule ligne :
{{"score": 85, "verdict": "Vérifié", "explanation": "Explication précise en 1-2 phrases."}}

Barème : 85-100=confirmé, 65-84=probable, 45-64=incertain, 25-44=douteux, 0-24=faux
Verdict : exactement un de → Vérifié, Probable, Indéterminé, Trompeur, Faux"""

        raw = self._groq(prompt, max_tokens=250)
        print(f"  [Groq] {raw[:150]}")

        data    = safe_parse_json(raw)
        score   = data.get("score", None)
        verdict = data.get("verdict", None)
        expl    = data.get("explanation", "")

        if score is None:
            m = re.search(r'\b(\d{1,3})\b', raw)
            score = int(m.group(1)) if m else 50
        score = max(0, min(100, int(score)))

        valid = ["Vérifié", "Probable", "Indéterminé", "Trompeur", "Faux"]
        if verdict not in valid:
            if score >= 75: verdict = "Vérifié"
            elif score >= 55: verdict = "Probable"
            elif score >= 35: verdict = "Indéterminé"
            elif score >= 20: verdict = "Trompeur"
            else: verdict = "Faux"

        # ── Construire les sources affichées ─────────────────
        # Garantir TOUJOURS au moins 1 Wikipedia + 1 News
        display = []

        # Wikipedia FR en premier
        for s in wiki_fr[:1]:
            display.append({"title": s["title"], "url": s["url"], "source": s["source"]})
        # Wikipedia EN
        for s in wiki_en[:1]:
            display.append({"title": s["title"], "url": s["url"], "source": s["source"]})
        # Google News
        for s in news[:2]:
            display.append({"title": s["title"], "url": s["url"], "source": s["source"]})

        # Fallback Wikipedia si vide
        if not any("Wikipedia" in s["source"] for s in display):
            q = requests.utils.quote(claim[:60])
            display.insert(0, {
                "title": f"Rechercher sur Wikipedia : {claim[:45]}...",
                "url": f"https://fr.wikipedia.org/w/index.php?search={q}",
                "source": "Wikipedia FR",
            })

        # Fallback News si vide
        if not any("News" in s["source"] for s in display):
            q = requests.utils.quote(claim[:60])
            display.append({
                "title": f"Rechercher dans l'actualité : {claim[:45]}...",
                "url": f"https://news.google.com/search?q={q}&hl=fr",
                "source": "Google News",
            })

        print(f"  → {score}% | {verdict} | sources: {[s['source'] for s in display]}")
        return {"text": claim, "score": score, "verdict": verdict, "explanation": expl, "sources": display}

    # ── Analyse complète ────────────────────────────────────

    def calculate_global_score(self, results: List[Dict]) -> Dict:
        if not results:
            return {"score": 50, "verdict": "Indéterminé", "color": "amber", "summary": "Aucune affirmation analysée."}
        scores = [r["score"] for r in results]
        avg = sum(scores) / len(scores)
        penalty = sum(8 for s in scores if s < 25)
        final = max(0, min(100, int(avg - penalty)))
        if final >= 75:   verdict, color = "Fiable", "green"
        elif final >= 55: verdict, color = "Globalement fiable", "teal"
        elif final >= 35: verdict, color = "Douteux", "amber"
        else:             verdict, color = "Non fiable", "red"
        vc = {}
        for r in results:
            vc[r["verdict"]] = vc.get(r["verdict"], 0) + 1
        summary = f"Sur {len(results)} affirmations : " + ", ".join(f"{n} '{v}'" for v, n in vc.items()) + "."
        return {"score": final, "verdict": verdict, "color": color, "summary": summary}

    def analyze(self, text: str) -> Dict[str, Any]:
        """
        Analyse complète — les affirmations sont vérifiées EN PARALLÈLE
        pour réduire le temps d'analyse au maximum.
        """
        import time
        t0 = time.time()
        print(f"\n{'='*55}\n[ANALYSE] {len(text)} caractères\n{'='*55}")

        claims = self.extract_claims(text)
        if not claims:
            return {
                "score": 50, "verdict": "Indéterminé", "color": "amber",
                "summary": "Aucune affirmation factuelle vérifiable détectée. Essayez un texte avec des chiffres, dates ou noms précis.",
                "claims": [],
            }

        # ── VÉRIFICATION PARALLÈLE de toutes les affirmations ──
        # Chaque affirmation est vérifiée dans son propre thread
        # → Temps total ≈ temps d'une seule vérification (au lieu de N × T)
        results = [None] * len(claims)
        with ThreadPoolExecutor(max_workers=min(len(claims), 6)) as ex:
            future_to_idx = {ex.submit(self.verify_claim, claim): i for i, claim in enumerate(claims[:8])}
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    results[idx] = future.result()
                except Exception as e:
                    print(f"  [ERREUR claim {idx}] {e}")
                    results[idx] = {
                        "text": claims[idx], "score": 50, "verdict": "Indéterminé",
                        "explanation": "Erreur lors de l'analyse.", "sources": [],
                    }

        results = [r for r in results if r is not None]
        global_result = self.calculate_global_score(results)

        elapsed = time.time() - t0
        print(f"\n[RÉSULTAT] {global_result['score']}% — {global_result['verdict']} ({elapsed:.1f}s)")

        return {
            "score": global_result["score"],
            "verdict": global_result["verdict"],
            "color": global_result["color"],
            "summary": global_result["summary"],
            "claims": results,
            "total_claims": len(results),
            "analysis_time": round(elapsed, 1),
        }
