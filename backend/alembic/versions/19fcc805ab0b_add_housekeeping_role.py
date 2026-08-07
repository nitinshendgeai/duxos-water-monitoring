"""add housekeeping role

Revision ID: 19fcc805ab0b
Revises: 4a112908dece
Create Date: 2026-08-07 18:06:32.515996

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "19fcc805ab0b"
down_revision: Union[str, None] = "4a112908dece"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("ck_staff_role", "staff", type_="check")
    op.create_check_constraint(
        "ck_staff_role",
        "staff",
        "role IN ('security','technical','manager','gym_attendant',"
        "'security_supervisor','housekeeping_supervisor','housekeeping')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_staff_role", "staff", type_="check")
    op.create_check_constraint(
        "ck_staff_role",
        "staff",
        "role IN ('security','technical','manager','gym_attendant',"
        "'security_supervisor','housekeeping_supervisor')",
    )
