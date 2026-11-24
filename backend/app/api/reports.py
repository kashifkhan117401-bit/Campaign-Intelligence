"""Professional ReportLab PDF report generation, regeneration, and download routes."""
from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import desc
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.models.ads import AdvertisingStrategy
from app.models.analysis import AudienceInsight, VideoAnalysis
from app.models.content import GeneratedContent
from app.models.reporting import CampaignRecord, PDFReport
from app.models.user import User
from app.reports.pdf_generator import generate_intelligence_pdf
from app.schemas.reporting import PDFReportResponse, ReportGenerateRequest

router = APIRouter(prefix="/reports", tags=["PDF Reports"])


def _build_pdf_for_records(
    *,
    db: Session,
    user: User,
    analysis: VideoAnalysis,
    content: Optional[GeneratedContent],
    strategy: Optional[AdvertisingStrategy],
    title: str,
    output_path: str,
) -> tuple[int, int]:
    insight = db.query(AudienceInsight).filter(AudienceInsight.analysis_id == analysis.id).first()

    video_dict = {
        "youtube_video_id": analysis.video.youtube_video_id if analysis.video else "",
        "url": analysis.video.url if analysis.video else "",
        "title": analysis.video.title if analysis.video else "YouTube Video",
        "channel_title": analysis.video.channel_title if analysis.video else "",
        "duration_iso": analysis.video.duration_iso if analysis.video else "",
        "view_count": analysis.video.view_count if analysis.video else 0,
        "like_count": analysis.video.like_count if analysis.video else 0,
        "comment_count": analysis.video.comment_count if analysis.video else 0,
        "comments_disabled": analysis.video.comments_disabled if analysis.video else False,
        "is_demo_data": analysis.video.is_demo_data if analysis.video else False,
    }
    analysis_dict = {
        "requested_max_comments": analysis.requested_max_comments,
        "collected_comments_count": analysis.collected_comments_count,
        "analyzed_comments_count": analysis.analyzed_comments_count,
        "positive_count": analysis.positive_count,
        "negative_count": analysis.negative_count,
        "neutral_count": analysis.neutral_count,
        "positive_pct": analysis.positive_pct,
        "negative_pct": analysis.negative_pct,
        "neutral_pct": analysis.neutral_pct,
        "emotion_distribution_json": analysis.emotion_distribution_json,
        "topics_json": analysis.topics_json,
        "keywords_json": analysis.keywords_json,
        "pain_points_json": analysis.pain_points_json,
        "faqs_json": analysis.faqs_json,
        "ai_disclaimer": analysis.ai_disclaimer,
        "is_demo_data": analysis.is_demo_data,
    }
    insight_dict = (
        {
            "opportunity_score": insight.opportunity_score,
            "interests_json": insight.interests_json,
            "content_gaps_json": insight.content_gaps_json,
            "product_opportunities_json": insight.product_opportunities_json,
            "customer_objections_json": insight.customer_objections_json,
            "marketing_angles_json": insight.marketing_angles_json,
            "top_10_questions_json": insight.top_10_questions_json,
        }
        if insight
        else None
    )
    content_dict = (
        {
            "youtube_content_json": content.youtube_content_json,
            "seo_json": content.seo_json,
            "content_strategy_json": content.content_strategy_json,
        }
        if content
        else None
    )
    strategy_dict = None
    tiers_list = None
    if strategy:
        strategy_dict = {
            "campaign_name": strategy.campaign_name,
            "marketing_objective": strategy.marketing_objective,
            "campaign_type_and_format": strategy.campaign_type_and_format,
            "target_country": strategy.target_country,
            "target_audience": strategy.target_audience,
            "executive_report": strategy.executive_report,
            "audience_segments_json": strategy.audience_segments_json,
            "creative_recommendations_json": strategy.creative_recommendations_json,
            "ab_testing_ideas_json": strategy.ab_testing_ideas_json,
        }
        tiers_list = [
            {
                "tier": b.tier,
                "currency": b.currency,
                "daily_budget": b.daily_budget,
                "total_budget": b.total_budget,
                "assumed_cpv": b.assumed_cpv,
                "estimated_views": b.estimated_views,
                "estimated_impressions": b.estimated_impressions,
                "estimated_clicks": b.estimated_clicks,
            }
            for b in (strategy.budget_estimates or [])
        ]

    return generate_intelligence_pdf(
        output_path=output_path,
        report_title=title,
        video=video_dict,
        analysis=analysis_dict,
        insight=insight_dict,
        content=content_dict,
        strategy=strategy_dict,
        budget_tiers=tiers_list,
    )


@router.post("/generate", response_model=PDFReportResponse, status_code=status.HTTP_201_CREATED)
def generate_report(
    payload: ReportGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    analysis = (
        db.query(VideoAnalysis)
        .options(joinedload(VideoAnalysis.video))
        .filter(VideoAnalysis.id == payload.analysis_id, VideoAnalysis.user_id == current_user.id)
        .first()
    )
    if not analysis:
        raise HTTPException(status_code=404, detail="Video analysis not found.")

    content = None
    if payload.content_id:
        content = (
            db.query(GeneratedContent)
            .filter(GeneratedContent.id == payload.content_id, GeneratedContent.user_id == current_user.id)
            .first()
        )
    else:
        content = (
            db.query(GeneratedContent)
            .filter(GeneratedContent.analysis_id == analysis.id, GeneratedContent.user_id == current_user.id)
            .order_by(desc(GeneratedContent.created_at))
            .first()
        )

    strategy = None
    if payload.strategy_id:
        strategy = (
            db.query(AdvertisingStrategy)
            .options(joinedload(AdvertisingStrategy.budget_estimates))
            .filter(AdvertisingStrategy.id == payload.strategy_id, AdvertisingStrategy.user_id == current_user.id)
            .first()
        )
    else:
        strategy = (
            db.query(AdvertisingStrategy)
            .options(joinedload(AdvertisingStrategy.budget_estimates))
            .filter(AdvertisingStrategy.analysis_id == analysis.id, AdvertisingStrategy.user_id == current_user.id)
            .order_by(desc(AdvertisingStrategy.created_at))
            .first()
        )

    settings = get_settings()
    title = payload.title or f"Campaign Intelligence Report — {(analysis.video.title if analysis.video else 'Video')[:90]}"
    filename = f"campaign_intelligence_report_{uuid.uuid4().hex[:12]}.pdf"
    output_path = str(Path(settings.REPORTS_DIR) / filename)

    file_size, page_count = _build_pdf_for_records(
        db=db,
        user=current_user,
        analysis=analysis,
        content=content,
        strategy=strategy,
        title=title,
        output_path=output_path,
    )

    report = PDFReport(
        user_id=current_user.id,
        analysis_id=analysis.id,
        content_id=content.id if content else None,
        strategy_id=strategy.id if strategy else None,
        title=title[:250],
        file_path=output_path,
        file_size_bytes=file_size,
        page_count=page_count,
        status="ready",
        version=1,
    )
    db.add(report)
    db.flush()

    db.add(
        CampaignRecord(
            user_id=current_user.id,
            analysis_id=analysis.id,
            report_id=report.id,
            name=f"PDF Report: {report.title[:120]}",
            record_type="pdf_report",
            status="completed",
            summary=f"Generated {page_count}-page PDF intelligence report ({round(file_size / 1024, 1)} KB).",
            metadata_json={"page_count": page_count, "file_size_bytes": file_size},
        )
    )
    db.commit()
    db.refresh(report)
    return PDFReportResponse.model_validate(report)


@router.get("", response_model=List[PDFReportResponse])
def list_reports(
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(PDFReport)
        .filter(PDFReport.user_id == current_user.id)
        .order_by(desc(PDFReport.created_at))
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [PDFReportResponse.model_validate(r) for r in rows]


@router.get("/{report_id}/download")
def download_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    report = (
        db.query(PDFReport)
        .filter(PDFReport.id == report_id, PDFReport.user_id == current_user.id)
        .first()
    )
    if not report:
        raise HTTPException(status_code=404, detail="PDF report not found.")
    if not os.path.exists(report.file_path):
        raise HTTPException(status_code=404, detail="PDF file missing on disk. Please regenerate the report.")

    safe_download_name = f"Campaign_Intelligence_Report_v{report.version}_{report.id[:8]}.pdf"
    return FileResponse(
        path=report.file_path,
        media_type="application/pdf",
        filename=safe_download_name,
    )


@router.post("/{report_id}/regenerate", response_model=PDFReportResponse)
def regenerate_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    report = (
        db.query(PDFReport)
        .filter(PDFReport.id == report_id, PDFReport.user_id == current_user.id)
        .first()
    )
    if not report:
        raise HTTPException(status_code=404, detail="PDF report not found.")

    analysis = (
        db.query(VideoAnalysis)
        .options(joinedload(VideoAnalysis.video))
        .filter(VideoAnalysis.id == report.analysis_id, VideoAnalysis.user_id == current_user.id)
        .first()
    )
    if not analysis:
        raise HTTPException(status_code=404, detail="Source video analysis no longer exists.")

    content = (
        db.query(GeneratedContent)
        .filter(GeneratedContent.id == report.content_id)
        .first()
        if report.content_id
        else None
    )
    strategy = (
        db.query(AdvertisingStrategy)
        .options(joinedload(AdvertisingStrategy.budget_estimates))
        .filter(AdvertisingStrategy.id == report.strategy_id)
        .first()
        if report.strategy_id
        else None
    )

    file_size, page_count = _build_pdf_for_records(
        db=db,
        user=current_user,
        analysis=analysis,
        content=content,
        strategy=strategy,
        title=report.title,
        output_path=report.file_path,
    )
    report.file_size_bytes = file_size
    report.page_count = page_count
    report.version += 1
    report.status = "ready"
    db.commit()
    db.refresh(report)
    return PDFReportResponse.model_validate(report)


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    report = (
        db.query(PDFReport)
        .filter(PDFReport.id == report_id, PDFReport.user_id == current_user.id)
        .first()
    )
    if not report:
        raise HTTPException(status_code=404, detail="PDF report not found.")
    if report.file_path and os.path.exists(report.file_path):
        try:
            os.unlink(report.file_path)
        except OSError:
            pass
    db.delete(report)
    db.commit()
    return None


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def clear_reports_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = db.query(PDFReport).filter(PDFReport.user_id == current_user.id).all()
    for report in rows:
        if report.file_path and os.path.exists(report.file_path):
            try:
                os.unlink(report.file_path)
            except OSError:
                pass
        db.delete(report)
    db.commit()
    return None
