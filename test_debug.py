"""
test_debug.py — Diagnostic pour la version Groq
Commande : python test_debug.py
"""
import os
import json

print("=" * 60)
print("DIAGNOSTIC FACTCHECKER (Groq)")
print("=" * 60)

# 1. Vérifier la clé Groq
api_key = os.environ.get("GROQ_API_KEY", "")
if not api_key:
    print("❌ ERREUR : GROQ_API_KEY non définie !")
    print("   1. Va sur https://console.groq.com")
    print("   2. Crée un compte gratuit")
    print("   3. Clique sur 'API Keys' → 'Create API Key'")
    print("   4. Tape dans le terminal PowerShell :")
    print('      $env:GROQ_API_KEY="gsk_TACLÉ"')
    exit(1)
else:
    print(f"✅ Clé Groq trouvée : {api_key[:20]}...")

# 2. Tester la connexion Groq
print("\n--- Test connexion Groq ---")
try:
    from groq import Groq
    client = Groq()
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=50,
        messages=[{"role": "user", "content": "Réponds juste: OK"}],
    )
    print(f"✅ Groq répond : {response.choices[0].message.content}")
except Exception as e:
    print(f"❌ ERREUR Groq : {e}")
    exit(1)

# 3. Tester l'extraction de claims
print("\n--- Test extraction des affirmations ---")
try:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=300,
        messages=[
            {"role": "system", "content": "Réponds TOUJOURS en JSON valide uniquement."},
            {"role": "user", "content": 'Extrais les affirmations de: "Jeff Bezos a fondé Amazon en 1994. Le CA dépasse 500 milliards."\nJSON: {"claims": ["...", "..."]}'}
        ],
    )
    raw = response.choices[0].message.content
    print(f"Réponse : {raw}")
    data = json.loads(raw)
    print(f"✅ Claims : {data['claims']}")
except Exception as e:
    print(f"❌ ERREUR : {e}")

# 4. Tester l'évaluation
print("\n--- Test évaluation d'une affirmation ---")
try:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=150,
        messages=[
            {"role": "system", "content": "Réponds TOUJOURS en JSON valide uniquement."},
            {"role": "user", "content": 'Évalue: "Jeff Bezos a fondé Amazon en 1994 à Seattle"\nJSON sur une ligne: {"score": 90, "verdict": "Vérifié", "explanation": "raison"}'}
        ],
    )
    raw = response.choices[0].message.content
    print(f"Réponse : {raw}")
    data = json.loads(raw)
    print(f"✅ Score: {data['score']}% | Verdict: {data['verdict']}")
except Exception as e:
    print(f"❌ ERREUR : {e}")

# 5. Test Wikipedia
print("\n--- Test Wikipedia ---")
try:
    import requests as req
    resp = req.get(
        "https://fr.wikipedia.org/w/api.php",
        params={"action": "query", "list": "search", "srsearch": "Amazon Jeff Bezos", "srlimit": 2, "format": "json"},
        timeout=6
    )
    results = resp.json().get("query", {}).get("search", [])
    print(f"✅ Wikipedia : {results[0]['title'] if results else 'aucun résultat'}")
except Exception as e:
    print(f"❌ ERREUR Wikipedia : {e}")

print("\n" + "=" * 60)
print("✅ DIAGNOSTIC TERMINÉ — Tout est OK, lance : python app.py")
print("=" * 60)
