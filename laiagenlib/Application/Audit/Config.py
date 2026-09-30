from dataclasses import dataclass


@dataclass(frozen=True)
class AuditConfig:
    enabled: bool = False
    before_request: bool = False
    exclude_models: tuple = ()

    @classmethod
    def from_openapi(cls, spec):
        middleware = spec.get('middleware', {})
        if not isinstance(middleware, dict):
            raise ValueError('middleware must be an object')
        value = middleware.get('auditlog', {})
        if not isinstance(value, dict):
            raise ValueError('middleware.auditlog must be an object')
        for name in ('enabled', 'before_request'):
            if name in value and type(value[name]) is not bool:
                raise ValueError(f'middleware.auditlog.{name} must be a boolean')
        excluded = value.get('exclude_models', [])
        if not isinstance(excluded, list) or any(not isinstance(v, str) for v in excluded):
            raise ValueError('middleware.auditlog.exclude_models must be a list of model names')
        return cls(value.get('enabled', False), value.get('before_request', False),
                   tuple(v.casefold() for v in excluded))

    def as_dict(self):
        return {'enabled': self.enabled, 'before_request': self.before_request,
                'exclude_models': list(self.exclude_models)}
