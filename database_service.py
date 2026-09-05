import os
import sqlite3
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

DB_PATH = Path(__file__).parent.parent / "selections.db"

class DatabaseService:
    @staticmethod
    def init_db():
        """Initializes the database and creates the selections table if it doesn't exist."""
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS officer_selections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bid_id TEXT NOT NULL,
                vendor_name TEXT NOT NULL,
                officer_username TEXT NOT NULL,
                registered_email TEXT NOT NULL,
                email_content TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()

    @staticmethod
    def save_selection(bid_id: str, vendor_name: str, officer_username: str, registered_email: str, email_content: str) -> int:
        """Saves a new officer selection record into the database."""
        # Ensure database is initialized
        DatabaseService.init_db()
        
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        
        cursor.execute("""
            INSERT INTO officer_selections (bid_id, vendor_name, officer_username, registered_email, email_content, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (bid_id, vendor_name, officer_username, registered_email, email_content, timestamp))
        
        inserted_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return inserted_id

    @staticmethod
    def get_selections() -> List[Dict[str, Any]]:
        """Retrieves all selection records, ordered by timestamp descending."""
        DatabaseService.init_db()
        
        conn = sqlite3.connect(str(DB_PATH))
        # This row factory maps columns to dictionary keys
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM officer_selections ORDER BY timestamp DESC")
        rows = cursor.fetchall()
        
        results = [dict(row) for row in rows]
        conn.close()
        
        return results

# Self-initialize on module load
DatabaseService.init_db()
