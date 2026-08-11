#!/usr/bin/env python3
# verifier_base.py
import sqlite3

def verifier():
    try:
        conn = sqlite3.connect("mitarys.db", timeout=5)
        conn.row_factory = sqlite3.Row
    except sqlite3.OperationalError as e:
        print(f"❌ Base de données inaccessible : {e}")
        return

    c = conn.cursor()

    c.execute("SELECT id, titre, modele FROM conversations ORDER BY creee_le DESC")
    conversations = c.fetchall()

    if not conversations:
        print("Aucune conversation enregistrée.")
        return

    print(f"\n{'='*70}")
    print(f"{len(conversations)} conversation(s) trouvée(s)")
    print(f"{'='*70}\n")

    total_anomalies = 0

    for conv in conversations:
        print(f"📁 [{conv['id']}] {conv['titre'][:60]}  ({conv['modele']})")
        print("-" * 70)

        c.execute("""
            SELECT role, contenu FROM messages
            WHERE conversation_id = ?
            ORDER BY id ASC
        """, (conv['id'],))
        messages = c.fetchall()

        if not messages:
            print("   ⚠️  ANOMALIE : conversation vide, aucun message.")
            total_anomalies += 1
            print()
            continue

        a_reponse_ia = any(m['role'] == 'ia' for m in messages)
        if not a_reponse_ia:
            print("   ⚠️  ANOMALIE : aucune réponse IA enregistrée.")
            total_anomalies += 1

        for m in messages:
            etiquette = "👤 Toi " if m['role'] == 'user' else "🤖 IA  "
            contenu = m['contenu']

            if "Erreur" in contenu or "erreur" in contenu:
                print(f"   {etiquette}: ⚠️  {contenu[:150]}")
                total_anomalies += 1
            else:
                apercu = contenu[:200].replace("\n", " ")
                print(f"   {etiquette}: {apercu}{'...' if len(contenu) > 200 else ''}")

        print()

    print(f"{'='*70}")
    print(f"Total anomalies détectées : {total_anomalies}")
    print(f"{'='*70}\n")

    conn.close()

if __name__ == "__main__":
    verifier()