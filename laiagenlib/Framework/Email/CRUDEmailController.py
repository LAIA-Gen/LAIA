from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from ...Domain.Email.EmailRequest import EmailRequest
from jinja2 import Environment, FileSystemLoader, select_autoescape
from typing import Optional
from ...Application.LaiaUser import JWTToken
from ...Domain.LaiaBaseModel.ModelRepository import ModelRepository
from ...Domain.LaiaUser.Role import Role
from ...Application.LaiaBaseModel import ReadLaiaBaseModel

async def CRUDEmailController(smtp_config: dict, repository: ModelRepository, jwtSecretKey: str):
    model = EmailRequest
    router = APIRouter(tags=[model.__name__])

    class EmailResponse(BaseModel):
        message: str

    templates_dir = smtp_config.get("templates_dir", "email_templates")
    env = Environment(
        loader=FileSystemLoader(templates_dir),
        autoescape=select_autoescape(["html", "xml"])
    )

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

    @router.post("/send-email/", response_model=EmailResponse, dependencies=[Depends(verify_admin)])
    async def send_email(email: EmailRequest):
        try:
            # Renderizado del HTML si hay plantilla
            html_content = None
            if email.template:
                template = env.get_template(email.template)
                html_content = template.render(email.variables or {})

            # Construir el mensaje
            msg = MIMEMultipart("alternative")
            msg["From"] = smtp_config["user"]
            msg["To"] = email.to
            msg["Subject"] = email.subject

            if email.body:
                msg.attach(MIMEText(email.body, "plain"))
            if html_content:
                msg.attach(MIMEText(html_content, "html"))

            # Envío
            if smtp_config.get("tls", True):
                server = smtplib.SMTP(smtp_config["host"], smtp_config["port"])
                server.starttls()
            else:
                server = smtplib.SMTP_SSL(smtp_config["host"], smtp_config["port"])

            server.login(smtp_config["user"], smtp_config["password"])
            server.sendmail(smtp_config["user"], email.to, msg.as_string())
            server.quit()

            return {"message": f"Email sent to {email.to}"}

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Email sending failed: {str(e)}")
        
    return router