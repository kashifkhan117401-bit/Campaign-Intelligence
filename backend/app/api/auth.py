"""Authentication, user profile, password reset, and workspace settings routes."""
from __future__ import annotations

import os
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user
from app.core.captcha import generate_captcha_challenge, verify_captcha_challenge
from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_secure_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models.ads import AdvertisingStrategy
from app.models.analysis import VideoAnalysis
from app.models.content import GeneratedContent, PublishingJob, UploadedMedia
from app.models.reporting import CampaignRecord, PDFReport
from app.models.user import RefreshToken, User, UserProfile, UserSettings
from app.schemas.auth import (
    CaptchaResponse,
    ChangePasswordRequest,
    DeleteAccountRequest,
    IntegrationStatusResponse,
    LoginRequest,
    LogoutRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserProfileResponse,
    UserProfileUpdate,
    UserResponse,
    UserSettingsResponse,
    UserSettingsUpdate,
)
from app.services.video_processor import is_ffmpeg_available

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _issue_tokens(db: Session, user: User) -> TokenResponse:
    settings = get_settings()
    access_token = create_access_token(subject=user.id, role=user.role)
    refresh_token, expires_at = create_refresh_token(subject=user.id)

    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(refresh_token),
            expires_at=expires_at,
        )
    )
    db.commit()

    hydrated = (
        db.query(User)
        .options(joinedload(User.profile), joinedload(User.settings))
        .filter(User.id == user.id)
        .first()
    )
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(hydrated),
    )


@router.get("/captcha", response_model=CaptchaResponse)
def get_captcha():
    token, image_data_url, expires_in = generate_captcha_challenge()
    return CaptchaResponse(
        captcha_token=token,
        image_data_url=image_data_url,
        expires_in=expires_in,
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    settings = get_settings()
    if not payload.accepted_terms:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must accept the Terms & Conditions and Privacy & Security Policy to create an account.",
        )
    if settings.CAPTCHA_ENABLED:
        ok, err = verify_captcha_challenge(payload.captcha_token, payload.captcha_answer)
        if not ok:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err)

    email = payload.email.lower().strip()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists.",
        )

    user = User(
        email=email,
        hashed_password=hash_password(payload.password),
        role="user",
        is_active=True,
    )
    db.add(user)
    db.flush()

    db.add(
        UserProfile(
            user_id=user.id,
            full_name=payload.full_name.strip() or email.split("@")[0].title(),
            company_name=payload.company_name.strip(),
            onboarding_completed=False,
        )
    )
    db.add(UserSettings(user_id=user.id))
    db.commit()
    return _issue_tokens(db, user)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    settings = get_settings()
    if settings.CAPTCHA_ENABLED:
        ok, err = verify_captcha_challenge(payload.captcha_token, payload.captcha_answer)
        if not ok:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err)

    email = payload.email.lower().strip()
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated.",
        )
    return _issue_tokens(db, user)


@router.post("/refresh", response_model=TokenResponse)
def refresh_tokens(payload: RefreshRequest, db: Session = Depends(get_db)):
    decoded = decode_token(payload.refresh_token)
    if not decoded or decoded.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token.")

    t_hash = hash_token(payload.refresh_token)
    stored = (
        db.query(RefreshToken)
        .filter(RefreshToken.token_hash == t_hash, RefreshToken.revoked.is_(False))
        .first()
    )
    now = datetime.now(timezone.utc)
    if not stored:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token revoked or unknown.")

    exp = stored.expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if exp <= now:
        stored.revoked = True
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired.")

    user = db.query(User).filter(User.id == stored.user_id, User.is_active.is_(True)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")

    # Rotate refresh token
    stored.revoked = True
    db.commit()
    return _issue_tokens(db, user)


@router.post("/logout")
def logout(
    payload: LogoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.refresh_token:
        t_hash = hash_token(payload.refresh_token)
        stored = (
            db.query(RefreshToken)
            .filter(RefreshToken.token_hash == t_hash, RefreshToken.user_id == current_user.id)
            .first()
        )
        if stored:
            stored.revoked = True
    else:
        db.query(RefreshToken).filter(
            RefreshToken.user_id == current_user.id, RefreshToken.revoked.is_(False)
        ).update({"revoked": True})
    db.commit()
    return {"message": "Logged out successfully."}


@router.post("/password-reset/request")
def request_password_reset(payload: PasswordResetRequest, db: Session = Depends(get_db)):
    settings = get_settings()
    email = payload.email.lower().strip()
    user = db.query(User).filter(User.email == email).first()
    dev_token = None
    if user:
        raw_token = generate_secure_token(24)
        user.reset_token_hash = hash_token(raw_token)
        user.reset_token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        db.commit()
        if settings.DEBUG:
            dev_token = raw_token

    resp = {
        "message": "If an account exists for that email, password reset instructions have been issued."
    }
    if dev_token:
        resp["dev_reset_token"] = dev_token
    return resp


@router.post("/password-reset/confirm")
def confirm_password_reset(payload: PasswordResetConfirm, db: Session = Depends(get_db)):
    t_hash = hash_token(payload.token)
    user = db.query(User).filter(User.reset_token_hash == t_hash).first()
    if not user or not user.reset_token_expires_at:
        raise HTTPException(status_code=400, detail="Invalid or expired password reset token.")

    exp = user.reset_token_expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if exp <= datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Password reset token has expired.")

    user.hashed_password = hash_password(payload.new_password)
    user.reset_token_hash = None
    user.reset_token_expires_at = None
    db.query(RefreshToken).filter(RefreshToken.user_id == user.id).update({"revoked": True})
    db.commit()
    return {"message": "Password updated successfully. Please log in with your new password."}


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)


@router.put("/profile", response_model=UserProfileResponse)
def update_profile(
    payload: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if not profile:
        profile = UserProfile(user_id=current_user.id)
        db.add(profile)

    for key, val in payload.model_dump(exclude_unset=True).items():
        setattr(profile, key, val)
    db.commit()
    db.refresh(profile)
    return UserProfileResponse.model_validate(profile)


@router.put("/settings", response_model=UserSettingsResponse)
def update_settings(
    payload: UserSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_settings = db.query(UserSettings).filter(UserSettings.user_id == current_user.id).first()
    if not user_settings:
        user_settings = UserSettings(user_id=current_user.id)
        db.add(user_settings)

    for key, val in payload.model_dump(exclude_unset=True).items():
        setattr(user_settings, key, val)
    db.commit()
    db.refresh(user_settings)
    return UserSettingsResponse.model_validate(user_settings)


@router.get("/integrations", response_model=IntegrationStatusResponse)
def get_integrations_status(_current_user: User = Depends(get_current_user)):
    settings = get_settings()
    return IntegrationStatusResponse(
        ai_configured=settings.has_ai_key,
        gemini_configured=settings.has_gemini_key,
        openai_configured=settings.has_openai_key,
        youtube_api_configured=settings.has_youtube_api_key,
        google_oauth_configured=settings.has_google_oauth,
        ffmpeg_available=is_ffmpeg_available(),
        allow_demo_mode=settings.ALLOW_DEMO_MODE,
        llm_provider=settings.LLM_PROVIDER,
        llm_model=settings.active_llm_model,
    )


@router.post("/password/change")
def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect.")
    current_user.hashed_password = hash_password(payload.new_password)
    db.query(RefreshToken).filter(RefreshToken.user_id == current_user.id).update({"revoked": True})
    db.commit()
    return {"message": "Password updated successfully. All other sessions have been signed out."}


@router.get("/privacy/export")
def export_user_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    uid = current_user.id
    analyses = db.query(VideoAnalysis).filter(VideoAnalysis.user_id == uid).all()
    contents = db.query(GeneratedContent).filter(GeneratedContent.user_id == uid).all()
    strategies = db.query(AdvertisingStrategy).filter(AdvertisingStrategy.user_id == uid).all()
    reports = db.query(PDFReport).filter(PDFReport.user_id == uid).all()
    jobs = db.query(PublishingJob).filter(PublishingJob.user_id == uid).all()
    activity = db.query(CampaignRecord).filter(CampaignRecord.user_id == uid).all()

    return {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "account": {
            "id": current_user.id,
            "email": current_user.email,
            "role": current_user.role,
            "created_at": current_user.created_at.isoformat(),
        },
        "profile": UserProfileResponse.model_validate(current_user.profile).model_dump()
        if current_user.profile
        else None,
        "settings": UserSettingsResponse.model_validate(current_user.settings).model_dump()
        if current_user.settings
        else None,
        "counts": {
            "analyses": len(analyses),
            "content_packs": len(contents),
            "ads_strategies": len(strategies),
            "pdf_reports": len(reports),
            "publishing_jobs": len(jobs),
            "campaign_history_records": len(activity),
        },
        "analyses": [
            {
                "id": a.id,
                "status": a.status,
                "analyzed_comments_count": a.analyzed_comments_count,
                "positive_pct": a.positive_pct,
                "negative_pct": a.negative_pct,
                "neutral_pct": a.neutral_pct,
                "created_at": a.created_at.isoformat(),
            }
            for a in analyses
        ],
        "content_packs": [
            {"id": c.id, "title": c.title, "tone": c.tone, "status": c.status, "created_at": c.created_at.isoformat()}
            for c in contents
        ],
        "ads_strategies": [
            {
                "id": s.id,
                "campaign_name": s.campaign_name,
                "marketing_objective": s.marketing_objective,
                "available_budget": s.available_budget,
                "currency": s.currency,
                "created_at": s.created_at.isoformat(),
            }
            for s in strategies
        ],
        "campaign_history": [
            {
                "id": r.id,
                "name": r.name,
                "record_type": r.record_type,
                "status": r.status,
                "summary": r.summary,
                "created_at": r.created_at.isoformat(),
            }
            for r in activity
        ],
    }


@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    payload: DeleteAccountRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.confirm_text.strip().upper() != "DELETE":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Please type DELETE to confirm account deletion.")
    if not verify_password(payload.password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect password.")

    settings = get_settings()
    for media in db.query(UploadedMedia).filter(UploadedMedia.user_id == current_user.id).all():
        if media.file_path and os.path.exists(media.file_path):
            try:
                os.unlink(media.file_path)
            except OSError:
                pass
        frames_dir = Path(settings.FRAMES_DIR) / media.id
        if frames_dir.exists():
            shutil.rmtree(frames_dir, ignore_errors=True)

    for rep in db.query(PDFReport).filter(PDFReport.user_id == current_user.id).all():
        if rep.file_path and os.path.exists(rep.file_path):
            try:
                os.unlink(rep.file_path)
            except OSError:
                pass

    db.delete(current_user)
    db.commit()
    return None
