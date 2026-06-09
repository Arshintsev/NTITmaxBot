"""Профиль пользователя MAX (ФИО, телефон, ПК) в SQLite."""

from typing import Any, Optional

from app.data.instance import db


def get_profile(max_user_id: int) -> Optional[dict[str, Any]]:
    return db.get_user_profile(max_user_id)


def has_complete_profile(max_user_id: int) -> bool:
    return db.profile_is_complete(get_profile(max_user_id))


def profile_context_payload(profile: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if profile.get("contact_name"):
        payload["name"] = profile["contact_name"]
    if profile.get("phone"):
        payload["phone"] = profile["phone"]
    if profile.get("pc_name"):
        payload["pc_name"] = profile["pc_name"]
    if profile.get("pyrus_user_id"):
        payload["client_task_id"] = profile["pyrus_user_id"]
    return payload


def company_context_payload(profile: dict[str, Any]) -> dict[str, Any]:
    """ИНН и контрагент из сохранённого профиля."""
    payload: dict[str, Any] = {}
    if profile.get("inn"):
        payload["inn"] = profile["inn"]
    if profile.get("company_name"):
        payload["company_name"] = profile["company_name"]
    if profile.get("pyrus_contractor_task_id"):
        payload["contractor_id"] = profile["pyrus_contractor_task_id"]
    return payload


def ticket_start_context_payload(profile: dict[str, Any]) -> dict[str, Any]:
    return {**profile_context_payload(profile), **company_context_payload(profile)}


def has_saved_company(profile: Optional[dict[str, Any]]) -> bool:
    """Пользователь уже вводил валидный ИНН — контрагент найден в Pyrus."""
    if not profile:
        return False
    return bool(profile.get("inn") and profile.get("pyrus_contractor_task_id"))


def save_profile(
    *,
    max_user_id: int,
    contact_name: Optional[str] = None,
    phone: Optional[str] = None,
    pc_name: Optional[str] = None,
    pyrus_user_id: Optional[int] = None,
    pyrus_contractor_task_id: Optional[int] = None,
    inn: Optional[str] = None,
    company_name: Optional[str] = None,
    max_username: Optional[str] = None,
    max_full_name: Optional[str] = None,
) -> None:
    db.upsert_user_link(
        max_user_id=max_user_id,
        contact_name=contact_name,
        phone=phone,
        pc_name=pc_name,
        pyrus_user_id=pyrus_user_id,
        pyrus_contractor_task_id=pyrus_contractor_task_id,
        inn=inn,
        company_name=company_name,
        max_username=max_username,
        max_full_name=max_full_name,
    )


def save_profile_from_ticket_data(
    *,
    max_user_id: int,
    data: dict[str, Any],
    max_username: Optional[str] = None,
    max_full_name: Optional[str] = None,
) -> None:
    save_profile(
        max_user_id=max_user_id,
        contact_name=data.get("name"),
        phone=data.get("phone"),
        pc_name=data.get("pc_name"),
        pyrus_user_id=data.get("client_task_id"),
        pyrus_contractor_task_id=data.get("contractor_id"),
        inn=data.get("inn"),
        company_name=data.get("company_name"),
        max_username=max_username,
        max_full_name=max_full_name,
    )
