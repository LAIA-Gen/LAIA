from ....Application.Shared.Utils.SendEmail import send_email
from ....Domain.Hooks.LambdaRegistry import register_lambda
from ....Domain.Shared.Utils.logger import _logger


async def send_mail_lambda(to: str, subject: str, template: str, context: dict = None,
                           smtp_config: dict = None, locale: str = "ca", **kwargs):
    """
    Lambda genèrica per enviar emails amb templates.
    
    Args:
        to: Adreça email del destinatari
        subject: Assumpte de l'email
        template: Nom del fitxer template (ex: "registration_received.html")
        context: Variables per Jinja2 (ex: {"username": "Joan"})
        smtp_config: Configuració SMTP
        locale: Idioma del template (subcarpeta dins email_templates/)
        **kwargs: Paràmetres extra ignorats (from, etc.)
    """
    if not smtp_config or not smtp_config.get("host"):
        _logger.warning("SMTP not configured, skipping email send")
        return

    if not to:
        _logger.warning("No recipient address provided, skipping email send")
        return

    # El template està dins d'una subcarpeta per locale: ca/welcome.html
    template_path = f"{locale}/{template}"

    _logger.info(f"sendMail lambda: to={to}, subject='{subject}', template={template_path}")

    await send_email(
        to=to,
        subject=subject,
        template=template_path,
        variables=context or {},
        smtp_config=smtp_config
    )

    _logger.info(f"Email sent successfully to {to}")


# Auto-registre: quan s'importa aquest mòdul, la lambda queda registrada
register_lambda("sendMail", send_mail_lambda)
