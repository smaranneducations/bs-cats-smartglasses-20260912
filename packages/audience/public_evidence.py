"""Project only published statements whose referenced product version is current."""
from packages.contracts.store import ObjectNotFoundError


def published_cards(store, view):
    result = []
    for card in store.list_objects(object_type="content_card"):
        if card.status.value != "published":
            continue
        try:
            product = store.get(card.payload["product_id"])
        except (ObjectNotFoundError, KeyError):
            continue
        if (product.object_type != "product"
                or product.version != card.payload.get("product_version")
                or product.status.value in {"archived", "deprecated", "rejected"}):
            continue
        result.append({**view(card), "product_id": product.object_id,
                       "product_version": product.version, "product_title": product.title})
    return result
