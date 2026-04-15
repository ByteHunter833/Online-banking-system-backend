from fastapi import APIRouter

from app.api.routes.accounts import router as accounts_router
from app.api.routes.admin import router as admin_router
from app.api.routes.auth import router as auth_router
from app.api.routes.beneficiaries import router as beneficiaries_router
from app.api.routes.cards import router as cards_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.kyc import router as kyc_router
from app.api.routes.notifications import router as notifications_router
from app.api.routes.recurring_transfers import router as recurring_transfers_router
from app.api.routes.security import router as security_router
from app.api.routes.statements import router as statements_router
from app.api.routes.support import router as support_router
from app.api.routes.transactions import router as transactions_router
from app.api.routes.users import router as users_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(security_router)
api_router.include_router(dashboard_router)
api_router.include_router(accounts_router)
api_router.include_router(beneficiaries_router)
api_router.include_router(transactions_router)
api_router.include_router(recurring_transfers_router)
api_router.include_router(statements_router)
api_router.include_router(cards_router)
api_router.include_router(notifications_router)
api_router.include_router(kyc_router)
api_router.include_router(support_router)
api_router.include_router(admin_router)
