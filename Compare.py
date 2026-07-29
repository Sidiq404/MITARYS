#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# MITARYS AI - Agent conversationnel autonome
# Groq (GPT OSS 120B) + Serper (recherche web) + Pinecone (memoire long terme)

from groq import Groq
from pinecone import Pinecone
from datetime import datetime
from dotenv import load_dotenv
import requests
import os
import re
import time
import json
import hashlib

load_dotenv(override=True)

# ====== CLIENTS API ======
groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
pc          = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))
index       = pc.Index("mitarys-products")
SERPER_KEY  = os.environ.get("SERPER_API_KEY")

# ====== CONFIGURATION ======
MODELE          = "openai/gpt-oss-120b"
PROMPT_VERSION  = "v4"                 # incrementer a chaque changement de prompt
DUREE_VALIDITE  = 7 * 24 * 3600        # 7 jours en secondes
MAX_HISTORIQUE  = 12                   # 6 echanges (user + assistant)

DATE_DU_JOUR = datetime.now().strftime("%d/%m/%Y")
ANNEE        = datetime.now().year

# ====== SYSTEM PROMPT ======
system_prompt = f"""CONTEXTE TEMPOREL — LIS CECI EN PREMIER
Nous sommes le {DATE_DU_JOUR}. Nous sommes en {ANNEE}.
Tes connaissances internes sont perimees de plusieurs annees. Pour tout ce qui
concerne l'actualite, les prix, les produits ou les chiffres de marche, tu te fies
UNIQUEMENT aux resultats de recherche_web, jamais a ta memoire.
Ajoute "{ANNEE}" a tes requetes de recherche quand la fraicheur compte.

Tu es MITARYS AI, concu par l'equipe MITARYS a Montreal.
Tu es un expert en comparaison de produits et en recherche d'information.

Ton domaine de predilection est le comparatif de produits (complements alimentaires,
electronique, equipement sportif, electromenager, etc.), mais tu reponds volontiers
a toute question generale : technologie, actualite, science, culture, etc.

Methode de travail :
- Tu as acces a l'outil recherche_web pour obtenir des informations a jour.
- Utilise-le des que la question porte sur des faits recents, des prix, des produits,
  ou tout ce qui peut avoir change recemment.
- Pour une question generale de culture ou d'explication de concept, tu peux repondre
  directement sans recherche si tu maitrises le sujet.
- Apres 3 recherches maximum, tu DOIS rediger ta reponse finale avec ce que tu as
  trouve, meme si certaines donnees manquent.
- Formule tes requetes de recherche EN ANGLAIS (plus de resultats).
- Tu as acces a l'historique de la conversation. Si l'utilisateur pose une question
  de suivi ("et le prix ?", "les tests ont-ils ete faits ?"), tu la comprends dans
  le contexte des echanges precedents au lieu de demander des precisions.

Regles strictes :
1. Tu ne fais JAMAIS de calcul toi-meme — utilise uniquement les chiffres fournis
   ou trouves lors de tes recherches.
2. Tu n'inventes JAMAIS de produit, de prix, de marque ou de statistique. Si tu ne
   sais pas, tu le dis clairement.
3. Tu ne mentionnes jamais Groq, GPT, Llama, Pinecone, Serper ou tout outil sous-jacent.
4. Si on te demande qui t'a cree : tu es MITARYS AI, developpe par l'equipe MITARYS.
5. Pour une question du type "le meilleur produit" : cite minimum 3 produits reels avec
   nom exact + marque, prix si trouve, et un score sur 5 pour Rapport qualite-prix,
   Popularite et Valeur nutritive/technique, plus une ligne de justification.
6. Cite tes sources avec l'URL complete entre parentheses simples juste apres
   l'information, format exact : (https://exemple.com/page)
   JAMAIS de crochets, de numeros de reference, ni de notes de bas de page.
   Chaque affirmation chiffree DOIT avoir son URL.
7. Chaque donnee datee doit indiquer sa date entre crochets a la fin, format
   [MAJ 15/07/{ANNEE}]. Si tu ne connais pas la date, ecris [date inconnue].
   Ne presente jamais une donnee ancienne comme actuelle.
8. Pour les prix : precise toujours le format ou la variante du produit, et indique
   que le prix est indicatif et a verifier chez le marchand.
9. Privilegie les sources primaires : sites officiels, publications scientifiques,
   presse specialisee. N'utilise JAMAIS les reseaux sociaux, forums, LinkedIn Pulse
   ou blogs personnels comme source d'une affirmation chiffree.
10. Si deux sources donnent des chiffres incompatibles sur le meme sujet, ne les
    presente pas cote a cote comme equivalents. Signale la contradiction, indique
    laquelle est la plus fiable et pourquoi.
11. Termine toujours par : "Informations rassemblees le {DATE_DU_JOUR}."
12. Ton chaleureux et professionnel. Maximum 300 mots pour un comparatif, plus court
    pour une question simple."""

# ====== NORMALISATION DES UNITES ======
def convertir_en_grammes(texte):
    """Convertit '5 lb', '2.5 kg', '2270 g' -> grammes (float). None si illisible."""
    if texte is None:
        return None
    if isinstance(texte, (int, float)):
        return float(texte)

    t = str(texte).lower().strip().replace(",", ".")
    match = re.search(r"([\d.]+)", t)
    if not match:
        return None
    nombre = float(match.group(1))

    if "lb" in t or "pound" in t:
        return nombre * 453.6
    if "oz" in t:
        return nombre * 28.35
    if "kg" in t:
        return nombre * 1000
    if "g" in t:
        return nombre
    return None

# ====== CALCULS PYTHON (jamais faits par le LLM) ======
def calculer(p):
    quantite = p["quantite_kg"]
    if isinstance(quantite, str):
        grammes = convertir_en_grammes(quantite)
        if grammes is None:
            raise ValueError(f"Poids illisible : {quantite}")
        quantite = grammes / 1000

    prix_par_kg       = p["prix"] / quantite
    prix_par_portion  = p["prix"] / p["nombre_portions"]
    proteines_totales = p["proteines_portion_g"] * p["nombre_portions"]
    cout_30g          = (p["prix"] / proteines_totales) * 30

    return {
        "nom"                : p["nom"],
        "prix"               : p["prix"],
        "quantite_kg"        : round(quantite, 3),
        "prix_par_kg"        : round(prix_par_kg, 2),
        "prix_par_portion"   : round(prix_par_portion, 2),
        "proteines_portion_g": p["proteines_portion_g"],
        "nombre_portions"    : p["nombre_portions"],
        "cout_30g"           : round(cout_30g, 2),
    }

# ====== OUTIL DE RECHERCHE (Serper) ======
DOMAINES_BLOQUES = [
    "linkedin.com", "facebook.com", "twitter.com", "x.com",
    "reddit.com", "quora.com", "pinterest.com", "tiktok.com",
    "medium.com", "blogspot.com", "wordpress.com"
]

def agent_recherche(query):
    try:
        response = requests.post(
            "https://google.serper.dev/search",
            headers={
                "X-API-KEY"   : SERPER_KEY,
                "Content-Type": "application/json"
            },
            json={"q": query, "num": 10, "gl": "ca", "hl": "en"},
            timeout=15
        )

        if response.status_code != 200:
            print(f"      ⚠️  Serper status {response.status_code} : {response.text[:200]}")
            return f"Erreur Serper (status {response.status_code})."

        data     = response.json()
        snippets = []
        bloques  = 0

        # answerBox = reponse directe Google (souvent le prix)
        if data.get("answerBox"):
            ab = data["answerBox"]
            direct = ab.get("answer") or ab.get("snippet", "")
            if direct:
                snippets.append(f"[Reponse directe Google] {direct}")

        for r in data.get("organic", []):
            lien = r.get("link", "")
            if any(d in lien for d in DOMAINES_BLOQUES):
                bloques += 1
                continue
            if r.get("snippet"):
                snippets.append(f"{r.get('title','')} ({lien}) : {r.get('snippet','')}")

        if not snippets:
            return "Aucun resultat exploitable pour cette requete."

        resultat = "\n\n".join(snippets[:7])
        info_bloc = f", {bloques} source(s) non fiable(s) ecartee(s)" if bloques else ""
        print(f"      ✅ {len(snippets)} resultats ({len(resultat)} caracteres{info_bloc})")
        return resultat

    except Exception as e:
        print(f"      ⚠️  Erreur Serper : {e}")
        return f"Erreur lors de la recherche : {e}"

# ====== DEFINITION DE L'OUTIL POUR LE LLM ======
tools = [{
    "type": "function",
    "function": {
        "name": "recherche_web",
        "description": (
            "Recherche sur le web en temps reel. Utilise cet outil 2 a 3 fois maximum "
            "avec des requetes differentes, puis redige ta reponse finale."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Requete de recherche, formulee en anglais"
                }
            },
            "required": ["query"]
        }
    }
}]

# ====== MEMOIRE LONG TERME (Pinecone) ======
def get_embedding(text):
    response = pc.inference.embed(
        model      = "llama-text-embed-v2",
        inputs     = [text],
        parameters = {"input_type": "query"}
    )
    return response[0].values

def agent_memoire_chercher(query):
    print("🧠 Memoire → Pinecone...")
    try:
        vector  = get_embedding(query)
        results = index.query(vector=vector, top_k=1, include_metadata=True)

        if results.matches and results.matches[0].score > 0.95:
            meta = results.matches[0].metadata

            if meta.get("prompt_ver") != PROMPT_VERSION:
                print("   ⏭️  Reponse d'une ancienne version du prompt, ignoree.")
                return None

            age = int(time.time()) - int(meta.get("timestamp", 0))
            if age > DUREE_VALIDITE:
                print(f"   ⏭️  Reponse perimee ({age // 86400} jours), ignoree.")
                return None

            print(f"   ✅ Trouve en memoire (score {results.matches[0].score:.3f})")
            return meta.get("response")

        print("   ❌ Pas en memoire, recherche en cours...")
        return None
    except Exception as e:
        print(f"   ⚠️  Pinecone : {e}")
        return None

def agent_memoire_sauvegarder(query, response):
    print("💾 Sauvegarde Pinecone...")
    try:
        vector = get_embedding(query)
        doc_id = hashlib.md5(query.encode()).hexdigest()
        index.upsert(vectors=[{
            "id"      : doc_id,
            "values"  : vector,
            "metadata": {
                "query"     : query,
                "response"  : response,
                "timestamp" : int(time.time()),
                "prompt_ver": PROMPT_VERSION
            }
        }])
        print("   ✅ Sauvegarde.")
    except Exception as e:
        print(f"   ⚠️  Erreur sauvegarde : {e}")

# ====== BOUCLE AGENTIQUE (le coeur de MITARYS) ======
def agent_boucle(question, contexte_calcul=None, historique=None, max_tours=4):
    contenu_user = question

    if contexte_calcul:
        a, b = contexte_calcul
        contenu_user += f"""

Chiffres deja calcules (ne recalcule rien) :

{a['nom']} : {a['prix']}$ | {a['quantite_kg']}kg | {a['prix_par_kg']}$/kg | {a['prix_par_portion']}$/portion | {a['proteines_portion_g']}g prot/portion | {a['nombre_portions']} portions | {a['cout_30g']}$ pour 30g prot

{b['nom']} : {b['prix']}$ | {b['quantite_kg']}kg | {b['prix_par_kg']}$/kg | {b['prix_par_portion']}$/portion | {b['proteines_portion_g']}g prot/portion | {b['nombre_portions']} portions | {b['cout_30g']}$ pour 30g prot"""

    messages = [{"role": "system", "content": system_prompt}]
    if historique:
        messages.extend(historique)
    messages.append({"role": "user", "content": contenu_user})

    resultats_collectes = []

    for tour in range(max_tours):
        print(f"\n🔄 Tour {tour + 1}/{max_tours}")

        response = groq_client.chat.completions.create(
            model       = MODELE,
            messages    = messages,
            tools       = tools,
            temperature = 0.3
        )

        msg = response.choices[0].message

        if not msg.tool_calls:
            print("   ✅ L'agent a termine sa recherche.")
            return msg.content

        # Convertir l'objet Groq en dictionnaire propre
        messages.append({
            "role"      : "assistant",
            "content"   : msg.content or "",
            "tool_calls": [
                {
                    "id"      : c.id,
                    "type"    : "function",
                    "function": {
                        "name"     : c.function.name,
                        "arguments": c.function.arguments
                    }
                } for c in msg.tool_calls
            ]
        })

        for call in msg.tool_calls:
            try:
                args    = json.loads(call.function.arguments)
                requete = args.get("query", "")
            except Exception:
                requete = ""

            print(f"   🔍 Recherche : \"{requete}\"")
            resultat = agent_recherche(requete) if requete else "Requete vide."
            resultats_collectes.append(f"--- Recherche : {requete} ---\n{resultat}")

            messages.append({
                "role"        : "tool",
                "tool_call_id": call.id,
                "content"     : resultat
            })

    # Max de tours atteint : reponse finale SANS outils, historique propre
    print("\n⏱️  Max de tours atteint, generation de la reponse finale...")

    messages_propres = [{"role": "system", "content": system_prompt}]
    if historique:
        messages_propres.extend(historique)
    messages_propres.append({
        "role"   : "user",
        "content": f"""{contenu_user}

Voici les resultats de recherche deja rassembles :

{chr(10).join(resultats_collectes)}

Redige maintenant ta reponse finale avec ces informations uniquement.
N'appelle aucun outil."""
    })

    final = groq_client.chat.completions.create(
        model       = MODELE,
        messages    = messages_propres,
        temperature = 0.3
    )
    return final.choices[0].message.content

# ====== SUPERVISEUR ======
def agent_superviseur(query, produit_A=None, produit_B=None, historique=None):
    print("\n" + "=" * 55)
    print("MITARYS AI — Agent Superviseur")
    print("=" * 55)
    print(f"Question : {query}\n")

    # La memoire Pinecone ne sert que pour une question autonome.
    # Une question de suivi depend du contexte de la conversation.
    if not historique:
        reponse_memorisee = agent_memoire_chercher(query)
        if reponse_memorisee:
            return reponse_memorisee

    contexte_calcul = None
    if produit_A and produit_B:
        contexte_calcul = (calculer(produit_A), calculer(produit_B))

    reponse = agent_boucle(query, contexte_calcul, historique)

    if not historique:
        agent_memoire_sauvegarder(query, reponse)

    return reponse

# ====== POINT D'ENTREE : CONVERSATION ======
if __name__ == "__main__":
    print("\n" + "=" * 55)
    print("MITARYS AI")
    print("=" * 55)
    print("Commandes : 'quit' pour sortir, 'reset' pour repartir a zero.")

    historique = []

    while True:
        try:
            question = input("\n💬 Toi : ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nA bientot !")
            break

        if question.lower() in ("quit", "exit", "q"):
            print("A bientot !")
            break

        if question.lower() == "reset":
            historique = []
            print("🔄 Conversation reinitialisee.")
            continue

        if not question:
            continue

        reponse = agent_superviseur(question, historique=historique)

        print("\n" + "=" * 55)
        print("MITARYS AI")
        print("=" * 55)
        print(reponse)

        historique.append({"role": "user",      "content": question})
        historique.append({"role": "assistant", "content": reponse})
        historique = historique[-MAX_HISTORIQUE:]