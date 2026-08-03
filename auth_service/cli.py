"""Administrative commands. Admin accounts are never created through public signup."""

from __future__ import annotations

import argparse
import getpass

from email_validator import EmailNotValidError, validate_email

from auth_service.config import Settings
from auth_service.database import build_engine, build_session_factory, initialize_database
from auth_service.models import ApprovalAction, ApprovalEvent
from auth_service.operations import apply_password_reset, create_admin_user, find_user_by_identifier


def create_admin(
    username: str,
    full_name: str,
    password: str | None,
    email: str | None = None,
) -> int:
    normalized_email = None
    if email:
        try:
            normalized_email = validate_email(email, check_deliverability=False).normalized
        except EmailNotValidError as exc:
            print(f"올바른 이메일을 입력해 주세요: {exc}")
            return 2

    actual_password = password or getpass.getpass("관리자 비밀번호: ")
    if len(actual_password) < 12:
        print("관리자 비밀번호는 12자 이상이어야 합니다.")
        return 2

    settings = Settings.from_env()
    engine = build_engine(settings.database_url)
    initialize_database(engine)
    session_factory = build_session_factory(engine)
    try:
        with session_factory() as db:
            user = create_admin_user(
                db,
                username=username,
                email=normalized_email,
                password=actual_password,
                full_name=full_name,
            )
        print(f"관리자 계정을 생성했습니다: {user.username}")
        return 0
    except ValueError as exc:
        print(str(exc))
        return 1
    finally:
        engine.dispose()


def reset_password(identifier: str, password: str | None) -> int:
    actual_password = password or getpass.getpass("새 비밀번호: ")
    if len(actual_password) < 10:
        print("비밀번호는 10자 이상이어야 합니다.")
        return 2

    settings = Settings.from_env()
    engine = build_engine(settings.database_url)
    initialize_database(engine)
    session_factory = build_session_factory(engine)
    try:
        with session_factory() as db:
            user = find_user_by_identifier(db, identifier)
            if user is None:
                print(f"계정을 찾을 수 없습니다: {identifier}")
                return 1
            apply_password_reset(db, user=user, new_password=actual_password)
            db.add(
                ApprovalEvent(
                    user_id=user.id,
                    actor_user_id=user.id,
                    action=ApprovalAction.PASSWORD_RESET.value,
                    previous_role=user.access_role,
                    new_role=user.access_role,
                    note="서버 CLI에서 비밀번호 재설정",
                )
            )
            db.commit()
        print(f"비밀번호를 재설정했습니다: {identifier}")
        return 0
    finally:
        engine.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(description="인증 서비스 관리 명령")
    subparsers = parser.add_subparsers(dest="command", required=True)
    create_parser = subparsers.add_parser("create-admin", help="관리자 계정 생성")
    create_parser.add_argument("--username", required=True)
    create_parser.add_argument("--email")
    create_parser.add_argument("--name", required=True)
    create_parser.add_argument("--password", help="생략하면 화면에 노출되지 않게 입력")

    reset_parser = subparsers.add_parser("reset-password", help="계정 비밀번호 재설정 (관리자 계정 포함)")
    reset_parser.add_argument("--identifier", required=True, help="아이디 또는 이메일")
    reset_parser.add_argument("--password", help="생략하면 화면에 노출되지 않게 입력")

    args = parser.parse_args()
    if args.command == "create-admin":
        return create_admin(args.username, args.name, args.password, args.email)
    if args.command == "reset-password":
        return reset_password(args.identifier, args.password)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
