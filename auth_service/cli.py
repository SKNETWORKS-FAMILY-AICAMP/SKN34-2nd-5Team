"""Administrative commands. Admin accounts are never created through public signup."""

from __future__ import annotations

import argparse
import getpass

from email_validator import EmailNotValidError, validate_email

from auth_service.config import Settings
from auth_service.database import build_engine, build_session_factory, initialize_database
from auth_service.operations import create_admin_user


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


def main() -> int:
    parser = argparse.ArgumentParser(description="인증 서비스 관리 명령")
    subparsers = parser.add_subparsers(dest="command", required=True)
    create_parser = subparsers.add_parser("create-admin", help="관리자 계정 생성")
    create_parser.add_argument("--username", required=True)
    create_parser.add_argument("--email")
    create_parser.add_argument("--name", required=True)
    create_parser.add_argument("--password", help="생략하면 화면에 노출되지 않게 입력")
    args = parser.parse_args()
    if args.command == "create-admin":
        return create_admin(args.username, args.name, args.password, args.email)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
