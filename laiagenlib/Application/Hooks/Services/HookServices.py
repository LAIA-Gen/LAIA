from .ModelService import DemandService, MatchService, ModelService, MouCulturaService, OfferService, UserService


def create_hook_services(repository=None, smtp_config: dict = None) -> dict:
    return {
        "model": ModelService(repository),
        "user": UserService(repository),
        "offer": OfferService(repository),
        "demand": DemandService(repository),
        "match": MatchService(repository),
        "moucultura": MouCulturaService(repository),
    }
