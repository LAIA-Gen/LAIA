import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Environment, FileSystemLoader, select_autoescape
from fastapi import HTTPException
from ....Domain.Shared.Utils.logger import _logger

async def send_email(to: str, subject: str, template: str, variables: dict, smtp_config: dict):
    try:
        templates_dir = smtp_config.get("templates_dir", "backend/backend/email_templates")
        env = Environment(
            loader=FileSystemLoader(templates_dir),
            autoescape=select_autoescape(["html", "xml"])
        )
        template_file = env.get_template(template)
        html_content = template_file.render(variables or {})

        msg = MIMEMultipart("alternative")
        msg["From"] = smtp_config["user"]
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(html_content, "html"))

        if smtp_config.get("tls", True):
            server = smtplib.SMTP(smtp_config["host"], smtp_config["port"])
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(smtp_config["host"], smtp_config["port"])

        server.login(smtp_config["user"], smtp_config["password"])
        server.sendmail(smtp_config["user"], to, msg.as_string())
        server.quit()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al enviar el email: {str(e)}")