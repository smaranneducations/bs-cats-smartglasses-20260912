from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from packages.contracts.media import RenderArtifactPayload
from packages.media.planning import file_hash
from packages.runtime.context import ROOT, fingerprint


def media_router(get_store, require_access):
    router = APIRouter(tags=["private-media-review"], dependencies=[Depends(require_access)])

    def artifact(object_id):
        records = get_store().history(object_id)
        if not records:
            raise HTTPException(404,"Render artifact not found.")
        obj = max(records, key=lambda record: record.snapshot.version).snapshot
        if obj.object_type != "render_artifact":
            raise HTTPException(404,"Choose a render artifact.")
        return obj, RenderArtifactPayload.model_validate(obj.payload)

    def checked_path(uri, expected_hash):
        path = (ROOT/uri).resolve()
        if not path.is_relative_to((ROOT/".local/production-renders").resolve()) or not path.is_file():
            raise HTTPException(404,"Private artifact file is unavailable.")
        if expected_hash and file_hash(path) != expected_hash:
            raise HTTPException(409,"Artifact bytes changed; the previous review identity is no longer valid.")
        return path

    @router.get("/v1/media/artifacts")
    def artifacts():
        return {"artifacts":[{"object_id":obj.object_id,"version":obj.version,"title":obj.title,"review_state":obj.review.state.value,
                              "duration_seconds":obj.payload["duration_seconds"],"review_url":"/media-review/"+obj.object_id}
                             for obj in get_store().list_objects() if obj.object_type == "render_artifact"]}

    @router.get("/v1/media/artifacts/{object_id}")
    def detail(object_id: str):
        obj, payload = artifact(object_id)
        if fingerprint(payload.publish_metadata) != payload.metadata_sha256:
            raise HTTPException(409,"Publish metadata no longer matches the artifact identity.")
        return {"object_id":obj.object_id,"version":obj.version,"title":obj.title,"review_state":obj.review.state.value,
                "payload":payload.model_dump(mode="json"),"sources":[source.model_dump(mode="json") for source in obj.sources]}

    @router.get("/v1/media/artifacts/{object_id}/video")
    def video(object_id: str):
        _, payload = artifact(object_id)
        return FileResponse(checked_path(payload.artifact_uri,payload.video_sha256),media_type="video/mp4")

    @router.get("/v1/media/artifacts/{object_id}/poster")
    def poster(object_id: str):
        _, payload = artifact(object_id)
        return FileResponse(checked_path(payload.poster_uri,None),media_type="image/png")

    @router.get("/v1/media/artifacts/{object_id}/manifest")
    def manifest(object_id: str):
        _, payload = artifact(object_id)
        return FileResponse(checked_path(payload.manifest_uri,payload.manifest_sha256),media_type="application/json")

    @router.get("/media-review/{object_id}",include_in_schema=False)
    def review_page(object_id: str):
        artifact(object_id)
        return FileResponse(ROOT/"apps/web/intelligence/video.html",media_type="text/html")

    @router.get("/media-review-assets/video.js",include_in_schema=False)
    def review_script():
        return FileResponse(ROOT/"apps/web/intelligence/video.js",media_type="text/javascript")

    @router.get("/media-review-assets/video.css",include_in_schema=False)
    def review_styles():
        return FileResponse(ROOT/"apps/web/intelligence/video.css",media_type="text/css")

    return router
