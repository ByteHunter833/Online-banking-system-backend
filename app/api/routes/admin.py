from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from app.api.dependencies.auth import require_roles, rate_limit
from app.api.dependencies.services import (
    get_admin_service,
    get_auth_service,
    get_fraud_service,
    get_kyc_service,
    get_support_service,
)
from app.schemas.account import BankAccountResponse
from app.schemas.admin import AdminReasonRequest
from app.schemas.audit import AuditLogResponse
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.fraud import FraudCaseDecisionRequest, FraudCaseResponse
from app.schemas.kyc import KYCSubmissionResponse, KYCSubmissionReviewRequest
from app.schemas.support import SupportTicketResponse, SupportTicketUpdateRequest
from app.schemas.transaction import TransactionResponse
from app.schemas.user import UserProfileResponse
from app.services.admin import AdminService
from app.services.auth import AuthService
from app.services.fraud import FraudService
from app.services.kyc import KYCService
from app.services.support import SupportService

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.post("/login", response_model=TokenResponse, dependencies=[Depends(rate_limit("admin-login", key_strategy="ip_email"))])
async def admin_login(
    payload: LoginRequest,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
):
    return await auth_service.login(payload, request, admin_only=True)


@router.get("/users", response_model=list[UserProfileResponse])
async def list_users(
    current_user=Depends(require_roles("admin", "support", "compliance")),
    admin_service: AdminService = Depends(get_admin_service),
):
    return [
        UserProfileResponse.model_validate(
            {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "is_active": user.is_active,
                "is_email_verified": user.is_email_verified,
                "mfa_enabled": user.mfa_enabled,
                "biometric_enabled": user.biometric_enabled,
                "kyc_status": user.kyc_status,
                "roles": sorted(role.name for role in user.roles),
                "phone": user.phone,
                "date_of_birth": user.date_of_birth,
                "address_line1": user.address_line1,
                "address_line2": user.address_line2,
                "city": user.city,
                "state": user.state,
                "postal_code": user.postal_code,
                "country": user.country,
                "last_login_at": user.last_login_at,
                "created_at": user.created_at,
                "updated_at": user.updated_at,
            }
        )
        for user in await admin_service.list_users()
    ]


@router.get("/transactions", response_model=list[TransactionResponse])
async def list_transactions(
    current_user=Depends(require_roles("admin", "compliance", "auditor")),
    admin_service: AdminService = Depends(get_admin_service),
):
    return await admin_service.list_transactions()


@router.post("/accounts/{account_id}/freeze", response_model=BankAccountResponse)
async def freeze_account(
    account_id: UUID,
    payload: AdminReasonRequest,
    request: Request,
    current_user=Depends(require_roles("admin", "compliance")),
    admin_service: AdminService = Depends(get_admin_service),
):
    return await admin_service.freeze_account(
        admin_user=current_user,
        account_id=account_id,
        reason=payload.reason,
        request=request,
    )


@router.post("/accounts/{account_id}/unfreeze", response_model=BankAccountResponse)
async def unfreeze_account(
    account_id: UUID,
    payload: AdminReasonRequest,
    request: Request,
    current_user=Depends(require_roles("admin", "compliance")),
    admin_service: AdminService = Depends(get_admin_service),
):
    return await admin_service.unfreeze_account(
        admin_user=current_user,
        account_id=account_id,
        reason=payload.reason,
        request=request,
    )


@router.post("/transactions/{transaction_id}/flag", response_model=TransactionResponse)
async def flag_transaction(
    transaction_id: UUID,
    payload: AdminReasonRequest,
    request: Request,
    current_user=Depends(require_roles("admin", "compliance")),
    admin_service: AdminService = Depends(get_admin_service),
):
    return await admin_service.flag_transaction(
        admin_user=current_user,
        transaction_id=transaction_id,
        reason=payload.reason,
        request=request,
    )


@router.get("/audit-logs", response_model=list[AuditLogResponse])
async def list_audit_logs(
    current_user=Depends(require_roles("admin", "compliance", "auditor")),
    admin_service: AdminService = Depends(get_admin_service),
):
    return await admin_service.list_audit_logs()


@router.get("/support", response_model=list[SupportTicketResponse])
async def list_support_tickets(
    current_user=Depends(require_roles("admin", "support")),
    admin_service: AdminService = Depends(get_admin_service),
):
    return await admin_service.list_support_tickets()


@router.patch("/support/{ticket_id}", response_model=SupportTicketResponse)
async def update_support_ticket(
    ticket_id: UUID,
    payload: SupportTicketUpdateRequest,
    request: Request,
    current_user=Depends(require_roles("admin", "support")),
    support_service: SupportService = Depends(get_support_service),
):
    return await support_service.update_ticket_as_admin(
        admin_user=current_user,
        ticket_id=ticket_id,
        payload=payload,
        request=request,
    )


@router.get("/kyc/submissions", response_model=list[KYCSubmissionResponse])
async def list_kyc_submissions(
    current_user=Depends(require_roles("admin", "support", "compliance", "auditor")),
    kyc_service: KYCService = Depends(get_kyc_service),
):
    submissions = await kyc_service.list_submissions()
    return [
        {
            "submission_id": item.id,
            "user_id": item.user_id,
            "reviewer_user_id": item.reviewer_user_id,
            "status": item.status,
            "document_type": item.document_type,
            "document_number": item.document_number,
            "files": item.files,
            "address_text": item.address_text,
            "review_note": item.review_note,
            "reviewed_at": item.reviewed_at,
            "created_at": item.created_at,
        }
        for item in submissions
    ]


@router.post("/kyc/submissions/{submission_id}/review", response_model=KYCSubmissionResponse)
async def review_kyc_submission(
    submission_id: UUID,
    payload: KYCSubmissionReviewRequest,
    request: Request,
    current_user=Depends(require_roles("admin", "compliance")),
    kyc_service: KYCService = Depends(get_kyc_service),
):
    submission = await kyc_service.review(
        admin_user=current_user,
        submission_id=submission_id,
        payload=payload,
        request=request,
    )
    return {
        "submission_id": submission.id,
        "user_id": submission.user_id,
        "reviewer_user_id": submission.reviewer_user_id,
        "status": submission.status,
        "document_type": submission.document_type,
        "document_number": submission.document_number,
        "files": submission.files,
        "address_text": submission.address_text,
        "review_note": submission.review_note,
        "reviewed_at": submission.reviewed_at,
        "created_at": submission.created_at,
    }


@router.get("/fraud/cases", response_model=list[FraudCaseResponse])
async def list_fraud_cases(
    status: str | None = None,
    score_gte: int | None = Query(default=None, ge=0),
    current_user=Depends(require_roles("admin", "compliance", "auditor")),
    fraud_service: FraudService = Depends(get_fraud_service),
):
    cases = await fraud_service.list_cases(status=status, score_gte=score_gte)
    return [
        {
            "case_id": item.id,
            "transaction_id": item.transaction_id,
            "user_id": item.user_id,
            "status": item.status,
            "score": item.score,
            "reasons": item.reasons,
            "decision": item.decision,
            "decision_reason": item.decision_reason,
            "applied_actions": item.applied_actions,
            "decided_by_user_id": item.decided_by_user_id,
            "decided_at": item.decided_at,
            "created_at": item.created_at,
        }
        for item in cases
    ]


@router.post("/fraud/cases/{case_id}/decision", response_model=FraudCaseResponse)
async def decide_fraud_case(
    case_id: UUID,
    payload: FraudCaseDecisionRequest,
    request: Request,
    current_user=Depends(require_roles("admin", "compliance")),
    fraud_service: FraudService = Depends(get_fraud_service),
):
    case = await fraud_service.decide_case(
        admin_user=current_user,
        case_id=case_id,
        decision=payload.decision,
        reason=payload.reason,
        request=request,
    )
    return {
        "case_id": case.id,
        "transaction_id": case.transaction_id,
        "user_id": case.user_id,
        "status": case.status,
        "score": case.score,
        "reasons": case.reasons,
        "decision": case.decision,
        "decision_reason": case.decision_reason,
        "applied_actions": case.applied_actions,
        "decided_by_user_id": case.decided_by_user_id,
        "decided_at": case.decided_at,
        "created_at": case.created_at,
    }
