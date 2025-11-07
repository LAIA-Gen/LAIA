from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from ...Domain.Email.EmailRequest import EmailRequest
from jinja2 import Environment, FileSystemLoader, select_autoescape

async def CRUDEmailController(smtp_config: dict):
    model = EmailRequest
    router = APIRouter(tags=[model.__name__])

    templates_dir = smtp_config.get("templates_dir", "email_templates")
    env = Environment(
        loader=FileSystemLoader(templates_dir),
        autoescape=select_autoescape(["html", "xml"])
    )

    @router.post("/send-email/", response_model=dict)
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