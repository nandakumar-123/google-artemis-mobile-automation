import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from app.config import DB_PATH

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        instruction TEXT NOT NULL,
        plan_json TEXT,
        results_json TEXT,
        success INTEGER DEFAULT 0,
        error_message TEXT,
        screenshot_path TEXT,
        created_at TEXT NOT NULL
    )
    """)
    conn.commit()
    conn.close()

def save_task(
    instruction: str,
    plan: Optional[Dict[str, Any]] = None,
    results: Optional[List[Dict[str, Any]]] = None,
    success: bool = False,
    error_message: Optional[str] = None,
    screenshot_path: Optional[str] = None
) -> int:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    now_str = datetime.now().isoformat()
    cursor.execute("""
    INSERT INTO tasks (instruction, plan_json, results_json, success, error_message, screenshot_path, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        instruction,
        json.dumps(plan) if plan else None,
        json.dumps(results) if results else None,
        1 if success else 0,
        error_message,
        screenshot_path,
        now_str
    ))
    task_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return task_id

def update_task(
    task_id: int,
    results: Optional[List[Dict[str, Any]]] = None,
    success: bool = False,
    error_message: Optional[str] = None,
    screenshot_path: Optional[str] = None
):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE tasks
    SET results_json = ?, success = ?, error_message = ?, screenshot_path = ?
    WHERE id = ?
    """, (
        json.dumps(results) if results else None,
        1 if success else 0,
        error_message,
        screenshot_path,
        task_id
    ))
    conn.commit()
    conn.close()

def get_task_history(limit: int = 50) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
    SELECT * FROM tasks ORDER BY id DESC LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    history = []
    for r in rows:
        history.append({
            "id": r["id"],
            "instruction": r["instruction"],
            "plan": json.loads(r["plan_json"]) if r["plan_json"] else None,
            "results": json.loads(r["results_json"]) if r["results_json"] else [],
            "success": bool(r["success"]),
            "error_message": r["error_message"],
            "screenshot_path": r["screenshot_path"],
            "created_at": r["created_at"]
        })
    conn.close()
    return history

