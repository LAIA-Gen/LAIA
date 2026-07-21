import os

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

    locale = _normalize_locale(locale)
    template_path = _resolve_template_path(template, locale, smtp_config)

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


def _resolve_template_path(template: str, locale: str, smtp_config: dict) -> str:
    templates_dir = (smtp_config or {}).get("templates_dir", "backend/backend/email_templates")
    localized_template = f"{locale}/{template}"
    localized_path = os.path.join(templates_dir, locale, template)
    if os.path.exists(localized_path):
        return localized_template

    fallback_template = f"ca/{template}"
    fallback_path = os.path.join(templates_dir, "ca", template)
    if locale != "ca" and os.path.exists(fallback_path):
        _logger.warning(f"Email template '{localized_template}' not found, falling back to '{fallback_template}'")
        return fallback_template

    return localized_template


def _normalize_locale(locale: str) -> str:
    locale = str(locale or "ca").strip().replace("-", "_")
    if not locale:
        return "ca"

    language = locale.split("_", 1)[0].lower()
    if language == "en":
        return "en_US"
    if language == "es":
        return "es"
    if language == "ca":
        return "ca"
    return language
