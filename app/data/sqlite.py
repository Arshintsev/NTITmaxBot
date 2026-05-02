import sqlite3
from pathlib import Path
from typing import Any, Optional


UNRESOLVED_STATUSES = (
    "Новая",
    "В работе",
    "Ожидание",
    "Открыта",
    "Не решена",
)

CLOSED_STATUSES = (
    "Закрыт",
    "Закрыта",
    "Решена",
    "Выполнена",
)


class BotDB:
    """SQLite-хранилище бота: пользователи, задачи, оценки."""

    def __init__(self, db_path: str = "data/bot.db"):
        self.db_path = Path(db_path)
        self._ensure_parent_dir()
        self._init_db()

    def _ensure_parent_dir(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_db(self) -> None:
        with self._get_conn() as conn:
            # Связка MAX пользователя с Pyrus пользователем/контрагентом.
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_links (
                    max_user_id INTEGER PRIMARY KEY,
                    max_username TEXT,
                    max_full_name TEXT,
                    pyrus_user_id INTEGER,
                    pyrus_contractor_task_id INTEGER,
                    inn TEXT,
                    company_name TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            # Задачи из Pyrus, интересуют в первую очередь нерешенные.
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tickets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pyrus_task_id INTEGER NOT NULL UNIQUE,
                    max_user_id INTEGER NOT NULL,
                    inn TEXT,
                    theme_id TEXT,
                    theme_name TEXT,
                    status TEXT NOT NULL DEFAULT 'Новая',
                    subject TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    resolved_at TEXT,
                    FOREIGN KEY (max_user_id) REFERENCES user_links(max_user_id)
                )
                """
            )

            # Задел под оценку инженера по закрытой заявке.
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ticket_ratings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket_id INTEGER NOT NULL UNIQUE,
                    pyrus_task_id INTEGER NOT NULL UNIQUE,
                    max_user_id INTEGER NOT NULL,
                    engineer_name TEXT,
                    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
                    comment TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE,
                    FOREIGN KEY (max_user_id) REFERENCES user_links(max_user_id)
                )
                """
            )

            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_tickets_max_user_id ON tickets(max_user_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_ticket_ratings_max_user_id ON ticket_ratings(max_user_id)"
            )
        self._ensure_ticket_columns()

    def _ensure_ticket_columns(self) -> None:
        """
        Добавляет новые колонки в tickets для обратной совместимости
        со старыми БД без мигратора.
        """
        required_columns: dict[str, str] = {
            "phone": "TEXT",
            "pc_name": "TEXT",
            "problem": "TEXT",
            "company_name": "TEXT",
            "contractor_id": "INTEGER",
            "client_task_id": "INTEGER",
            "payload_json": "TEXT",
        }
        with self._get_conn() as conn:
            existing = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(tickets)").fetchall()
            }
            for col_name, col_type in required_columns.items():
                if col_name in existing:
                    continue
                conn.execute(f"ALTER TABLE tickets ADD COLUMN {col_name} {col_type}")

    def upsert_user_link(
        self,
        *,
        max_user_id: int,
        pyrus_user_id: Optional[int] = None,
        pyrus_contractor_task_id: Optional[int] = None,
        inn: Optional[str] = None,
        company_name: Optional[str] = None,
        max_username: Optional[str] = None,
        max_full_name: Optional[str] = None,
    ) -> None:
        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT INTO user_links (
                    max_user_id,
                    max_username,
                    max_full_name,
                    pyrus_user_id,
                    pyrus_contractor_task_id,
                    inn,
                    company_name
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(max_user_id) DO UPDATE SET
                    max_username=excluded.max_username,
                    max_full_name=excluded.max_full_name,
                    pyrus_user_id=COALESCE(excluded.pyrus_user_id, user_links.pyrus_user_id),
                    pyrus_contractor_task_id=COALESCE(excluded.pyrus_contractor_task_id, user_links.pyrus_contractor_task_id),
                    inn=COALESCE(excluded.inn, user_links.inn),
                    company_name=COALESCE(excluded.company_name, user_links.company_name),
                    updated_at=CURRENT_TIMESTAMP
                """,
                (
                    max_user_id,
                    max_username,
                    max_full_name,
                    pyrus_user_id,
                    pyrus_contractor_task_id,
                    inn,
                    company_name,
                ),
            )

    def create_or_update_ticket(
        self,
        *,
        pyrus_task_id: int,
        max_user_id: int,
        status: str,
        inn: Optional[str] = None,
        theme_id: Optional[str] = None,
        theme_name: Optional[str] = None,
        subject: Optional[str] = None,
        phone: Optional[str] = None,
        pc_name: Optional[str] = None,
        problem: Optional[str] = None,
        company_name: Optional[str] = None,
        contractor_id: Optional[int] = None,
        client_task_id: Optional[int] = None,
        payload_json: Optional[str] = None,
    ) -> None:
        with self._get_conn() as conn:
            resolved_at = "CURRENT_TIMESTAMP" if status not in UNRESOLVED_STATUSES else "NULL"
            conn.execute(
                f"""
                INSERT INTO tickets (
                    pyrus_task_id,
                    max_user_id,
                    inn,
                    theme_id,
                    theme_name,
                    status,
                    subject,
                    phone,
                    pc_name,
                    problem,
                    company_name,
                    contractor_id,
                    client_task_id,
                    payload_json,
                    resolved_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, {resolved_at})
                ON CONFLICT(pyrus_task_id) DO UPDATE SET
                    max_user_id=excluded.max_user_id,
                    inn=excluded.inn,
                    theme_id=excluded.theme_id,
                    theme_name=excluded.theme_name,
                    status=excluded.status,
                    subject=excluded.subject,
                    phone=excluded.phone,
                    pc_name=excluded.pc_name,
                    problem=excluded.problem,
                    company_name=excluded.company_name,
                    contractor_id=excluded.contractor_id,
                    client_task_id=excluded.client_task_id,
                    payload_json=excluded.payload_json,
                    updated_at=CURRENT_TIMESTAMP,
                    resolved_at={resolved_at}
                """,
                (
                    pyrus_task_id,
                    max_user_id,
                    inn,
                    theme_id,
                    theme_name,
                    status,
                    subject,
                    phone,
                    pc_name,
                    problem,
                    company_name,
                    contractor_id,
                    client_task_id,
                    payload_json,
                ),
            )

    def get_unresolved_tickets_by_user(self, max_user_id: int) -> list[dict[str, Any]]:
        placeholders = ",".join("?" for _ in UNRESOLVED_STATUSES)
        with self._get_conn() as conn:
            rows = conn.execute(
                f"""
                SELECT
                    id,
                    pyrus_task_id,
                    inn,
                    theme_name,
                    status,
                    subject,
                    created_at,
                    updated_at
                FROM tickets
                WHERE max_user_id = ?
                  AND status IN ({placeholders})
                ORDER BY updated_at DESC
                """,
                (max_user_id, *UNRESOLVED_STATUSES),
            ).fetchall()
        return [dict(row) for row in rows]

    def save_ticket_rating(
        self,
        *,
        pyrus_task_id: int,
        max_user_id: int,
        rating: int,
        engineer_name: Optional[str] = None,
        comment: Optional[str] = None,
    ) -> None:
        with self._get_conn() as conn:
            ticket = conn.execute(
                "SELECT id FROM tickets WHERE pyrus_task_id = ?",
                (pyrus_task_id,),
            ).fetchone()
            if ticket is None:
                raise ValueError("Нельзя сохранить оценку: задача не найдена в локальной БД")

            conn.execute(
                """
                INSERT INTO ticket_ratings (
                    ticket_id,
                    pyrus_task_id,
                    max_user_id,
                    engineer_name,
                    rating,
                    comment
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(pyrus_task_id) DO UPDATE SET
                    max_user_id=excluded.max_user_id,
                    engineer_name=excluded.engineer_name,
                    rating=excluded.rating,
                    comment=excluded.comment
                """,
                (ticket["id"], pyrus_task_id, max_user_id, engineer_name, rating, comment),
            )

    def delete_old_closed_tickets(self, days: int = 60) -> int:
        """
        Удаляет из БД закрытые заявки старше указанного количества дней.
        Возвращает количество удаленных строк.
        """
        placeholders = ",".join("?" for _ in CLOSED_STATUSES)
        with self._get_conn() as conn:
            cursor = conn.execute(
                f"""
                DELETE FROM tickets
                WHERE status IN ({placeholders})
                  AND datetime(COALESCE(resolved_at, updated_at, created_at))
                      <= datetime('now', ?)
                """,
                (*CLOSED_STATUSES, f"-{days} days"),
            )
            return cursor.rowcount

