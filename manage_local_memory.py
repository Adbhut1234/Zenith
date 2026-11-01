"""
Zenith Local Memory Management CLI Utility
==========================================
View, export, prune, or reset Zenith's local SQLite memory matrix
(zenith_facts, zenith_playbooks, zenith_relations, zenith_working_memory).
"""

import os
import sys
import json
import sqlite3
import argparse
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "zenith_memory.db")

def get_db():
    if not os.path.exists(DB_PATH):
        print(f"Database does not exist at: {DB_PATH}")
        sys.exit(1)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def show_summary(user_id: str):
    print("=" * 60)
    print(f"ZENITH LOCAL MEMORY MATRIX READOUT (User: {user_id})")
    print(f"Database Path: {DB_PATH}")
    print("=" * 60)
    
    with get_db() as conn:
        c = conn.cursor()
        
        # 1. Active Facts
        c.execute("""
            SELECT id, category, topic, fact, updated_at 
            FROM zenith_facts 
            WHERE user_id = ? AND (is_active IS NULL OR is_active = 1)
            ORDER BY category, topic
        """, (user_id,))
        active_facts = c.fetchall()
        print(f"\n[ACTIVE FACTS] ({len(active_facts)} total):")
        for f in active_facts:
            print(f"  • [{f['category'].upper()}] {f['topic']}: {f['fact']}")

        # 2. Superseded Facts (Ship of Theseus)
        c.execute("""
            SELECT id, topic, fact, superseded_reason, updated_at 
            FROM zenith_facts 
            WHERE user_id = ? AND is_active = 0
            ORDER BY updated_at DESC
        """, (user_id,))
        superseded = c.fetchall()
        if superseded:
            print(f"\n[HISTORICALLY SUPERSEDED FACTS] ({len(superseded)} archived):")
            for f in superseded:
                print(f"  - {f['topic']}: {f['fact']} (Reason: {f['superseded_reason']})")

        # 3. Procedural Playbooks
        c.execute("SELECT task_pattern, context_domain, recommended_action, success_count FROM zenith_playbooks")
        playbooks = c.fetchall()
        print(f"\n[LEARNED PROCEDURAL PLAYBOOKS] ({len(playbooks)} total):")
        for p in playbooks:
            print(f"  • [{p['context_domain']}] {p['task_pattern']} (Successes: {p['success_count']}) -> {p['recommended_action']}")

        # 4. Knowledge Graph Relations
        try:
            c.execute("SELECT source_entity, relation, target_entity FROM zenith_relations LIMIT 10")
            relations = c.fetchall()
            if relations:
                print(f"\n[KNOWLEDGE GRAPH RELATIONS] ({len(relations)} sample):")
                for r in relations:
                    print(f"  • ({r['source_entity']}) -[{r['relation']}]-> ({r['target_entity']})")
        except Exception:
            pass

    print("\n" + "=" * 60)

def clear_user_facts(user_id: str):
    confirm = input(f"Are you sure you want to delete all active facts for '{user_id}'? (y/N): ")
    if confirm.lower() != 'y':
        print("Aborted.")
        return
    with get_db() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM zenith_facts WHERE user_id = ?", (user_id,))
        c.execute("DELETE FROM zenith_history WHERE user_id = ?", (user_id,))
        conn.commit()
        print(f"All facts and history cleared for user: '{user_id}'.")

def export_json(output_file: str, user_id: str):
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM zenith_facts WHERE user_id = ?", (user_id,))
        facts = [dict(r) for r in c.fetchall()]
        c.execute("SELECT * FROM zenith_playbooks")
        playbooks = [dict(r) for r in c.fetchall()]
        
    data = {
        "user_id": user_id,
        "exported_at": datetime.now().isoformat(),
        "facts": facts,
        "playbooks": playbooks
    }
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Exported {len(facts)} facts and {len(playbooks)} playbooks to: {output_file}")

def main():
    parser = argparse.ArgumentParser(description="Zenith Local Memory Matrix Manager")
    parser.add_argument("--user", default=os.getenv("Zenith_USER_ID", "Admin"), help="User ID to query/manage")
    parser.add_argument("--clear", action="store_true", help="Clear all stored facts for the specified user")
    parser.add_argument("--export", metavar="FILE", help="Export memory snapshot to JSON file")
    
    args = parser.parse_args()
    
    if args.clear:
        clear_user_facts(args.user)
    elif args.export:
        export_json(args.export, args.user)
    else:
        show_summary(args.user)

if __name__ == "__main__":
    main()
