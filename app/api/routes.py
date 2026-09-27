from fastapi import (
    APIRouter,
    Depends,
)

from app.core.security import (
    Principal,
    get_current_principal,
)
from app.models.drug import DrugRequest
from app.services.drug_service import (
    create_drug_service,
)


router = APIRouter()


@router.get("/auth/me")
def current_identity(
    principal: Principal = Depends(
        get_current_principal
    ),
):
    return {
        "authenticated": True,
        "user_id": principal.user_id,
        "tenant_id": principal.tenant_id,
        "role": principal.role,
    }


@router.post("/drugs")
def create_drug(
    drug: DrugRequest,
    principal: Principal = Depends(
        get_current_principal
    ),
):
    return create_drug_service(
        drug,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
    )