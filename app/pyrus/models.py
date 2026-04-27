# app/pyrus/models.py

from dataclasses import dataclass
from typing import Optional, List


@dataclass
class PyrusComment:
    id: int
    author_name: Optional[str]
    text: Optional[str]
    created_at: Optional[str]


@dataclass
class PyrusTask:
    id: int
    title: Optional[str] = None

    inn: Optional[str] = None
    name: Optional[str] = None
    phone: Optional[str] = None
    pc_name: Optional[str] = None
    problem: Optional[str] = None

    status: Optional[str] = None

    comments: List[PyrusComment] = None