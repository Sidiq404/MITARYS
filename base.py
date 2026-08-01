#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# MITARYS AI - stockage des conversations (SQLite)
# Un seul fichier : mitarys.db, cree automatiquement au premier lancement.

import sqlite3
import time
import os

CHEMIN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mitarys.db")


def connexion():
    c = sqlite3.connect(CHEMIN)
    c.row_factory = sqlite3.Row
    return c


def initialiser():
    with connexion() as c:
        c.executescript("""
            CREATE TABLE IF NOT EXISTS conversations (
                id       INTEGER PRIMARY KEY,
                titre    TEXT    NOT NULL,
                modele   TEXT    NOT NULL,
                creee_le INTEGER NOT NULL,
                maj_le   INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS messages (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                role            TEXT    NOT NULL,
                contenu         TEXT    NOT NULL,
                brut            TEXT,
                cree_le         INTEGER NOT NULL,
                FOREIGN KEY (conversation_id)
                    REFERENCES conversations(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_msg_conv
                ON messages(conversation_id);
        """)


def creer_conversation(id_conv, titre, modele):
    maintenant = int(time.time())
    with connexion() as c:
        c.execute("""
            INSERT OR IGNORE INTO conversations (id, titre, modele, creee_le, maj_le)
            VALUES (?, ?, ?, ?, ?)
        """, (id_conv, titre[:200], modele, maintenant, maintenant))


def ajouter_message(id_conv, role, contenu, brut=None):
    maintenant = int(time.time())
    with connexion() as c:
        c.execute("""
            INSERT INTO messages (conversation_id, role, contenu, brut, cree_le)
            VALUES (?, ?, ?, ?, ?)
        """, (id_conv, role, contenu, brut, maintenant))
        c.execute("UPDATE conversations SET maj_le = ? WHERE id = ?",
                  (maintenant, id_conv))


def lister_conversations(limite=60):
    with connexion() as c:
        lignes = c.execute("""
            SELECT c.id, c.titre, c.modele, c.creee_le,
                   COUNT(m.id) AS nb_messages
            FROM conversations c
            LEFT JOIN messages m ON m.conversation_id = c.id
            GROUP BY c.id
            ORDER BY c.maj_le DESC
            LIMIT ?
        """, (limite,)).fetchall()
    return [dict(l) for l in lignes]


def lire_messages(id_conv):
    with connexion() as c:
        lignes = c.execute("""
            SELECT role, contenu, brut
            FROM messages
            WHERE conversation_id = ?
            ORDER BY id ASC
        """, (id_conv,)).fetchall()
    return [dict(l) for l in lignes]


def supprimer_conversation(id_conv):
    with connexion() as c:
        c.execute("DELETE FROM messages      WHERE conversation_id = ?", (id_conv,))
        c.execute("DELETE FROM conversations WHERE id = ?",              (id_conv,))