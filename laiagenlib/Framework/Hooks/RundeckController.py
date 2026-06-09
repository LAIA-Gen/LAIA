from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from ...Application.Hooks.Lambdas.SendMailLambda import send_mail_lambda
from ...Domain.LaiaBaseModel.ModelRepository import ModelRepository
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


def RundeckController(smtp_config: dict, repository: ModelRepository):
    router = APIRouter(tags=["Hooks"])

    @router.post(
        "/api/hooks/send-bulk-email/",
        response_model=BulkEmailResponse,
        summary="Envia emails massivament (per Rundeck o tasques programades)"
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
