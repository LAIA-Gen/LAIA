from dataclasses import dataclass, field
from typing import Optional


@dataclass
class HookDefinition:
    """
    Represents a hook defined in a model YAML.

    Preferred YAML:
        x-hooks:
          preupdate:
            - script: offer/check_offer_not_full
          postsave:
            - command: sendMail
              condition: "statusOffer == 'full'"
              to: "{{email}}"
              subject: "Benvingut!"
              template: registration_received.html
              context:
                username: "{{name}}"
          postupdate:
            - script: send_mail
              params:
                template: offer-confirmed
            - script: offer/update_offer_status

    Inline scripts are still accepted for simple declarative actions:
        - script:
            condition: "true"
            execute: "totalSeatsOccupied = len(acceptedUserIds)"
    """
    event: str
    lambda_name: str                    # Deprecated. Prefer command/script in YAML.
    condition: Optional[str] = None
    params: dict = field(default_factory=dict)

    @classmethod
    def from_yaml(cls, event: str, hook_dict: dict) -> "HookDefinition":
        """Creates a HookDefinition from YAML while accepting old and new syntax."""
        script = hook_dict.get("script")
        body = script if isinstance(script, dict) else hook_dict
        lambda_name = hook_dict.get("command") or hook_dict.get("lambda", "")
        condition = body.get("condition", None)
        params = {k: v for k, v in hook_dict.items() if k not in ("command", "lambda", "condition")}
        return cls(
            event=event,
            lambda_name=lambda_name,
            condition=condition,
            params=params
        )
