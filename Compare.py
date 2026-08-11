#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# MITARYS AI - Agent autonome, version instrumentee
# Chaque etape emet un evenement que l'interface peut afficher en direct.

from groq import Groq
from openai import OpenAI
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
groq_client     = Groq(api_key=os.environ.get("GROQ_API_KEY"))
deepseek_client = OpenAI(
    api_key  = os.environ.get("DEEPSEEK_API_KEY") or "placeholder",
    base_url = "https://api.deepseek.com"
)
pc         = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))
index      = pc.Index("mitarys-products")
SERPER_KEY = os.environ.get("SERPER_API_KEY")

# ====== CONFIGURATION ======
MODELES = {
    "VIX 1.9": {
        "fournisseur": "groq",
        "modele"     : "openai/gpt-oss-20b",
        "tours"      : 3,
        "web"        : True,
    },
    "VIX Search": {
        "fournisseur": "deepseek",
        "modele"     : "deepseek-v4-flash",
        "tours"      : 5,
        "web"        : True,
    },
}
MODELE_DEFAUT = "VIX 1.9"


PROMPT_VERSION = "v18"
DUREE_VALIDITE = 7 * 24 * 3600

DATE_DU_JOUR = datetime.now().strftime("%d/%m/%Y")
ANNEE        = datetime.now().year

def client_pour(config):
    """Renvoie le client correspondant au fournisseur du modele."""
    if config["fournisseur"] == "deepseek":
        return deepseek_client
    return groq_client


DOMAINES_BLOQUES = [
    "linkedin.com", "facebook.com", "twitter.com", "x.com",
    "reddit.com", "quora.com", "pinterest.com", "tiktok.com",
    "medium.com", "blogspot.com", "wordpress.com"
]

# ====== SYSTEM PROMPT ======
PROMPT_VERSION = "v14"

system_prompt = f"""CONTEXTE TEMPOREL — LIS CECI EN PREMIER
Nous sommes le {DATE_DU_JOUR}. Nous sommes en {ANNEE}.
Tes connaissances internes sont perimees de plusieurs annees. Pour tout ce qui
concerne l'actualite, les prix, les produits ou les chiffres de marche, tu te fies
UNIQUEMENT aux resultats de recherche_web, jamais a ta memoire.
Ajoute "{ANNEE}" a tes requetes de recherche quand la fraicheur compte.
Lorsqu'on te questionne avec une langue tu envois la reponse avec cette meme langue.

Tu es MITARYS AI, concu par l'equipe MITARYS a Montreal.
Tu es un expert en serveurs IA domestiques : dimensionnement, refroidissement,
montage et deploiement.
Tu as ete concu afin que le commerce soit plus paisible, se resume juste par une
conversation et non par des scrolls infinissables. Ajoute cette phrase a chaque
moment qu'on te demande qui tu es.

DOMAINE PRINCIPAL : serveurs IA / home lab
- Calcul de charge GPU/CPU : conversion watts -> BTU/h (1W = 3.41 BTU/h),
  toujours prevoir 20% de marge sur la charge calculee pour du LLM en continu
  (80-100% de charge 24h/24, different d'une charge gaming en rafale).
- Conductivite thermique : comparer les pates (W/mK) et pads thermiques selon
  l'ecart CPU/GPU et le contact avec le dissipateur.
- Ventilateurs PWM : distinguer pression statique (mm H2O, radiateurs/serveurs
  fermes) et debit d'air (m3/h ou CFM, boitiers ouverts) — les deux comptent
  selon le cas d'usage, jamais un seul chiffre isole.
- Refroidissement : air (simple, bruyant sous charge continue) vs AIO 240/360mm
  (silence, pour GPU unique) vs custom loop (multi-GPU, boucles GPU/CPU
  separees obligatoires) vs immersion (hors scope home lab).
- Niveaux de bruit cibles : chambre <30 dB(A), bureau <40 dB(A), sous-sol/garage
  sans contrainte.
- Serveurs de tout calibre : d'un mini-PC single-GPU a un rack multi-GPU —
  adapte toujours la recommandation a l'usage reel decrit (inference simple,
  fine-tuning, multi-utilisateurs).

SERVICES MITARYS (a mentionner si pertinent, jamais forcer la vente) :
- Montage de serveurs home lab sur mesure : main-d'oeuvre + choix des
  composants selon le budget et l'usage du client.
- Cles USB pretes a l'emploi : Proxmox ISO + un petit modele local
  pre-installe (Qwen 7B) pour deploiement immediat sans configuration.
  A proposer uniquement quand la question porte sur le demarrage rapide
  ou la simplicite de deploiement, jamais de maniere systematique.


  COMPORTEMENT PROACTIF — QUALIFICATION DU BESOIN :
Quand la question laisse penser que la personne planifie un vrai projet
(pas juste une question générale de culture technique), pose UNE question
de clarification avant de conclure, ou propose l'audit gratuit explicitement.

Signaux qui indiquent un vrai projet :
- Mention d'un usage concret ("je veux monter", "je débute", "pour mon serveur")
- Mention de contraintes (budget, espace, bruit, GPU precis)
- Question de suivi après un premier comparatif

Dans ce cas, termine ta reponse par UNE phrase adaptee, par exemple :
"Si vous voulez qu'on valide ce choix avec vos contraintes precises (budget,
espace, usage), l'audit est gratuit pour nos 10 premiers clients : ecrivez a
support@mitarys.com."

Ne fais jamais ca sur une question purement definitionnelle ou generale
(ex: "c'est quoi un ventilateur PWM ?") — reste factuel, sans relance commerciale.

Methode de travail :
- Utilise recherche_web des que la question porte sur des faits recents, des prix,
  des produits, ou tout ce qui peut avoir change recemment.
- Apres 3 recherches maximum, redige ta reponse finale avec ce que tu as trouve.
- Formule tes requetes EN ANGLAIS (plus de resultats).
- Tu as acces a l'historique de la conversation : comprends les questions de suivi
  dans leur contexte au lieu de demander des precisions.

Regles strictes :
1. Tu ne fais JAMAIS de calcul toi-meme — utilise uniquement les chiffres fournis
   ou deja calcules dans le contexte.
2. Tu n'inventes JAMAIS de produit, de prix, de marque ou de statistique.
3. Tu ne mentionnes jamais Groq, GPT, DeepSeek, Pinecone, Serper ou tout outil
   sous-jacent.
4. Si on te demande qui t'a cree ou "qui es-tu"   : tu es MITARYS AI, developpe par
   l'equipe MITARYS. N'ajoute JAMAIS cette presentation en fin de reponse pour
   une question technique — seulement quand on te la demande explicitement.
5. Pour "le meilleur produit" : cite minimum 3 produits reels avec nom exact + marque,
   prix si trouve, et un score sur 5 pour Rapport qualite-prix, Performance et
   Silence, plus une ligne de justification.
6. Cite tes sources avec l'URL complete entre parentheses simples juste apres
   l'information, format exact : (https://exemple.com/page)
   JAMAIS de crochets, de numeros de reference, ni de notes de bas de page.
7. Chaque donnee datee doit indiquer sa date, format [MAJ 15/07/{ANNEE}].
   Si tu ne connais pas la date, ecris [date inconnue].
8. Pour les prix : precise le format ou la variante du produit, et indique que le
   prix est indicatif et a verifier chez le marchand.
9. Privilegie les sources primaires : sites officiels, publications scientifiques,
   presse specialisee, documentation constructeur.
10. Si deux sources donnent des chiffres incompatibles, signale la contradiction et
    indique laquelle est la plus fiable.
11. Termine toujours par : "Informations rassemblees le {DATE_DU_JOUR}."
12. Pour toute demande de rendez-vous, devis ou suivi personnalise, oriente vers
    support@mitarys.com plutot que de tenter d'y repondre toi-meme.
13. Ton chaleureux et professionnel. Maximum 300 mots pour un comparatif.
14. Pour toute question technique/explicative, presente les donnees chiffrees
    dans un tableau markdown STRICT avec cette syntaxe exacte :
    | Colonne1 | Colonne2 |
    |----------|----------|
    | valeur   | valeur   |
    La ligne de separation avec les tirets est OBLIGATOIRE. Chaque ligne de
    donnees tient sur UNE seule ligne, sans retour a la ligne a l'interieur
    d'une cellule.
    15. Pour une question de definition simple (ex: "c'est quoi un PWM", "c'est quoi
    un pad thermique"), NE LANCE PAS de recherche web si tu connais deja la
    reponse de facon fiable et non-datee. Reponds en 3-4 phrases claires, SANS
    tableau, SANS recherche. Le tableau est reserve aux VRAIES comparaisons
    entre plusieurs produits/options, jamais a une simple definition.
16. Si la question est une demande generale sans  contexte precis (budget, GPU, usage), tu DOIS d'abord repondre normalement a la question en 2-4 phrases
    utiles, PUIS sur une NOUVELLE ligne separee, ajouter exactement :
    [QUALIFICATION]
    Le marqueur [QUALIFICATION] ne remplace JAMAIS ta reponse — il vient
    TOUJOURS en plus, apres du vrai contenu. Une reponse qui contient
    UNIQUEMENT [QUALIFICATION] sans texte avant est INTERDITE.
17. Si l'utilisateur indique qu'il part de zero (aucun materiel, aucune
    experience), propose explicitement l'audit gratuit avec
    l'equipe technique. Formule exacte a adapter :
    "Vu que vous partez de zero, je vous recommande notre audit gratuit —
    l'equipe technique MITARYS analyse votre besoin et vous
    propose une configuration sur mesure. Ecrivez a support@mitarys.com
    pour demarrer."""


# ====== TRACE : collecte ce qui se passe pendant une requete ======
class Trace:
    """Accumule les evenements d'une requete et les transmet a l'interface."""
    def __init__(self, emettre=None):
        self.emettre = emettre or (lambda *a, **k: None)
        self.bloques = []
        self.retenus = []

    def envoyer(self, **donnees):
        self.emettre(donnees)


# ====== NORMALISATION DES UNITES ======
def convertir_en_grammes(texte):
    if texte is None:
        return None
    if isinstance(texte, (int, float)):
        return float(texte)
    t = str(texte).lower().strip().replace(",", ".")
    m = re.search(r"([\d.]+)", t)
    if not m:
        return None
    n = float(m.group(1))
    if "lb" in t or "pound" in t: return n * 453.6
    if "oz" in t:                 return n * 28.35
    if "kg" in t:                 return n * 1000
    if "g"  in t:                 return n
    return None


def calculer(p):
    quantite = p["quantite_kg"]
    if isinstance(quantite, str):
        g = convertir_en_grammes(quantite)
        if g is None:
            raise ValueError(f"Poids illisible : {quantite}")
        quantite = g / 1000

    proteines_totales = p["proteines_portion_g"] * p["nombre_portions"]
    return {
        "nom"                : p["nom"],
        "prix"               : p["prix"],
        "quantite_kg"        : round(quantite, 3),
        "prix_par_kg"        : round(p["prix"] / quantite, 2),
        "prix_par_portion"   : round(p["prix"] / p["nombre_portions"], 2),
        "proteines_portion_g": p["proteines_portion_g"],
        "nombre_portions"    : p["nombre_portions"],
        "cout_30g"           : round((p["prix"] / proteines_totales) * 30, 2),
    }


# ====== AGENT RECHERCHE (Serper) ======
def agent_recherche(query, trace):
    try:
        reponse = requests.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": SERPER_KEY, "Content-Type": "application/json"},
            json={"q": query, "num": 10, "gl": "ca", "hl": "en"},
            timeout=15
        )
        

        if reponse.status_code != 200:
            trace.envoyer(etape="recherche", requete=query, n=0,
                          erreur=f"HTTP {reponse.status_code}")
            return f"Erreur Serper (status {reponse.status_code})."

        data     = reponse.json()
        snippets = []

        if data.get("answerBox"):
            ab = data["answerBox"]
            direct = ab.get("answer") or ab.get("snippet", "")
            if direct:
                snippets.append(f"[Reponse directe Google] {direct}")

        for r in data.get("organic", []):
            lien = r.get("link", "")
            domaine = re.sub(r"^https?://(www\.)?", "", lien).split("/")[0]

            if any(d in lien for d in DOMAINES_BLOQUES):
                if domaine not in trace.bloques:
                    trace.bloques.append(domaine)
                continue

            if r.get("snippet"):
                snippets.append(f"{r.get('title','')} ({lien}) : {r.get('snippet','')}")
                if domaine and domaine not in trace.retenus:
                    trace.retenus.append(domaine)

        trace.envoyer(etape="recherche", requete=query, n=len(snippets))

        if not snippets:
            return "Aucun resultat exploitable pour cette requete."
        return "\n\n".join(snippets[:7])

    except Exception as e:
        trace.envoyer(etape="recherche", requete=query, n=0, erreur=str(e))
        return f"Erreur lors de la recherche : {e}"



tools = [{
    "type": "function",
    "function": {
        "name": "recherche_web",
        "description": ("Recherche sur le web en temps reel. Utilise cet outil 2 a 3 fois "
                        "maximum avec des requetes differentes, puis redige ta reponse."),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Requete en anglais"}
            },
            "required": ["query"]
        }
    }
}]


# ====== MEMOIRE PINECONE ======
def get_embedding(texte):
    r = pc.inference.embed(
        model="llama-text-embed-v2",
        inputs=[texte],
        parameters={"input_type": "query"}
    )
    return r[0].values


def agent_memoire_chercher(query, trace):
    try:
        vector  = get_embedding(query)
        results = index.query(vector=vector, top_k=1, include_metadata=True)

        if results.matches and results.matches[0].score > 0.95:
            meta = results.matches[0].metadata
            if meta.get("prompt_ver") != PROMPT_VERSION:
                trace.envoyer(etape="memoire", statut="fin", verdict="version obsolete")
                return None
            age = int(time.time()) - int(meta.get("timestamp", 0))
            if age > DUREE_VALIDITE:
                trace.envoyer(etape="memoire", statut="fin",
                              verdict=f"perimee ({age // 86400} j)")
                return None
            trace.envoyer(etape="memoire", statut="fin",
                          verdict=f"trouvee ({results.matches[0].score:.2f})")
            return meta.get("response")

        trace.envoyer(etape="memoire", statut="fin", verdict="aucune correspondance")
        return None
    except Exception as e:
        trace.envoyer(etape="memoire", statut="fin", verdict="indisponible")
        return None


def agent_memoire_sauvegarder(query, reponse):
    try:
        index.upsert(vectors=[{
            "id"      : hashlib.md5(query.encode()).hexdigest(),
            "values"  : get_embedding(query),
            "metadata": {
                "query"     : query,
                "response"  : reponse,
                "timestamp" : int(time.time()),
                "prompt_ver": PROMPT_VERSION
            }
        }])
    except Exception:
        pass


# ====== BOUCLE AGENTIQUE ======
def agent_boucle(question, trace, modele=MODELE_DEFAUT, contexte_calcul=None, historique=None):
    config = MODELES.get(modele, MODELES[MODELE_DEFAUT])
    client = client_pour(config)

    contenu = question
    if contexte_calcul:
        a, b = contexte_calcul
        contenu += (
            f"\n\nChiffres deja calcules (ne recalcule rien) :\n\n"
            f"{a['nom']} : {a['prix']}$ | {a['quantite_kg']}kg | {a['prix_par_kg']}$/kg | "
            f"{a['proteines_portion_g']}g prot/portion | {a['cout_30g']}$ pour 30g prot\n\n"
            f"{b['nom']} : {b['prix']}$ | {b['quantite_kg']}kg | {b['prix_par_kg']}$/kg | "
            f"{b['proteines_portion_g']}g prot/portion | {b['cout_30g']}$ pour 30g prot"
        )

    messages = [{"role": "system", "content": system_prompt}]
    if historique:
        messages.extend(historique)
    messages.append({"role": "user", "content": contenu})

    outils = tools if config["web"] else None
    collecte = []

    for _ in range(config["tours"]):
        appel = {"model": config["modele"], "messages": messages, "temperature": 0.3}
        if outils:
            appel["tools"] = outils

        reponse = client.chat.completions.create(**appel)
        msg = reponse.choices[0].message

        if not msg.tool_calls:
            return msg.content

        messages.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [{
                "id": c.id, "type": "function",
                "function": {"name": c.function.name, "arguments": c.function.arguments}
            } for c in msg.tool_calls]
        })

        for call in msg.tool_calls:
            try:
                requete = json.loads(call.function.arguments).get("query", "")
            except Exception:
                requete = ""
            resultat = agent_recherche(requete, trace) if requete else "Requete vide."
            collecte.append(f"--- {requete} ---\n{resultat}")
            messages.append({
                "role": "tool", "tool_call_id": call.id, "content": resultat
            })

    # tours epuises : reponse finale sans outils
    propres = [{"role": "system", "content": system_prompt}]
    if historique:
        propres.extend(historique)
    propres.append({
        "role": "user",
        "content": f"{contenu}\n\nResultats rassembles :\n\n"
                   + "\n\n".join(collecte)
                   + "\n\nRedige ta reponse finale. N'appelle aucun outil."
    })

    final = client.chat.completions.create(
        model=config["modele"], messages=propres, temperature=0.3
    )
    return final.choices[0].message.content


# ====== SUPERVISEUR ======
def agent_superviseur(query, modele=MODELE_DEFAUT, historique=None,
                      produit_A=None, produit_B=None, emettre=None):
    trace = Trace(emettre)

    # 1. memoire
    trace.envoyer(etape="memoire", statut="debut")
    if not historique:
        memorisee = agent_memoire_chercher(query, trace)
        if memorisee:
            trace.envoyer(etape="synthese", statut="fin", verdict="depuis la memoire")
            trace.envoyer(reponse=memorisee)
            return memorisee
    else:
        trace.envoyer(etape="memoire", statut="fin", verdict="suivi de conversation")

    # 2. calculs Python
    contexte = None
    if produit_A and produit_B:
        contexte = (calculer(produit_A), calculer(produit_B))

    # 3. recherche + generation
    trace.envoyer(etape="recherche", statut="debut")
    reponse = agent_boucle(query, trace, modele, contexte, historique)
    trace.envoyer(etape="recherche", statut="fin",
                  verdict=f"{len(trace.retenus) + len(trace.bloques)} resultats")

    # 4. filtrage
    trace.envoyer(etape="filtrage", statut="debut", domaines=trace.bloques)
    trace.envoyer(etape="filtrage", statut="fin",
                  verdict=f"{len(trace.bloques)} ecartees")

    # 5. synthese
    trace.envoyer(etape="synthese", statut="debut", sources=trace.retenus)
    trace.envoyer(etape="synthese", statut="fin",
                  verdict=f"{len(trace.retenus)} sources retenues")

    if not historique:
        agent_memoire_sauvegarder(query, reponse)

    trace.envoyer(reponse=reponse)
    return reponse


# ====== MODE TERMINAL ======
if __name__ == "__main__":
    print("\nMITARYS AI — 'quit' pour sortir, 'reset' pour repartir a zero.")
    historique = []

    while True:
        try:
            question = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if question.lower() in ("quit", "exit", "q"):
            break
        if question.lower() == "reset":
            historique = []
            print("Conversation reinitialisee.")
            continue
        if not question:
            continue

        def afficher(e):
            if "reponse" in e:
                return
            if e.get("requete"):
                print(f"   recherche : {e['requete']} -> {e.get('n', 0)}")
            elif e.get("verdict"):
                print(f"   {e.get('etape')} : {e['verdict']}")

        reponse = agent_superviseur(question, historique=historique, emettre=afficher)
        print("\n" + reponse)

        historique.append({"role": "user",      "content": question})
        historique.append({"role": "assistant", "content": reponse})
        historique = historique[-12:]