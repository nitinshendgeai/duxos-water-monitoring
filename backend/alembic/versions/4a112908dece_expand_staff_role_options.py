"""expand staff role options

Revision ID: 4a112908dece
Revises: d23d407245e2
Create Date: 2026-08-06 00:25:57.745949

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4a112908dece'
down_revision: Union[str, None] = 'd23d407245e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint('ck_staff_role', 'staff', type_='check')
    op.alter_column('staff', 'role',
               existing_type=sa.VARCHAR(length=20),
               type_=sa.String(length=30),
               existing_nullable=False)
    op.create_check_constraint(
        'ck_staff_role',
        'staff',
        "role IN ('security','technical','manager','gym_attendant',"
        "'security_supervisor','housekeeping_supervisor')",
    )


def downgrade() -> None:
    op.drop_constraint('ck_staff_role', 'staff', type_='check')
    op.alter_column('staff', 'role',
               existing_type=sa.String(length=30),
               type_=sa.VARCHAR(length=20),
               existing_nullable=False)
    op.create_check_constraint(
        'ck_staff_role',
        'staff',
        "role IN ('security','technical','manager','gym_attendant')",
    )
