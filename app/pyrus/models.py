from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass
class PyrusComment:
    id: int
    author_name: Optional[str]
    text: Optional[str]
    created_at: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        """Сериализация комментария"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PyrusComment':
        """Десериализация комментария"""
        return cls(**data)


@dataclass
class PyrusTask:
    """Модель задачи из Pyrus"""
    id: int
    title: Optional[str] = None

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    inn: Optional[str] = None
    name: Optional[str] = None
    phone: Optional[str] = None
    pc_name: Optional[str] = None
    problem: Optional[str] = None
    max_id: Optional[int] = None
    pyrus_user_id: Optional[int] = None
    pyrus_task_id: Optional[int] = None

    status: Optional[str] = None

    comments: Optional[List[PyrusComment]] = None  # Исправлено: Optional
    raw_data: Dict[str, Any] = field(default_factory=dict)  # Добавлен импорт field

    def to_dict(self) -> Dict[str, Any]:
        """Сериализация для Redis"""
        data = asdict(self)

        # Преобразуем datetime в строку
        if isinstance(data.get('created_at'), datetime):
            data['created_at'] = data['created_at'].isoformat()
        if isinstance(data.get('updated_at'), datetime):
            data['updated_at'] = data['updated_at'].isoformat()

        # Сериализуем комментарии, если они есть
        if data.get('comments'):
            data['comments'] = [
                comment.to_dict() if isinstance(comment, PyrusComment) else comment
                for comment in data['comments']
            ]

        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PyrusTask':
        """Десериализация из Redis"""
        # Восстанавливаем datetime
        if data.get('created_at'):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if data.get('updated_at'):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])

        # Восстанавливаем комментарии
        if data.get('comments'):
            data['comments'] = [
                PyrusComment.from_dict(comment) if isinstance(comment, dict) else comment
                for comment in data['comments']
            ]

        return cls(**data)

    def add_comment(self, comment: PyrusComment) -> None:
        """Добавить комментарий к задаче"""
        if self.comments is None:
            self.comments = []
        self.comments.append(comment)

    def get_last_comment(self) -> Optional[PyrusComment]:
        """Получить последний комментарий"""
        if self.comments:
            return self.comments[-1]
        return None

    def __repr__(self) -> str:
        return f"PyrusTask(id={self.id}, title={self.title[:50] if self.title else 'None'}...)"


@dataclass
class CacheMetadata:
    """Метаданные кэша"""
    last_sync: datetime
    total_tasks: int
    version: str = "1.0"

    def to_dict(self) -> Dict[str, Any]:
        return {
            'last_sync': self.last_sync.isoformat(),
            'total_tasks': self.total_tasks,
            'version': self.version
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CacheMetadata':
        data['last_sync'] = datetime.fromisoformat(data['last_sync'])
        return cls(**data)