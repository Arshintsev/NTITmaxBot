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

# Закрытая / открытая заявка в боте (поле «Статус» в Pyrus).
TICKET_CLOSED_STATUS = "Решена"
TICKET_OPEN_STATUS = "Открыта"


def is_ticket_closed(status: Optional[str]) -> bool:
    return (status or "").strip() == TICKET_CLOSED_STATUS


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
        self._ensure_user_link_columns()
        self._ensure_ticket_closure_column()

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

    def _ensure_user_link_columns(self) -> None:
        required_columns: dict[str, str] = {
            "contact_name": "TEXT",
            "phone": "TEXT",
            "pc_name": "TEXT",
        }
        with self._get_conn() as conn:
            existing = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(user_links)").fetchall()
            }
            for col_name, col_type in required_columns.items():
                if col_name in existing:
                    continue
                conn.execute(f"ALTER TABLE user_links ADD COLUMN {col_name} {col_type}")

    def get_user_profile(self, max_user_id: int) -> Optional[dict[str, Any]]:
        with self._get_conn() as conn:
            row = conn.execute(
                """
                SELECT
                    max_user_id,
                    max_username,
                    max_full_name,
                    contact_name,
                    phone,
                    pc_name,
                    pyrus_user_id,
                    pyrus_contractor_task_id,
                    inn,
                    company_name
                FROM user_links
                WHERE max_user_id = ?
                """,
                (max_user_id,),
            ).fetchone()
        return dict(row) if row else None

    @staticmethod
    def profile_is_complete(profile: Optional[dict[str, Any]]) -> bool:
        if not profile:
            return False
        return bool(
            profile.get("contact_name")
            and profile.get("phone")
            and profile.get("pc_name")
        )

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
        contact_name: Optional[str] = None,
        phone: Optional[str] = None,
        pc_name: Optional[str] = None,
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
                    company_name,
                    contact_name,
                    phone,
                    pc_name
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(max_user_id) DO UPDATE SET
                    max_username=COALESCE(excluded.max_username, user_links.max_username),
                    max_full_name=COALESCE(excluded.max_full_name, user_links.max_full_name),
                    pyrus_user_id=COALESCE(excluded.pyrus_user_id, user_links.pyrus_user_id),
                    pyrus_contractor_task_id=COALESCE(
                        excluded.pyrus_contractor_task_id, user_links.pyrus_contractor_task_id
                    ),
                    inn=COALESCE(excluded.inn, user_links.inn),
                    company_name=COALESCE(excluded.company_name, user_links.company_name),
                    contact_name=COALESCE(excluded.contact_name, user_links.contact_name),
                    phone=COALESCE(excluded.phone, user_links.phone),
                    pc_name=COALESCE(excluded.pc_name, user_links.pc_name),
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
                    contact_name,
                    phone,
                    pc_name,
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
        closed = is_ticket_closed(status)
        resolved_at = "CURRENT_TIMESTAMP" if closed else "NULL"
        with self._get_conn() as conn:
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
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, {resolved_at})
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

    def get_open_tickets_by_user(self, max_user_id: int) -> list[dict[str, Any]]:
        with self._get_conn() as conn:
            rows = conn.execute(
                """
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
                  AND COALESCE(status, '') != ?
                ORDER BY updated_at DESC
                """,
                (max_user_id, TICKET_CLOSED_STATUS),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_unresolved_tickets_by_user(self, max_user_id: int) -> list[dict[str, Any]]:
        """Открытые заявки (статус не «Решена»)."""
        return self.get_open_tickets_by_user(max_user_id)

    def get_recently_closed_tickets_by_user(
        self, max_user_id: int, *, hours: int = 1
    ) -> list[dict[str, Any]]:
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT
                    id,
                    pyrus_task_id,
                    inn,
                    theme_name,
                    status,
                    subject,
                    created_at,
                    updated_at,
                    resolved_at
                FROM tickets
                WHERE max_user_id = ?
                  AND status = ?
                  AND datetime(COALESCE(resolved_at, updated_at))
                      >= datetime('now', ?)
                ORDER BY COALESCE(resolved_at, updated_at) DESC
                """,
                (max_user_id, TICKET_CLOSED_STATUS, f"-{hours} hours"),
            ).fetchall()
        return [dict(row) for row in rows]

    def is_ticket_open_for_user(self, pyrus_task_id: int, max_user_id: int) -> bool:
        with self._get_conn() as conn:
            row = conn.execute(
                """
                SELECT status FROM tickets
                WHERE pyrus_task_id = ? AND max_user_id = ?
                """,
                (pyrus_task_id, max_user_id),
            ).fetchone()
        return bool(row and not is_ticket_closed(row["status"]))

    def list_pyrus_task_ids_by_user(self, max_user_id: int, limit: int = 100) -> list[int]:
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT pyrus_task_id FROM tickets
                WHERE max_user_id = ?
                  AND COALESCE(pyrus_sync_blocked, 0) = 0
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (max_user_id, limit),
            ).fetchall()
        return [int(row["pyrus_task_id"]) for row in rows]

    def list_tickets_for_status_sync(self, limit: int = 80) -> list[dict[str, Any]]:
        """
        Все открытые и все «Решена» — чтобы подхватить переоткрытие в Pyrus.
        """
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT pyrus_task_id, max_user_id
                FROM tickets
                WHERE COALESCE(pyrus_sync_blocked, 0) = 0
                  AND (
                    COALESCE(status, '') != ?
                    OR status = ?
                  )
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (TICKET_CLOSED_STATUS, TICKET_CLOSED_STATUS, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def _ensure_ticket_closure_column(self) -> None:
        with self._get_conn() as conn:
            existing = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(tickets)").fetchall()
            }
            if "closure_notified_at" not in existing:
                conn.execute(
                    "ALTER TABLE tickets ADD COLUMN closure_notified_at TEXT"
                )
            if "pyrus_sync_blocked" not in existing:
                conn.execute(
                    "ALTER TABLE tickets ADD COLUMN pyrus_sync_blocked INTEGER DEFAULT 0"
                )

    def list_tickets_pending_closure_notification(self, limit: int = 40) -> list[dict[str, Any]]:
        """Заявки без уведомления о закрытии и без оценки."""
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT t.pyrus_task_id, t.max_user_id, t.theme_name, t.status
                FROM tickets t
                WHERE t.closure_notified_at IS NULL
                  AND COALESCE(t.pyrus_sync_blocked, 0) = 0
                  AND NOT EXISTS (
                      SELECT 1 FROM ticket_ratings r
                      WHERE r.pyrus_task_id = t.pyrus_task_id
                  )
                ORDER BY t.updated_at ASC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def mark_pyrus_sync_blocked(self, pyrus_task_id: int) -> None:
        """Нет доступа к задаче в API — больше не опрашивать."""
        with self._get_conn() as conn:
            conn.execute(
                """
                UPDATE tickets
                SET pyrus_sync_blocked = 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE pyrus_task_id = ?
                """,
                (pyrus_task_id,),
            )

    def mark_closure_notified(self, pyrus_task_id: int) -> None:
        with self._get_conn() as conn:
            conn.execute(
                """
                UPDATE tickets
                SET closure_notified_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE pyrus_task_id = ?
                """,
                (pyrus_task_id,),
            )

    def is_closure_notified(self, pyrus_task_id: int) -> bool:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT closure_notified_at FROM tickets WHERE pyrus_task_id = ?",
                (pyrus_task_id,),
            ).fetchone()
        return bool(row and row["closure_notified_at"])

    def list_pyrus_task_ids_pending_rating(self, max_user_id: int, limit: int = 25) -> list[int]:
        """Заявки пользователя без записи в ticket_ratings (FIFO по дате создания)."""
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT t.pyrus_task_id
                FROM tickets t
                WHERE t.max_user_id = ?
                  AND NOT EXISTS (
                      SELECT 1 FROM ticket_ratings r
                      WHERE r.pyrus_task_id = t.pyrus_task_id
                  )
                ORDER BY t.created_at ASC
                LIMIT ?
                """,
                (max_user_id, limit),
            ).fetchall()
        return [int(row["pyrus_task_id"]) for row in rows]

    def has_ticket_rating(self, pyrus_task_id: int) -> bool:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM ticket_ratings WHERE pyrus_task_id = ? LIMIT 1",
                (pyrus_task_id,),
            ).fetchone()
        return row is not None

    def get_ticket_by_pyrus_for_user(
        self, pyrus_task_id: int, max_user_id: int
    ) -> Optional[dict[str, Any]]:
        with self._get_conn() as conn:
            row = conn.execute(
                """
                SELECT id, pyrus_task_id, max_user_id, theme_name, status
                FROM tickets
                WHERE pyrus_task_id = ? AND max_user_id = ?
                """,
                (pyrus_task_id, max_user_id),
            ).fetchone()
        return dict(row) if row else None

    def update_ticket_status_from_pyrus(self, pyrus_task_id: int, status: str) -> None:
        """Обновляет статус; «Решена» → resolved_at; открытие → сброс resolved_at и уведомления."""
        status = (status or "").strip()
        closed = is_ticket_closed(status)
        with self._get_conn() as conn:
            conn.execute(
                """
                UPDATE tickets
                SET status = ?,
                    updated_at = CURRENT_TIMESTAMP,
                    resolved_at = CASE
                        WHEN ? = 1 THEN COALESCE(resolved_at, CURRENT_TIMESTAMP)
                        ELSE NULL
                    END,
                    closure_notified_at = CASE
                        WHEN ? = 0 THEN NULL
                        ELSE closure_notified_at
                    END
                WHERE pyrus_task_id = ?
                """,
                (status, 1 if closed else 0, 1 if closed else 0, pyrus_task_id),
            )

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
        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                DELETE FROM tickets
                WHERE status = ?
                  AND datetime(COALESCE(resolved_at, updated_at, created_at))
                      <= datetime('now', ?)
                """,
                (TICKET_CLOSED_STATUS, f"-{days} days"),
            )
            return cursor.rowcount

