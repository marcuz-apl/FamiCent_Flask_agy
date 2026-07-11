"""Database viewer (Looker) blueprint.

Accessible only to admin users. Provides read-only query capabilities and table browsing.
"""
from __future__ import annotations

import logging
import sqlite3
from flask import Blueprint, render_template, request, session, abort, jsonify
from famicent.auth.routes import login_required, mfa_required, admin_required, _validate_csrf
from famicent.db.engine import _DEFAULT_DB_PATH

logger = logging.getLogger(__name__)

dbviewer_bp = Blueprint("dbviewer", __name__, url_prefix="/dbviewer")

def _query_db(query: str, args: list = None) -> tuple[list[str], list[tuple]]:
    """Execute a raw SQL query on the local sqlite database in read-only mode."""
    # Connect using a read-only URI to ensure safety
    db_uri = f"file:{_DEFAULT_DB_PATH}?mode=ro"
    conn = sqlite3.connect(db_uri, uri=True)
    cursor = conn.cursor()
    try:
        cursor.execute(query, args or [])
        columns = [col[0] for col in cursor.description] if cursor.description else []
        rows = cursor.fetchall()
        return columns, rows
    finally:
        conn.close()

@dbviewer_bp.route("/", methods=["GET"])
@login_required
@mfa_required
@admin_required
def index():
    """Render the main database Looker panel."""
    # Fetch list of user tables
    tables = []
    try:
        _, rows = _query_db("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        tables = [r[0] for r in rows]
    except Exception as e:
        logger.error("Failed to fetch tables list: %s", e)

    selected_table = request.args.get("table")
    columns = []
    data = []
    error = None

    if selected_table and selected_table in tables:
        try:
            columns, raw_data = _query_db(f"SELECT * FROM [{selected_table}] LIMIT 100;")
            # Convert raw bytes cells to placeholders so Jinja doesn't need to test for bytes type
            for row in raw_data:
                processed_row = []
                for cell in row:
                    if isinstance(cell, bytes):
                        processed_row.append(f"<Binary data: {len(cell)} bytes>")
                    else:
                        processed_row.append(cell)
                data.append(processed_row)
        except Exception as e:
            error = str(e)

    return render_template(
        "dbviewer.html",
        tables=tables,
        selected_table=selected_table,
        columns=columns,
        data=data,
        error=error,
        csrf_token=session.get("csrf_token", ""),
    )

@dbviewer_bp.route("/query", methods=["POST"])
@login_required
@mfa_required
@admin_required
def custom_query():
    """Execute a custom SQL SELECT statement in read-only mode."""
    _validate_csrf()
    sql = request.form.get("sql", "").strip()
    if not sql:
        return jsonify({"success": False, "error": "Query cannot be empty."}), 400

    # Strict protection: Only allow SELECT statements
    clean_sql = sql.strip().lower()
    if "select" not in clean_sql:
        return jsonify({"success": False, "error": "Only SELECT queries are allowed."}), 400

    forbidden = ["insert", "update", "delete", "drop", "alter", "create", "replace", "vacuum", "pragma"]
    # Check word boundaries rather than raw substring or strict splits
    import re
    words = re.findall(r'\b[a-z_]+\b', clean_sql)
    if any(keyword in words for keyword in forbidden):
        return jsonify({"success": False, "error": "Write operations are forbidden. Read-only queries only."}), 400

    try:
        columns, rows = _query_db(sql)
        # Convert rows (which contain bytes) to string representation if they are BLOBs (like passwords, keys)
        processed_rows = []
        for r in rows:
            processed_row = []
            for cell in r:
                if isinstance(cell, bytes):
                    # Show preview size of binary data
                    processed_row.append(f"<Binary data: {len(cell)} bytes>")
                else:
                    processed_row.append(cell)
            processed_rows.append(processed_row)

        return jsonify({
            "success": True,
            "columns": columns,
            "rows": processed_rows
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400
