from dataclasses import dataclass, field


@dataclass
class HookDefinition:
    """
    Represents a file-based hook defined in a model YAML.

    YAML:
        x-hooks:
          preUpdate:
            - script: offer/check_offer_not_full
          postUpdate:
            - script: send_mail
              params:
                template: offer-confirmed
            - script: offer/update_offer_status
    """
    event: str
    script: str
    params: dict = field(default_factory=dict)

    @classmethod
    def from_yaml(cls, event: str, hook_dict: dict) -> "HookDefinition":
        return cls(
            event=event,
            script=hook_dict.get("script", ""),
            params=hook_dict.get("params", {})
        )
