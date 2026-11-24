"""AI Content Generation Studio CRUD endpoints."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc
from sqlalchemy.orm import Session, joinedload

from app.ai.content_engine import generate_content_suite
from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.analysis import AudienceInsight, VideoAnalysis
from app.models.content import GeneratedContent
from app.models.reporting import CampaignRecord
from app.models.user import User
from app.schemas.content import (
    ContentGenerateRequest,
    ContentUpdateRequest,
    GeneratedContentResponse,
)

router = APIRouter(prefix="/content", tags=["AI Content Studio"])


@router.post("/generate", response_model=GeneratedContentResponse, status_code=status.HTTP_201_CREATED)
def generate_content(
    payload: ContentGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    analysis_ctx = None
    linked_analysis_id = None

    if payload.analysis_id:
        analysis = (
            db.query(VideoAnalysis)
            .options(joinedload(VideoAnalysis.video))
            .filter(
                VideoAnalysis.id == payload.analysis_id,
                VideoAnalysis.user_id == current_user.id,
            )
            .first()
        )
        if not analysis:
            raise HTTPException(status_code=404, detail="Referenced video analysis not found.")

        insight = (
            db.query(AudienceInsight)
            .filter(AudienceInsight.analysis_id == analysis.id)
            .first()
        )
        linked_analysis_id = analysis.id
        analysis_ctx = {
            "video_title": analysis.video.title if analysis.video else "",
            "positive_pct": analysis.positive_pct,
            "negative_pct": analysis.negative_pct,
            "keywords": [k.get("keyword") for k in (analysis.keywords_json or [])],
            "pain_points": [p.get("pain_point") for p in (analysis.pain_points_json or [])],
            "top_questions": [
                q.get("question") for q in (insight.top_10_questions_json if insight else [])
            ]
            or (analysis.faqs_json or []),
            "content_gaps": insight.content_gaps_json if insight else [],
        }

    if not analysis_ctx and not payload.topic_brief.strip():
        raise HTTPException(
            status_code=422,
            detail="Provide either a completed analysis_id or a topic_brief to generate content.",
        )

    result = generate_content_suite(
        tone=payload.tone,
        topic_brief=payload.topic_brief.strip(),
        target_audience=payload.target_audience.strip(),
        custom_instructions=payload.custom_instructions.strip(),
        analysis_context=analysis_ctx,
    )

    content = GeneratedContent(
        user_id=current_user.id,
        analysis_id=linked_analysis_id,
        title=str(result["title"])[:250],
        tone=payload.tone,
        status="draft",
        topic_brief=payload.topic_brief.strip() or (analysis_ctx["video_title"] if analysis_ctx else ""),
        youtube_content_json=result["youtube_content_json"],
        seo_json=result["seo_json"],
        social_media_json=result["social_media_json"],
        content_strategy_json=result["content_strategy_json"],
        disclaimer=result["disclaimer"],
        is_demo_data=bool(result.get("is_demo_data", False)),
    )
    db.add(content)
    db.flush()

    db.add(
        CampaignRecord(
            user_id=current_user.id,
            analysis_id=linked_analysis_id,
            content_id=content.id,
            name=f"Content Pack: {content.title[:120]}",
            record_type="content_generation",
            status="completed",
            summary=f"Generated {payload.tone} YouTube script, SEO pack, social media posts & 10 future ideas.",
            metadata_json={"tone": payload.tone, "is_demo_data": content.is_demo_data},
        )
    )
    db.commit()
    db.refresh(content)
    return GeneratedContentResponse.model_validate(content)


@router.get("", response_model=List[GeneratedContentResponse])
def list_content(
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(GeneratedContent)
        .filter(GeneratedContent.user_id == current_user.id)
        .order_by(desc(GeneratedContent.created_at))
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [GeneratedContentResponse.model_validate(r) for r in rows]


@router.get("/{content_id}", response_model=GeneratedContentResponse)
def get_content(
    content_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = (
        db.query(GeneratedContent)
        .filter(GeneratedContent.id == content_id, GeneratedContent.user_id == current_user.id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Generated content not found.")
    return GeneratedContentResponse.model_validate(row)


@router.put("/{content_id}", response_model=GeneratedContentResponse)
def update_content(
    content_id: str,
    payload: ContentUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = (
        db.query(GeneratedContent)
        .filter(GeneratedContent.id == content_id, GeneratedContent.user_id == current_user.id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Generated content not found.")

    for key, val in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, val)
    db.commit()
    db.refresh(row)
    return GeneratedContentResponse.model_validate(row)


@router.delete("/{content_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_content(
    content_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = (
        db.query(GeneratedContent)
        .filter(GeneratedContent.id == content_id, GeneratedContent.user_id == current_user.id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Generated content not found.")
    db.delete(row)
    db.commit()
    return None


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def clear_content_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = db.query(GeneratedContent).filter(GeneratedContent.user_id == current_user.id).all()
    for row in rows:
        db.delete(row)
    db.commit()
    return None
