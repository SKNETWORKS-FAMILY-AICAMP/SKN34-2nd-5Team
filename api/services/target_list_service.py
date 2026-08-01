"""Transactional persistence for playbook target lists (F-5)."""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine

from api.auth_context import OperatorIdentity


def _iso(value) -> str | None:
    return value.isoformat() if value is not None else None


def _list_json(row: dict, member_user_ids: list[str]) -> dict:
    return {
        "listId": int(row["list_id"]),
        "name": row["name"],
        "decision": row["decision"],
        "modelVersion": row["model_version"],
        "memberUserIds": member_user_ids,
        "memberCount": len(member_user_ids),
        "createdBy": {
            "subject": row["created_by_subject"],
            "name": row["created_by_name"],
        },
        "createdAt": _iso(row["created_at"]),
    }


def list_target_lists(engine: Engine) -> list[dict]:
    with engine.connect() as connection:
        lists = connection.execute(
            text("SELECT * FROM target_lists ORDER BY created_at DESC")
        ).mappings().all()

        list_ids = [int(row["list_id"]) for row in lists]
        members_by_list: dict[int, list[str]] = {list_id: [] for list_id in list_ids}
        if list_ids:
            member_rows = connection.execute(
                text(
                    "SELECT list_id, reviewer_user_id FROM target_list_members "
                    "WHERE list_id IN :list_ids ORDER BY reviewer_user_id"
                ),
                {"list_ids": tuple(list_ids)},
            ).mappings().all()
            for member_row in member_rows:
                members_by_list[int(member_row["list_id"])].append(
                    member_row["reviewer_user_id"]
                )

    return [
        _list_json(row, members_by_list.get(int(row["list_id"]), []))
        for row in lists
    ]


def create_target_list(
    engine: Engine,
    payload: dict,
    operator: OperatorIdentity,
) -> dict:
    members = payload["members"]
    if not members:
        raise ValueError("대상 명단에는 최소 1명이 필요합니다")

    deduped: dict[str, dict] = {}
    for member in members:
        deduped.setdefault(member["user_id"], member)
    duplicates_removed = len(members) - len(deduped)

    with engine.begin() as connection:
        result = connection.execute(
            text(
                """
                INSERT INTO target_lists (
                    name, decision, model_version,
                    created_by_subject, created_by_name
                ) VALUES (
                    :name, :decision, :model_version,
                    :actor_subject, :actor_name
                )
                """
            ),
            {
                "name": payload["name"],
                "decision": payload["decision"],
                "model_version": payload["model_version"],
                "actor_subject": operator.subject,
                "actor_name": operator.name,
            },
        )
        list_id = int(result.lastrowid)

        for member in deduped.values():
            connection.execute(
                text(
                    """
                    INSERT INTO target_list_members (
                        list_id, reviewer_user_id, model_version, sample_id
                    ) VALUES (
                        :list_id, :reviewer_user_id, :model_version, :sample_id
                    )
                    """
                ),
                {
                    "list_id": list_id,
                    "reviewer_user_id": member["user_id"],
                    "model_version": payload["model_version"],
                    "sample_id": member["sample_id"],
                },
            )

        row = connection.execute(
            text("SELECT * FROM target_lists WHERE list_id = :list_id"),
            {"list_id": list_id},
        ).mappings().one()

    result_json = _list_json(row, [member["user_id"] for member in deduped.values()])
    result_json["duplicatesRemoved"] = duplicates_removed
    return result_json


def delete_target_list(engine: Engine, list_id: int) -> bool:
    with engine.begin() as connection:
        result = connection.execute(
            text("DELETE FROM target_lists WHERE list_id = :list_id"),
            {"list_id": list_id},
        )
    return result.rowcount > 0
