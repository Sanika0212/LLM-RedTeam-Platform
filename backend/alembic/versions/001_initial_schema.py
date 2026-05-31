"""Initial schema — users, llm_models, evaluations, evaluation_results, attack_prompts

Revision ID: 001
Revises: None
Create Date: 2026-02-15
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True, index=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), server_default=""),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1")),
        sa.Column("is_admin", sa.Boolean(), server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    op.create_table(
        "llm_models",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("provider", sa.String(100), nullable=False),
        sa.Column("model_id", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column("api_endpoint", sa.String(500), server_default=""),
        sa.Column("safety_score", sa.Float(), server_default="0.0"),
        sa.Column("robustness_score", sa.Float(), server_default="0.0"),
        sa.Column("total_evaluations", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    op.create_table(
        "evaluations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column("model_id", sa.Integer(), sa.ForeignKey("llm_models.id"), nullable=False),
        sa.Column("eval_type", sa.String(100), nullable=False),
        sa.Column("status", sa.String(50), server_default="pending"),
        sa.Column("config", sa.JSON(), nullable=True),
        sa.Column("total_prompts", sa.Integer(), server_default="0"),
        sa.Column("completed_prompts", sa.Integer(), server_default="0"),
        sa.Column("safety_score", sa.Float(), server_default="0.0"),
        sa.Column("robustness_score", sa.Float(), server_default="0.0"),
        sa.Column("jailbreak_rate", sa.Float(), server_default="0.0"),
        sa.Column("hallucination_rate", sa.Float(), server_default="0.0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "evaluation_results",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("evaluation_id", sa.Integer(), sa.ForeignKey("evaluations.id"), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("response", sa.Text(), server_default=""),
        sa.Column("attack_type", sa.String(100), server_default=""),
        sa.Column("is_jailbroken", sa.Integer(), server_default="0"),
        sa.Column("toxicity_score", sa.Float(), server_default="0.0"),
        sa.Column("coherence_score", sa.Float(), server_default="0.0"),
        sa.Column("refusal_detected", sa.Integer(), server_default="0"),
        sa.Column("extra_data", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    op.create_table(
        "attack_prompts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("subcategory", sa.String(100), server_default=""),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(50), server_default="medium"),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column("expected_behavior", sa.String(100), server_default="refusal"),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("attack_prompts")
    op.drop_table("evaluation_results")
    op.drop_table("evaluations")
    op.drop_table("llm_models")
    op.drop_table("users")
