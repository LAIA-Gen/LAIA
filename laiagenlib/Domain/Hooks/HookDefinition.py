from dataclasses import dataclass, field
from typing import Optional


@dataclass
class HookDefinition:
    """
    Representa un hook definit al YAML del model.
    
    Exemple YAML:
        x-hooks:
          preupdate:
            - lambda: anonymous
              condition: "statusOffer == 'full'"
              action: "HttpResponse({status: 409, body: 'Offer is full'})"
          postsave:
            - lambda: sendMail
              condition: "statusOffer == 'full'"
              to: "{{email}}"
              subject: "Benvingut!"
              template: registration_received.html
              context:
                username: "{{name}}"
          postupdate:
            - lambda: anonymous
              condition: "true"
              action: "totalSeatsOccupied = len(acceptedUserIds)"
    """
    event: str                          # "preupdate", "postsave", "postupdate", "postdelete"
    lambda_name: str                    # "sendMail", "anonymous"
    condition: Optional[str] = None     # "statusOffer == 'full'"
    params: dict = field(default_factory=dict)  # to, subject, template, context, etc.

    @classmethod
    def from_yaml(cls, event: str, hook_dict: dict) -> 'HookDefinition':
        """Crea un HookDefinition a partir d'un dict del YAML."""
        lambda_name = hook_dict.get("lambda", "")
        condition = hook_dict.get("condition", None)
        # Tot el que no sigui lambda/condition són paràmetres per la lambda
        params = {k: v for k, v in hook_dict.items() if k not in ("lambda", "condition")}
        return cls(
            event=event,
            lambda_name=lambda_name,
            condition=condition,
            params=params
        )
