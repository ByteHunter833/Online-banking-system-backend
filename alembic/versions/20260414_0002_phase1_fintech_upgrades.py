"""Phase 1 fintech backend upgrades."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260414_0002"
down_revision = "20260402_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("family_id", sa.String(length=120), nullable=False),
        sa.Column("device_id", sa.String(length=120), nullable=True),
        sa.Column("device_name", sa.String(length=255), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_user_sessions_user_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_user_sessions"),
        sa.UniqueConstraint("family_id", name="uq_user_sessions_family_id"),
    )
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"], unique=False)
    op.create_index("ix_user_sessions_family_id", "user_sessions", ["family_id"], unique=False)
    op.create_index("ix_user_sessions_device_id", "user_sessions", ["device_id"], unique=False)
    op.create_index("ix_user_sessions_status", "user_sessions", ["status"], unique=False)

    op.create_table(
        "trusted_devices",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("device_id", sa.String(length=120), nullable=False),
        sa.Column("device_name", sa.String(length=255), nullable=True),
        sa.Column("last_ip_hash", sa.String(length=255), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trusted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_trusted_devices_user_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_trusted_devices"),
        sa.UniqueConstraint("user_id", "device_id", name="uq_trusted_devices_user_device"),
    )
    op.create_index("ix_trusted_devices_user_id", "trusted_devices", ["user_id"], unique=False)

    op.create_table(
        "mfa_secrets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("encrypted_secret", sa.String(length=512), nullable=False),
        sa.Column("primary_method", sa.String(length=32), nullable=False, server_default="totp"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("recovery_code_hashes", sa.JSON(), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_mfa_secrets_user_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_mfa_secrets"),
        sa.UniqueConstraint("user_id", "status", name="uq_mfa_secrets_user_status"),
    )
    op.create_index("ix_mfa_secrets_user_id", "mfa_secrets", ["user_id"], unique=False)
    op.create_index("ix_mfa_secrets_status", "mfa_secrets", ["status"], unique=False)

    op.create_table(
        "auth_challenges",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("purpose", sa.String(length=64), nullable=False),
        sa.Column("preferred_method", sa.String(length=32), nullable=False),
        sa.Column("allowed_methods", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("context", sa.JSON(), nullable=True),
        sa.Column("context_hash", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("verified_method", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_auth_challenges_user_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_auth_challenges"),
    )
    op.create_index("ix_auth_challenges_user_id", "auth_challenges", ["user_id"], unique=False)
    op.create_index("ix_auth_challenges_purpose", "auth_challenges", ["purpose"], unique=False)
    op.create_index("ix_auth_challenges_status", "auth_challenges", ["status"], unique=False)
    op.create_index("ix_auth_challenges_expires_at", "auth_challenges", ["expires_at"], unique=False)

    op.create_table(
        "login_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("email_attempted", sa.String(length=255), nullable=False),
        sa.Column("device_id", sa.String(length=120), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("suspicious", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_login_events_user_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_login_events"),
    )
    op.create_index("ix_login_events_user_id", "login_events", ["user_id"], unique=False)
    op.create_index("ix_login_events_email_attempted", "login_events", ["email_attempted"], unique=False)
    op.create_index("ix_login_events_success", "login_events", ["success"], unique=False)
    op.create_index("ix_login_events_suspicious", "login_events", ["suspicious"], unique=False)

    op.create_table(
        "notification_preferences",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("system_in_app", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("system_email", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("system_sms", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("security_alert_in_app", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("security_alert_email", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("security_alert_sms", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("transaction_in_app", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("transaction_email", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("transaction_sms", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("support_in_app", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("support_email", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("support_sms", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_notification_preferences_user_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_notification_preferences"),
        sa.UniqueConstraint("user_id", name="uq_notification_preferences_user_id"),
    )
    op.create_index("ix_notification_preferences_user_id", "notification_preferences", ["user_id"], unique=False)

    op.create_table(
        "beneficiaries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("account_number", sa.String(length=32), nullable=False),
        sa.Column("nickname", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("created_by_challenge_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["bank_accounts.id"], name="fk_beneficiaries_account_id_bank_accounts"),
        sa.ForeignKeyConstraint(["created_by_challenge_id"], ["auth_challenges.id"], name="fk_beneficiaries_created_by_challenge_id_auth_challenges"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_beneficiaries_user_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_beneficiaries"),
    )
    op.create_index("ix_beneficiaries_user_id", "beneficiaries", ["user_id"], unique=False)
    op.create_index("ix_beneficiaries_account_id", "beneficiaries", ["account_id"], unique=False)
    op.create_index("ix_beneficiaries_account_number", "beneficiaries", ["account_number"], unique=False)
    op.create_index("ix_beneficiaries_status", "beneficiaries", ["status"], unique=False)

    op.create_table(
        "recurring_transfers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("from_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("beneficiary_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("frequency", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["beneficiary_id"], ["beneficiaries.id"], name="fk_recurring_transfers_beneficiary_id_beneficiaries"),
        sa.ForeignKeyConstraint(["from_account_id"], ["bank_accounts.id"], name="fk_recurring_transfers_from_account_id_bank_accounts"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_recurring_transfers_user_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_recurring_transfers"),
    )
    op.create_index("ix_recurring_transfers_user_id", "recurring_transfers", ["user_id"], unique=False)
    op.create_index("ix_recurring_transfers_from_account_id", "recurring_transfers", ["from_account_id"], unique=False)
    op.create_index("ix_recurring_transfers_beneficiary_id", "recurring_transfers", ["beneficiary_id"], unique=False)
    op.create_index("ix_recurring_transfers_status", "recurring_transfers", ["status"], unique=False)

    op.create_table(
        "statement_exports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("export_format", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
        sa.Column("date_from", sa.Date(), nullable=False),
        sa.Column("date_to", sa.Date(), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=True),
        sa.Column("error_message", sa.String(length=255), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["bank_accounts.id"], name="fk_statement_exports_account_id_bank_accounts"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_statement_exports_user_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_statement_exports"),
    )
    op.create_index("ix_statement_exports_user_id", "statement_exports", ["user_id"], unique=False)
    op.create_index("ix_statement_exports_account_id", "statement_exports", ["account_id"], unique=False)
    op.create_index("ix_statement_exports_status", "statement_exports", ["status"], unique=False)

    op.create_table(
        "kyc_submissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reviewer_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="under_review"),
        sa.Column("document_type", sa.String(length=64), nullable=False),
        sa.Column("document_number", sa.String(length=120), nullable=False),
        sa.Column("files", sa.JSON(), nullable=False),
        sa.Column("address_text", sa.String(length=500), nullable=False),
        sa.Column("review_note", sa.String(length=1000), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["reviewer_user_id"], ["users.id"], name="fk_kyc_submissions_reviewer_user_id_users"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_kyc_submissions_user_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_kyc_submissions"),
    )
    op.create_index("ix_kyc_submissions_user_id", "kyc_submissions", ["user_id"], unique=False)
    op.create_index("ix_kyc_submissions_reviewer_user_id", "kyc_submissions", ["reviewer_user_id"], unique=False)
    op.create_index("ix_kyc_submissions_status", "kyc_submissions", ["status"], unique=False)

    op.create_table(
        "support_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("author_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("author_role", sa.String(length=32), nullable=False),
        sa.Column("message", sa.String(length=1000), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["author_user_id"], ["users.id"], name="fk_support_messages_author_user_id_users"),
        sa.ForeignKeyConstraint(["ticket_id"], ["support_tickets.id"], name="fk_support_messages_ticket_id_support_tickets"),
        sa.PrimaryKeyConstraint("id", name="pk_support_messages"),
    )
    op.create_index("ix_support_messages_ticket_id", "support_messages", ["ticket_id"], unique=False)
    op.create_index("ix_support_messages_author_user_id", "support_messages", ["author_user_id"], unique=False)

    op.add_column("refresh_tokens", sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_refresh_tokens_session_id_user_sessions",
        "refresh_tokens",
        "user_sessions",
        ["session_id"],
        ["id"],
    )
    op.create_index("ix_refresh_tokens_session_id", "refresh_tokens", ["session_id"], unique=False)

    op.add_column("audit_logs", sa.Column("target_user_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("audit_logs", sa.Column("request_id", sa.String(length=64), nullable=True))
    op.add_column("audit_logs", sa.Column("session_id", sa.String(length=120), nullable=True))
    op.add_column("audit_logs", sa.Column("device_id", sa.String(length=120), nullable=True))
    op.add_column("audit_logs", sa.Column("challenge_id", sa.String(length=120), nullable=True))
    op.add_column("audit_logs", sa.Column("idempotency_key", sa.String(length=120), nullable=True))
    op.add_column("audit_logs", sa.Column("before_state", sa.JSON(), nullable=True))
    op.add_column("audit_logs", sa.Column("after_state", sa.JSON(), nullable=True))
    op.create_index("ix_audit_logs_target_user_id", "audit_logs", ["target_user_id"], unique=False)
    op.create_index("ix_audit_logs_request_id", "audit_logs", ["request_id"], unique=False)
    op.create_index("ix_audit_logs_session_id", "audit_logs", ["session_id"], unique=False)
    op.create_index("ix_audit_logs_device_id", "audit_logs", ["device_id"], unique=False)
    op.create_index("ix_audit_logs_challenge_id", "audit_logs", ["challenge_id"], unique=False)
    op.create_index("ix_audit_logs_idempotency_key", "audit_logs", ["idempotency_key"], unique=False)

    op.add_column("cards", sa.Column("online_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")))
    op.add_column("cards", sa.Column("atm_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")))
    op.add_column("cards", sa.Column("contactless_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")))

    op.add_column("transactions", sa.Column("risk_score", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("transactions", sa.Column("risk_status", sa.String(length=32), nullable=False, server_default="allow"))
    op.add_column("transactions", sa.Column("review_required_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_transactions_risk_status", "transactions", ["risk_status"], unique=False)

    op.create_table(
        "fraud_cases",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("transaction_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="open"),
        sa.Column("score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reasons", sa.JSON(), nullable=False),
        sa.Column("decision", sa.String(length=64), nullable=True),
        sa.Column("decision_reason", sa.String(length=255), nullable=True),
        sa.Column("decided_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("applied_actions", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["decided_by_user_id"], ["users.id"], name="fk_fraud_cases_decided_by_user_id_users"),
        sa.ForeignKeyConstraint(["transaction_id"], ["transactions.id"], name="fk_fraud_cases_transaction_id_transactions"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_fraud_cases_user_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_fraud_cases"),
    )
    op.create_index("ix_fraud_cases_user_id", "fraud_cases", ["user_id"], unique=False)
    op.create_index("ix_fraud_cases_transaction_id", "fraud_cases", ["transaction_id"], unique=False)
    op.create_index("ix_fraud_cases_status", "fraud_cases", ["status"], unique=False)
    op.create_index("ix_fraud_cases_score", "fraud_cases", ["score"], unique=False)
    op.create_index("ix_fraud_cases_decided_by_user_id", "fraud_cases", ["decided_by_user_id"], unique=False)

    op.create_table(
        "risk_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("transaction_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("fraud_case_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("rule_name", sa.String(length=120), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("decision", sa.String(length=32), nullable=False),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["fraud_case_id"], ["fraud_cases.id"], name="fk_risk_events_fraud_case_id_fraud_cases"),
        sa.ForeignKeyConstraint(["transaction_id"], ["transactions.id"], name="fk_risk_events_transaction_id_transactions"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_risk_events_user_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_risk_events"),
    )
    op.create_index("ix_risk_events_user_id", "risk_events", ["user_id"], unique=False)
    op.create_index("ix_risk_events_transaction_id", "risk_events", ["transaction_id"], unique=False)
    op.create_index("ix_risk_events_fraud_case_id", "risk_events", ["fraud_case_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_risk_events_fraud_case_id", table_name="risk_events")
    op.drop_index("ix_risk_events_transaction_id", table_name="risk_events")
    op.drop_index("ix_risk_events_user_id", table_name="risk_events")
    op.drop_table("risk_events")

    op.drop_index("ix_fraud_cases_decided_by_user_id", table_name="fraud_cases")
    op.drop_index("ix_fraud_cases_score", table_name="fraud_cases")
    op.drop_index("ix_fraud_cases_status", table_name="fraud_cases")
    op.drop_index("ix_fraud_cases_transaction_id", table_name="fraud_cases")
    op.drop_index("ix_fraud_cases_user_id", table_name="fraud_cases")
    op.drop_table("fraud_cases")

    op.drop_index("ix_transactions_risk_status", table_name="transactions")
    op.drop_column("transactions", "review_required_at")
    op.drop_column("transactions", "risk_status")
    op.drop_column("transactions", "risk_score")

    op.drop_column("cards", "contactless_enabled")
    op.drop_column("cards", "atm_enabled")
    op.drop_column("cards", "online_enabled")

    op.drop_index("ix_audit_logs_idempotency_key", table_name="audit_logs")
    op.drop_index("ix_audit_logs_challenge_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_device_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_session_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_request_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_target_user_id", table_name="audit_logs")
    op.drop_column("audit_logs", "after_state")
    op.drop_column("audit_logs", "before_state")
    op.drop_column("audit_logs", "idempotency_key")
    op.drop_column("audit_logs", "challenge_id")
    op.drop_column("audit_logs", "device_id")
    op.drop_column("audit_logs", "session_id")
    op.drop_column("audit_logs", "request_id")
    op.drop_column("audit_logs", "target_user_id")

    op.drop_index("ix_refresh_tokens_session_id", table_name="refresh_tokens")
    op.drop_constraint("fk_refresh_tokens_session_id_user_sessions", "refresh_tokens", type_="foreignkey")
    op.drop_column("refresh_tokens", "session_id")

    op.drop_index("ix_support_messages_author_user_id", table_name="support_messages")
    op.drop_index("ix_support_messages_ticket_id", table_name="support_messages")
    op.drop_table("support_messages")

    op.drop_index("ix_kyc_submissions_status", table_name="kyc_submissions")
    op.drop_index("ix_kyc_submissions_reviewer_user_id", table_name="kyc_submissions")
    op.drop_index("ix_kyc_submissions_user_id", table_name="kyc_submissions")
    op.drop_table("kyc_submissions")

    op.drop_index("ix_statement_exports_status", table_name="statement_exports")
    op.drop_index("ix_statement_exports_account_id", table_name="statement_exports")
    op.drop_index("ix_statement_exports_user_id", table_name="statement_exports")
    op.drop_table("statement_exports")

    op.drop_index("ix_recurring_transfers_status", table_name="recurring_transfers")
    op.drop_index("ix_recurring_transfers_beneficiary_id", table_name="recurring_transfers")
    op.drop_index("ix_recurring_transfers_from_account_id", table_name="recurring_transfers")
    op.drop_index("ix_recurring_transfers_user_id", table_name="recurring_transfers")
    op.drop_table("recurring_transfers")

    op.drop_index("ix_beneficiaries_status", table_name="beneficiaries")
    op.drop_index("ix_beneficiaries_account_number", table_name="beneficiaries")
    op.drop_index("ix_beneficiaries_account_id", table_name="beneficiaries")
    op.drop_index("ix_beneficiaries_user_id", table_name="beneficiaries")
    op.drop_table("beneficiaries")

    op.drop_index("ix_notification_preferences_user_id", table_name="notification_preferences")
    op.drop_table("notification_preferences")

    op.drop_index("ix_login_events_suspicious", table_name="login_events")
    op.drop_index("ix_login_events_success", table_name="login_events")
    op.drop_index("ix_login_events_email_attempted", table_name="login_events")
    op.drop_index("ix_login_events_user_id", table_name="login_events")
    op.drop_table("login_events")

    op.drop_index("ix_auth_challenges_expires_at", table_name="auth_challenges")
    op.drop_index("ix_auth_challenges_status", table_name="auth_challenges")
    op.drop_index("ix_auth_challenges_purpose", table_name="auth_challenges")
    op.drop_index("ix_auth_challenges_user_id", table_name="auth_challenges")
    op.drop_table("auth_challenges")

    op.drop_index("ix_mfa_secrets_status", table_name="mfa_secrets")
    op.drop_index("ix_mfa_secrets_user_id", table_name="mfa_secrets")
    op.drop_table("mfa_secrets")

    op.drop_index("ix_trusted_devices_user_id", table_name="trusted_devices")
    op.drop_table("trusted_devices")

    op.drop_index("ix_user_sessions_status", table_name="user_sessions")
    op.drop_index("ix_user_sessions_device_id", table_name="user_sessions")
    op.drop_index("ix_user_sessions_family_id", table_name="user_sessions")
    op.drop_index("ix_user_sessions_user_id", table_name="user_sessions")
    op.drop_table("user_sessions")
