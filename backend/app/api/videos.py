"""Video Upload Studio endpoints: upload, FFprobe metadata, transcription, AI analysis & metadata generation."""
from __future__ import annotations

import os
import shutil
import uuid
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import sanitize_filename
from app.models.content import PublishingJob, UploadedMedia
from app.models.user import User
from app.schemas.video import (
    GenerateMetadataRequest,
    UploadedMediaResponse,
    VideoAnalyzeRequest,
)
from app.services.neon_storage import (
    NEON_S3_PREFIX,
    can_use_neon_storage_upload,
    delete_remote_video_object,
    ensure_local_video_file,
    mint_upload_token,
)
from app.services.video_processor import (
    ALLOWED_VIDEO_MIME_TYPES,
    analyze_uploaded_video_content,
    extract_video_metadata,
    generate_video_publish_metadata,
    sample_representative_frames,
    transcribe_video_audio,
    verify_video_file_magic,
)

router = APIRouter(prefix="/videos", tags=["Video Publishing Studio"])


class UploadSessionRequest(BaseModel):
    filename: str = Field(..., min_length=1, max_length=255)
    content_type: str = Field(default="video/mp4", max_length=120)
    file_size_bytes: int = Field(default=0, ge=0)


class CompleteUploadRequest(BaseModel):
    object_key: str = Field(..., min_length=1, max_length=400)
    stored_filename: str = Field(..., min_length=1, max_length=255)
    original_filename: str = Field(..., min_length=1, max_length=255)
    mime_type: str = Field(default="video/mp4", max_length=120)
    file_size_bytes: int = Field(default=0, ge=0)


@router.post("/upload-session")
def create_upload_session(
    payload: UploadSessionRequest,
    current_user: User = Depends(get_current_user),
):
    """Return a Neon Function direct upload grant when configured (bypasses Vercel's 4.5 MB body cap)."""
    settings = get_settings()
    mime = (payload.content_type or "video/mp4").lower()
    if mime not in ALLOWED_VIDEO_MIME_TYPES and not mime.startswith("video/"):
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported MIME type '{mime}'. Please upload a valid video file (MP4, MOV, WebM, MKV, AVI).",
        )
    max_bytes = settings.MAX_VIDEO_UPLOAD_MB * 1024 * 1024
    if payload.file_size_bytes > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds maximum allowed size of {settings.MAX_VIDEO_UPLOAD_MB} MB.",
        )

    fn_url = settings.neon_function_url("hello")
    if can_use_neon_storage_upload() and fn_url:
        safe_name = sanitize_filename(payload.filename)
        stored_filename = f"{current_user.id}_{uuid.uuid4().hex[:12]}_{safe_name}"
        object_key = f"{current_user.id}/{stored_filename}"
        upload_token = mint_upload_token(current_user.id, object_key)
        return {
            "mode": "neon_function",
            "upload_url": f"{fn_url}/storage/upload",
            "upload_token": upload_token,
            "object_key": object_key,
            "stored_filename": stored_filename,
            "original_filename": safe_name,
            "mime_type": mime,
        }

    return {"mode": "direct"}


@router.post("/complete-upload", response_model=UploadedMediaResponse, status_code=status.HTTP_201_CREATED)
def complete_remote_upload(
    payload: CompleteUploadRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Register a video uploaded directly to Neon Object Storage in Lakebase Postgres."""
    expected_prefix = f"{current_user.id}/"
    if not payload.object_key.startswith(expected_prefix):
        raise HTTPException(status_code=403, detail="Invalid object key for current user.")

    media = UploadedMedia(
        user_id=current_user.id,
        original_filename=sanitize_filename(payload.original_filename),
        stored_filename=sanitize_filename(payload.stored_filename),
        file_path=f"{NEON_S3_PREFIX}{payload.object_key}",
        mime_type=(payload.mime_type or "video/mp4").lower(),
        file_size_bytes=payload.file_size_bytes,
        analysis_status="uploaded",
    )
    db.add(media)
    db.commit()
    db.refresh(media)
    return UploadedMediaResponse.model_validate(media)


@router.post("/upload", response_model=UploadedMediaResponse, status_code=status.HTTP_201_CREATED)
async def upload_video(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    settings = get_settings()
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing video filename.")

    mime = (file.content_type or "application/octet-stream").lower()
    if mime not in ALLOWED_VIDEO_MIME_TYPES and not mime.startswith("video/"):
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported MIME type '{mime}'. Please upload a valid video file (MP4, MOV, WebM, MKV, AVI).",
        )

    safe_name = sanitize_filename(file.filename)
    unique_name = f"{current_user.id}_{uuid.uuid4().hex[:12]}_{safe_name}"
    dest_path = Path(settings.UPLOAD_DIR) / unique_name
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    max_bytes = settings.MAX_VIDEO_UPLOAD_MB * 1024 * 1024
    written = 0
    try:
        with open(dest_path, "wb") as out:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                written += len(chunk)
                if written > max_bytes:
                    out.close()
                    dest_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=413,
                        detail=f"File exceeds maximum allowed size of {settings.MAX_VIDEO_UPLOAD_MB} MB.",
                    )
                out.write(chunk)
    except HTTPException:
        raise
    except Exception as exc:
        dest_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Failed to store uploaded file: {exc}")

    ok, reason = verify_video_file_magic(str(dest_path), safe_name)
    if not ok:
        dest_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=reason)

    meta = extract_video_metadata(str(dest_path))

    media = UploadedMedia(
        user_id=current_user.id,
        original_filename=safe_name,
        stored_filename=unique_name,
        file_path=str(dest_path),
        mime_type=mime,
        analysis_status="uploaded",
        **meta,
    )
    db.add(media)
    db.commit()
    db.refresh(media)
    return UploadedMediaResponse.model_validate(media)


@router.get("", response_model=List[UploadedMediaResponse])
def list_uploaded_videos(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(UploadedMedia)
        .filter(UploadedMedia.user_id == current_user.id)
        .order_by(desc(UploadedMedia.created_at))
        .limit(50)
        .all()
    )
    return [UploadedMediaResponse.model_validate(r) for r in rows]


@router.post("/analyze", response_model=UploadedMediaResponse)
def analyze_video(
    payload: VideoAnalyzeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    media = (
        db.query(UploadedMedia)
        .filter(UploadedMedia.id == payload.video_id, UploadedMedia.user_id == current_user.id)
        .first()
    )
    if not media:
        raise HTTPException(status_code=404, detail="Uploaded video not found.")
    try:
        local_video_path = ensure_local_video_file(media.file_path, media.stored_filename)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=f"Could not retrieve video from storage: {exc}")
    if not os.path.exists(local_video_path):
        raise HTTPException(status_code=404, detail="Video file is no longer available on server storage.")

    media.analysis_status = "analyzing"
    db.commit()

    frames = sample_representative_frames(local_video_path, media.id, media.duration_seconds)
    transcript_text, segments, is_fallback = transcribe_video_audio(local_video_path, media.id)
    meta_dict = {
        "duration_seconds": media.duration_seconds,
        "width": media.width,
        "height": media.height,
        "aspect_ratio": media.aspect_ratio,
        "frame_rate": media.frame_rate,
    }
    content_analysis = analyze_uploaded_video_content(
        filename=media.original_filename,
        metadata=meta_dict,
        transcript_text=transcript_text,
        transcript_segments=segments,
        frames=frames,
        custom_notes=payload.custom_notes,
    )

    media.frames_json = frames
    media.transcript_text = transcript_text
    media.transcript_segments_json = segments
    media.content_analysis_json = content_analysis
    media.is_demo_data = is_fallback
    media.analysis_status = "analyzed"
    db.commit()
    db.refresh(media)
    return UploadedMediaResponse.model_validate(media)


@router.get("/{video_id}", response_model=UploadedMediaResponse)
def get_uploaded_video(
    video_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    media = (
        db.query(UploadedMedia)
        .filter(UploadedMedia.id == video_id, UploadedMedia.user_id == current_user.id)
        .first()
    )
    if not media:
        raise HTTPException(status_code=404, detail="Uploaded video not found.")
    return UploadedMediaResponse.model_validate(media)


@router.post("/{video_id}/generate-metadata", response_model=UploadedMediaResponse)
def generate_metadata(
    video_id: str,
    payload: GenerateMetadataRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    media = (
        db.query(UploadedMedia)
        .filter(UploadedMedia.id == video_id, UploadedMedia.user_id == current_user.id)
        .first()
    )
    if not media:
        raise HTTPException(status_code=404, detail="Uploaded video not found.")

    if not media.content_analysis_json:
        # Ensure basic analysis exists first
        media.content_analysis_json = analyze_uploaded_video_content(
            filename=media.original_filename,
            metadata={"duration_seconds": media.duration_seconds, "width": media.width, "height": media.height},
            transcript_text=media.transcript_text,
            transcript_segments=media.transcript_segments_json or [],
            frames=media.frames_json or [],
        )

    generated = generate_video_publish_metadata(
        filename=media.original_filename,
        content_analysis=media.content_analysis_json,
        transcript_segments=media.transcript_segments_json or [],
        tone=payload.tone,
        target_keywords=payload.target_keywords,
    )
    media.generated_metadata_json = generated
    media.analysis_status = "metadata_ready"
    db.commit()
    db.refresh(media)
    return UploadedMediaResponse.model_validate(media)


def _cleanup_media_files(media: UploadedMedia) -> None:
    settings = get_settings()
    delete_remote_video_object(media.file_path)
    if media.file_path and os.path.exists(media.file_path):
        try:
            os.unlink(media.file_path)
        except OSError:
            pass
    local_cached = Path(settings.UPLOAD_DIR) / media.stored_filename
    if local_cached.exists():
        try:
            local_cached.unlink()
        except OSError:
            pass
    frames_dir = Path(settings.FRAMES_DIR) / media.id
    if frames_dir.exists():
        shutil.rmtree(frames_dir, ignore_errors=True)


@router.delete("/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_uploaded_video(
    video_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    media = (
        db.query(UploadedMedia)
        .filter(UploadedMedia.id == video_id, UploadedMedia.user_id == current_user.id)
        .first()
    )
    if not media:
        raise HTTPException(status_code=404, detail="Uploaded video not found.")

    active_upload = (
        db.query(PublishingJob)
        .filter(PublishingJob.media_id == media.id, PublishingJob.status == "uploading")
        .first()
    )
    if active_upload:
        raise HTTPException(status_code=400, detail="Cannot delete a video while it is actively uploading to YouTube.")

    _cleanup_media_files(media)
    db.delete(media)
    db.commit()
    return None


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def clear_uploaded_videos_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = db.query(UploadedMedia).filter(UploadedMedia.user_id == current_user.id).all()
    for media in rows:
        active_upload = (
            db.query(PublishingJob)
            .filter(PublishingJob.media_id == media.id, PublishingJob.status == "uploading")
            .first()
        )
        if active_upload:
            continue
        _cleanup_media_files(media)
        db.delete(media)
    db.commit()
    return None
