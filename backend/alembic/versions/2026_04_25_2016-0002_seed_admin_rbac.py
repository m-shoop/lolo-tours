"""seed admin role and tour management permissions

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-25

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


PERMISSIONS = [
    ("tour-template:edit", "Create and edit tour templates"),
    ("tour-slot:edit", "Create and edit tour slots"),
    ("tour-slot:view", "View the tour slots page"),
    ("tour-image:edit", "Upload, edit, and delete tour images"),
]


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO roles (name, description)
        VALUES ('admin', 'Full administrative access to tour management')
        """
    )

    for name, description in PERMISSIONS:
        op.execute(
            f"""
            INSERT INTO permissions (name, description)
            VALUES ('{name}', '{description}')
            """
        )

    op.execute(
        """
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r
        CROSS JOIN permissions p
        WHERE r.name = 'admin'
          AND p.name IN ('tour-template:edit', 'tour-slot:edit', 'tour-slot:view', 'tour-image:edit')
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM role_permissions
        WHERE role_id IN (SELECT id FROM roles WHERE name = 'admin')
           OR permission_id IN (
               SELECT id FROM permissions
               WHERE name IN ('tour-template:edit', 'tour-slot:edit', 'tour-slot:view', 'tour-image:edit')
           )
        """
    )
    op.execute(
        """
        DELETE FROM permissions
        WHERE name IN ('tour-template:edit', 'tour-slot:edit', 'tour-slot:view', 'tour-image:edit')
        """
    )
    op.execute("DELETE FROM roles WHERE name = 'admin'")
