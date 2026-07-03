from fastapi import APIRouter, HTTPException, Depends, Query, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List, Optional
from ...Application.Hooks.Lambdas.SendMailLambda import send_mail_lambda
from ...Application.Hooks.TripRatingEmails import (
    DEFAULT_LOCALE,
    DEFAULT_SUBJECT,
    DEFAULT_TEMPLATE,
    send_trip_rating_emails,
)
from ...Domain.LaiaBaseModel.ModelRepository import ModelRepository
from ...Application.LaiaUser import JWTToken
from ...Domain.LaiaUser.Role import Role
from ...Application.LaiaBaseModel import ReadLaiaBaseModel
from ...Domain.Shared.Utils.logger import _logger


class RecipientInfo(BaseModel):
    email: str
    context: dict = {}


class BulkEmailRequest(BaseModel):
    subject: str
    template: str
    locale: str = "ca"
    recipients: Optional[List[RecipientInfo]] = None
    # Si no es passen recipients, busca automàticament
    auto_discover: bool = False
    filters: dict = {}


class BulkEmailResponse(BaseModel):
    message: str
    sent_count: int
    errors: List[str] = []
    count: int = 0
    events: List[dict] = []


def RundeckController(smtp_config: dict, repository: ModelRepository, jwtSecretKey: str):
    router = APIRouter(tags=["Hooks"])

    http_bearer = HTTPBearer(auto_error=False)

    def get_token(credentials: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer)) -> Optional[str]:
        return credentials.credentials if credentials else None

    async def verify_admin(token: str = Depends(get_token)):
        if not token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid authorization header")
        
        try:
            payload = JWTToken.verify_jwt_token(token, jwtSecretKey)
            user_roles_ids = payload.get("user_roles") or []
            
            user_roles = []
            for role in user_roles_ids:
                if isinstance(role, str) and len(role) != 24:
                    user_roles.append(role)
                else:
                    user_role = await ReadLaiaBaseModel.read_laia_base_model(role, Role, ['admin'], repository, False)
                    user_roles.append(user_role['name'])
            
            if "admin" not in user_roles:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin token required")
                
        except ValueError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session token")
        
        return True


    @router.get(
        "/trips/rating",
        summary="Envia emails de valoracio per matches completats",
        dependencies=[Depends(verify_admin)]
    )
    async def send_trip_rating(
        dry_run: bool = Query(False, description="Prepare recipients without sending emails"),
        force: bool = Query(False, description="Include matches already marked as emailed"),
        days_after_event: int = Query(2, ge=0),
        review_base_url: Optional[str] = Query(
            None,
            description="Frontend URL that opens the public feedback form",
        ),
    ):
        return await send_trip_rating_emails(
            repository=repository,
            smtp_config=smtp_config,
            subject=DEFAULT_SUBJECT,
            template=DEFAULT_TEMPLATE,
            locale=DEFAULT_LOCALE,
            days_after_event=days_after_event,
            force=force,
            dry_run=dry_run,
            review_base_url=review_base_url,
        )

    @router.post(
        "/api/hooks/send-bulk-email/",
        response_model=BulkEmailResponse,
        summary="Envia emails massivament (per Rundeck o tasques programades)",
        dependencies=[Depends(verify_admin)]
    )
    async def send_bulk_email(request: BulkEmailRequest):
        """
        Ruta per Rundeck o tasques programades.
        
        Modes:
        1. Amb `recipients`: envia als destinataris especificats
        2. Amb `auto_discover: true` i `filters`: busca Offers completades i envia
           emails de valoració a voluntaris i seekers
        """
        sent_count = 0
        errors = []

        if request.recipients:
            # Mode 1: Recipients explícits
            for recipient in request.recipients:
                try:
                    await send_mail_lambda(
                        to=recipient.email,
                        subject=request.subject,
                        template=request.template,
                        context=recipient.context,
                        smtp_config=smtp_config,
                        locale=request.locale
                    )
                    sent_count += 1
                except Exception as e:
                    errors.append(f"Failed for {recipient.email}: {str(e)}")

        elif request.auto_discover:
            if request.template == DEFAULT_TEMPLATE or request.filters.get("type") == "trip_ratings":
                result = await send_trip_rating_emails(
                    repository=repository,
                    smtp_config=smtp_config,
                    subject=request.subject,
                    template=request.template,
                    locale=request.locale,
                    days_after_event=int(request.filters.get("days_after_event", 2)),
                    force=bool(request.filters.get("force", False)),
                    dry_run=bool(request.filters.get("dry_run", False)),
                    review_base_url=request.filters.get("review_base_url"),
                )
                return BulkEmailResponse(
                    message=result["message"],
                    sent_count=result["sent_count"],
                    errors=result["errors"],
                    count=result["count"],
                    events=result["events"],
                )

            # Mode 2: Auto-discover — busca Offers i Demands
            try:
                # Buscar Offers completades (status full/cancelled/expired)
                search_filters = request.filters or {"statusOffer": "full"}
                offers, _ = await repository.get_items(
                    model_name="offer",
                    filters=search_filters,
                    limit=1000
                )

                for offer in offers:
                    # Email al voluntari (userId de l'Offer)
                    volunteer_id = offer.get("userId")
                    if volunteer_id:
                        try:
                            users, _ = await repository.get_items(
                                model_name="user",
                                filters={"_id": str(volunteer_id)},
                                limit=1
                            )
                            if users:
                                volunteer = users[0]
                                await send_mail_lambda(
                                    to=volunteer.get("email", ""),
                                    subject=request.subject,
                                    template=request.template,
                                    context={
                                        "username": volunteer.get("name", ""),
                                        "role": "voluntari"
                                    },
                                    smtp_config=smtp_config,
                                    locale=request.locale
                                )
                                sent_count += 1
                        except Exception as e:
                            errors.append(f"Volunteer {volunteer_id}: {str(e)}")

                    # Emails als seekers (acceptedUserIds de l'Offer)
                    accepted_ids = offer.get("acceptedUserIds", [])
                    for seeker_id in accepted_ids:
                        try:
                            users, _ = await repository.get_items(
                                model_name="user",
                                filters={"_id": str(seeker_id)},
                                limit=1
                            )
                            if users:
                                seeker = users[0]
                                await send_mail_lambda(
                                    to=seeker.get("email", ""),
                                    subject=request.subject,
                                    template=request.template,
                                    context={
                                        "username": seeker.get("name", ""),
                                        "role": "seeker"
                                    },
                                    smtp_config=smtp_config,
                                    locale=request.locale
                                )
                                sent_count += 1
                        except Exception as e:
                            errors.append(f"Seeker {seeker_id}: {str(e)}")

            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Auto-discover failed: {str(e)}")
        else:
            raise HTTPException(
                status_code=400,
                detail="Either 'recipients' or 'auto_discover: true' must be provided"
            )

        return BulkEmailResponse(
            message=f"Bulk email completed: {sent_count} sent, {len(errors)} errors",
            sent_count=sent_count,
            errors=errors
        )

    return router
