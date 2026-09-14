#!/usr/bin/env python
"""
VeriGate Admin Management Utility

Allows administrators or DevOps engineers to securely promote, demote,
create, and list admin users directly via CLI.

Usage:
    python scripts/manage_admin.py list
    python scripts/manage_admin.py promote user@example.com
    python scripts/manage_admin.py demote user@example.com
    python scripts/manage_admin.py create admin@example.com --password "SecurePassword123!" --name "System Admin"
"""

import argparse
import sys
from pathlib import Path

# Add Backend root to path
backend_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_root))

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.user import User
from app.services.audit_service import record_audit_event


def list_users(db):
    users = db.scalars(select(User).order_by(User.created_at.desc())).all()
    print(f"\nTotal users in VeriGate: {len(users)}")
    print("-" * 75)
    print(f"{'Email':<35} {'Role':<10} {'Active':<8} {'Full Name'}")
    print("-" * 75)
    for u in users:
        print(f"{u.email:<35} {u.system_role:<10} {str(u.is_active):<8} {u.full_name or '—'}")
    print("-" * 75)


def promote_user(db, email: str):
    email_clean = email.strip().lower()
    user = db.scalar(select(User).where(User.email == email_clean))
    if not user:
        print(f"Error: User with email '{email_clean}' not found.")
        sys.exit(1)

    if user.system_role == "admin":
        print(f"Notice: User '{email_clean}' is already an admin.")
        return

    user.system_role = "admin"
    record_audit_event(
        db,
        user_id=user.id,
        action="user_role_changed",
        resource_type="user",
        resource_id=user.id,
        description=f"CLI promoted {email_clean} to admin",
    )
    db.commit()
    print(f"Success: User '{email_clean}' has been promoted to ADMIN.")


def demote_user(db, email: str):
    email_clean = email.strip().lower()
    user = db.scalar(select(User).where(User.email == email_clean))
    if not user:
        print(f"Error: User with email '{email_clean}' not found.")
        sys.exit(1)

    if user.system_role == "user":
        print(f"Notice: User '{email_clean}' is already a regular user.")
        return

    user.system_role = "user"
    record_audit_event(
        db,
        user_id=user.id,
        action="user_role_changed",
        resource_type="user",
        resource_id=user.id,
        description=f"CLI demoted {email_clean} to user",
    )
    db.commit()
    print(f"Success: User '{email_clean}' has been demoted to USER.")


def create_admin(db, email: str, password: str, full_name: str | None):
    email_clean = email.strip().lower()
    existing = db.scalar(select(User).where(User.email == email_clean))
    if existing:
        print(f"Error: User with email '{email_clean}' already exists. Use 'promote' instead.")
        sys.exit(1)

    if len(password) < 8:
        print("Error: Password must be at least 8 characters long.")
        sys.exit(1)

    admin_user = User(
        email=email_clean,
        password_hash=hash_password(password),
        full_name=full_name or "System Administrator",
        system_role="admin",
        is_active=True,
    )
    db.add(admin_user)
    db.commit()
    db.refresh(admin_user)

    record_audit_event(
        db,
        user_id=admin_user.id,
        action="user_created",
        resource_type="user",
        resource_id=admin_user.id,
        description=f"CLI created new admin user {email_clean}",
    )
    db.commit()
    print(f"Success: Admin account '{email_clean}' created successfully.")


def main():
    parser = argparse.ArgumentParser(description="VeriGate Admin Management Utility")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # list
    subparsers.add_parser("list", help="List all users and their system roles")

    # promote
    promote_parser = subparsers.add_parser("promote", help="Promote an existing user to admin")
    promote_parser.add_argument("email", help="Email of the user to promote")

    # demote
    demote_parser = subparsers.add_parser("demote", help="Demote an admin to normal user")
    demote_parser.add_argument("email", help="Email of the user to demote")

    # create
    create_parser = subparsers.add_parser("create", help="Create a new admin user")
    create_parser.add_argument("email", help="Email of the new admin user")
    create_parser.add_argument("--password", required=True, help="Initial password (min 8 characters)")
    create_parser.add_argument("--name", default="System Administrator", help="Full name")

    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.command == "list":
            list_users(db)
        elif args.command == "promote":
            promote_user(db, args.email)
        elif args.command == "demote":
            demote_user(db, args.email)
        elif args.command == "create":
            create_admin(db, args.email, args.password, args.name)
    finally:
        db.close()


if __name__ == "__main__":
    main()
