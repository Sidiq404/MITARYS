#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# MITARYS - le CODE fait les calculs, le modele ne fait QUE comparer.
# Pour lancer :  python3 compare.py

import subprocess

# ====== TES DONNEES : la SEULE partie a modifier ======
produit_A = {
    "nom": "Whey A",
    "prix": 30.0,
    "quantite_kg": 1.0,
    "proteines_portion_g": 24.0,
    "nombre_portions": 33,
}
produit_B = {
    "nom": "Whey B",
    "prix": 45.0,
    "quantite_kg": 2.0,
    "proteines_portion_g": 20.0,
    "nombre_portions": 66,
}

# ====== LES CALCULS (faits par le code, jamais par l'IA) ======
def calculer(p):
    prix_par_kg = p["prix"] / p["quantite_kg"]
    prix_par_portion = p["prix"] / p["nombre_portions"]
    proteines_totales = p["proteines_portion_g"] * p["nombre_portions"]
    cout_30g = (p["prix"] / proteines_totales) * 30
    return {
        "nom": p["nom"], "prix": p["prix"],
        "prix_par_kg": round(prix_par_kg, 2),
        "prix_par_portion": round(prix_par_portion, 2),
        "proteines_portion_g": p["proteines_portion_g"],
        "nombre_portions": p["nombre_portions"],
        "cout_30g": round(cout_30g, 2),
    }

a = calculer(produit_A)
b = calculer(produit_B)

# ====== LE PROMPT : on donne les chiffres DEJA CALCULES ======
prompt = f"""Voici deux produits avec leurs chiffres DEJA CALCULES. Utilise-les tels quels, ne recalcule rien.

{a['nom']} :
- Prix total : {a['prix']} EUR
- Prix par kilo : {a['prix_par_kg']} EUR/kg
- Prix par portion : {a['prix_par_portion']} EUR
- Proteines par portion : {a['proteines_portion_g']} g
- Nombre de portions : {a['nombre_portions']}
- Cout pour 30 g de proteines : {a['cout_30g']} EUR

{b['nom']} :
- Prix total : {b['prix']} EUR
- Prix par kilo : {b['prix_par_kg']} EUR/kg
- Prix par portion : {b['prix_par_portion']} EUR
- Proteines par portion : {b['proteines_portion_g']} g
- Nombre de portions : {b['nombre_portions']}
- Cout pour 30 g de proteines : {b['cout_30g']} EUR

Compare ces deux produits et recommande le meilleur choix."""

# ====== ON ENVOIE AU MODELE ======
print("=" * 55)
print("CHIFFRES CALCULES PAR LE CODE :")
print("=" * 55)
print(prompt)
print("=" * 55)
print("REPONSE DE MITARYS :")
print("=" * 55)
r = subprocess.run(["ollama", "run", "mitarys", prompt],
                   capture_output=True, text=True)
print(r.stdout.strip())