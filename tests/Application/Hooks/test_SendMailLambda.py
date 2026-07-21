import pytest

from laiagenlib.Application.Hooks.Lambdas import SendMailLambda


@pytest.mark.asyncio
async def test_send_mail_uses_requested_locale_when_template_exists(tmp_path, monkeypatch):
    template_dir = tmp_path / "templates"
    (template_dir / "es").mkdir(parents=True)
    (template_dir / "es" / "welcome.html").write_text("Hola", encoding="utf-8")
    sent = {}

    async def fake_send_email(**kwargs):
        sent.update(kwargs)

    monkeypatch.setattr(SendMailLambda, "send_email", fake_send_email)

    await SendMailLambda.send_mail_lambda(
        to="user@example.com",
        subject="Subject",
        template="welcome.html",
        locale="es",
        context={},
        smtp_config={
            "host": "smtp.example.com",
            "port": 587,
            "user": "sender@example.com",
            "password": "secret",
            "templates_dir": str(template_dir),
        },
    )

    assert sent["template"] == "es/welcome.html"


@pytest.mark.asyncio
async def test_send_mail_falls_back_to_ca_when_locale_template_is_missing(tmp_path, monkeypatch):
    template_dir = tmp_path / "templates"
    (template_dir / "ca").mkdir(parents=True)
    (template_dir / "ca" / "welcome.html").write_text("Hola", encoding="utf-8")
    sent = {}

    async def fake_send_email(**kwargs):
        sent.update(kwargs)

    monkeypatch.setattr(SendMailLambda, "send_email", fake_send_email)

    await SendMailLambda.send_mail_lambda(
        to="user@example.com",
        subject="Subject",
        template="welcome.html",
        locale="es",
        context={},
        smtp_config={
            "host": "smtp.example.com",
            "port": 587,
            "user": "sender@example.com",
            "password": "secret",
            "templates_dir": str(template_dir),
        },
    )

    assert sent["template"] == "ca/welcome.html"
