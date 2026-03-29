from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260329_000001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pipeline_runs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("trigger", sa.String(length=32), nullable=False, server_default="manual"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="running"),
        sa.Column("total_sources", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sources_succeeded", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sources_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_items_collected", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_items_qualified", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_items_saved", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("digest_path", sa.String(length=1024), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
    )
    op.create_index("ix_pipeline_runs_started_at", "pipeline_runs", ["started_at"])
    op.create_index("ix_pipeline_runs_status", "pipeline_runs", ["status"])

    op.create_table(
        "opportunities",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("source_name", sa.String(length=255), nullable=False),
        sa.Column("link", sa.String(length=1024), nullable=False),
        sa.Column("application_url", sa.String(length=1024), nullable=True),
        sa.Column("deadline", sa.Date(), nullable=True),
        sa.Column("event_date", sa.Date(), nullable=True),
        sa.Column("country", sa.String(length=64), nullable=True),
        sa.Column("region", sa.String(length=128), nullable=True),
        sa.Column("city", sa.String(length=128), nullable=True),
        sa.Column("audience_scope", sa.String(length=32), nullable=False, server_default="africa"),
        sa.Column("issuer_name", sa.String(length=255), nullable=True),
        sa.Column("issuer_type", sa.String(length=64), nullable=True),
        sa.Column("location_text", sa.String(length=255), nullable=True),
        sa.Column("language", sa.String(length=32), nullable=False, server_default="en"),
        sa.Column("source_priority", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("africa_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("locality_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("relevance_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("total_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("date_found", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("whatsapp_short", sa.Text(), nullable=False, server_default=""),
        sa.Column("whatsapp_detailed", sa.Text(), nullable=False, server_default=""),
        sa.Column("whatsapp_channel", sa.Text(), nullable=False, server_default=""),
        sa.UniqueConstraint("link", name="uq_opportunities_link"),
    )
    op.create_index("ix_opportunities_link", "opportunities", ["link"], unique=True)
    op.create_index("ix_opportunities_country", "opportunities", ["country"])
    op.create_index("ix_opportunities_audience_scope", "opportunities", ["audience_scope"])

    op.create_table(
        "source_runs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("pipeline_run_id", sa.Integer(), nullable=False),
        sa.Column("source_name", sa.String(length=255), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_url", sa.String(length=1024), nullable=False),
        sa.Column("strategy", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="running"),
        sa.Column("items_collected", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("items_qualified", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("items_saved", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["pipeline_run_id"], ["pipeline_runs.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_source_runs_pipeline_run_id", "source_runs", ["pipeline_run_id"])
    op.create_index("ix_source_runs_source_name", "source_runs", ["source_name"])
    op.create_index("ix_source_runs_started_at", "source_runs", ["started_at"])
    op.create_index("ix_source_runs_status", "source_runs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_source_runs_status", table_name="source_runs")
    op.drop_index("ix_source_runs_started_at", table_name="source_runs")
    op.drop_index("ix_source_runs_source_name", table_name="source_runs")
    op.drop_index("ix_source_runs_pipeline_run_id", table_name="source_runs")
    op.drop_table("source_runs")

    op.drop_index("ix_opportunities_audience_scope", table_name="opportunities")
    op.drop_index("ix_opportunities_country", table_name="opportunities")
    op.drop_index("ix_opportunities_link", table_name="opportunities")
    op.drop_table("opportunities")

    op.drop_index("ix_pipeline_runs_status", table_name="pipeline_runs")
    op.drop_index("ix_pipeline_runs_started_at", table_name="pipeline_runs")
    op.drop_table("pipeline_runs")
