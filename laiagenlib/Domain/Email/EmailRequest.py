from pydantic import BaseModel, EmailStr

class EmailRequest(BaseModel):
    to: EmailStr
    subject: str
    body: str = ""            # opcional, texto plano
    template: str = None      # nombre del archivo HTML
    variables: dict = None    # variables para la plantilla