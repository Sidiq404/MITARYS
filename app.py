#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# MITARYS AI - serveur local
#
#   python3 app.py     puis     http://localhost:5050
#
# Rien n'est publie en ligne : le serveur n'ecoute que ta machine.
# Les conversations sont enregistrees dans mitarys.db (SQLite).

from flask import Flask, request, jsonify, render_template, Response, stream_with_context
import json
import queue
import threading

from compare import agent_superviseur
import base

app = Flask(__name__)
base.initialiser()


@app.route("/")
def accueil():
    return render_template("index.html")


# ---------- CONVERSATIONS ----------
@app.route("/api/conversations")
def conversations():
    return jsonify(base.lister_conversations())


@app.route("/api/conversations/<int:id_conv>")
def conversation(id_conv):
    return jsonify(base.lire_messages(id_conv))


@app.route("/api/conversations/<int:id_conv>", methods=["DELETE"])
def effacer(id_conv):
    base.supprimer_conversation(id_conv)
    return jsonify({"ok": True})


# ---------- CHAT ----------
@app.route("/api/chat", methods=["POST"])
def chat():
    """Diffuse un evenement JSON par ligne, au fur et a mesure du travail."""
    donnees    = request.get_json(force=True)
    message    = (donnees.get("message") or "").strip()
    modele     = donnees.get("modele") or "RYX1"
    historique = donnees.get("historique") or []
    id_conv    = donnees.get("conversation_id")

    if not message:
        return jsonify({"erreur": "message vide"}), 400

    # enregistre la question
    if id_conv:
        base.creer_conversation(id_conv, message, modele)
        base.ajouter_message(id_conv, "user", message, message)

    file = queue.Queue()

    def emettre(evenement):
        file.put(evenement)

    def travailler():
        try:
            reponse = agent_superviseur(
                message,
                modele=modele,
                historique=historique,
                emettre=emettre
            )
            if id_conv:
                base.ajouter_message(id_conv, "ia", reponse)
        except Exception as e:
            file.put({"erreur": str(e)})
        finally:
            file.put(None)

    threading.Thread(target=travailler, daemon=True).start()

    @stream_with_context
    def diffuser():
        while True:
            evenement = file.get()
            if evenement is None:
                break
            yield json.dumps(evenement, ensure_ascii=False) + "\n"

    return Response(diffuser(), mimetype="application/x-ndjson")


if __name__ == "__main__":
    print("\n  MITARYS AI  ->  http://localhost:5050\n")
    app.run(debug=True, port=5050)