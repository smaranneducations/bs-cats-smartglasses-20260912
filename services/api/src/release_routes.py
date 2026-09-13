from fastapi import APIRouter, Depends, HTTPException
from packages.media.release_review import assess_release


def release_router(get_store, require_access):
    router = APIRouter(dependencies=[Depends(require_access)])

    @router.get("/v1/media/artifacts/{artifact_id}/release-review")
    def release_review(artifact_id: str):
        try:
            return assess_release(get_store(), artifact_id)
        except (ValueError, KeyError, TypeError):
            raise HTTPException(422, "Artifact review inputs are invalid or exceed the bounded inspection scope.") from None

    return router
