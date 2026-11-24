"""YouTube Advertising Strategy & Budget Planner endpoints."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc
from sqlalchemy.orm import Session, joinedload

from app.ai.ads_engine import calculate_budget_tiers, generate_ads_strategy
from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.ads import AdvertisingStrategy, BudgetEstimate
from app.models.reporting import CampaignRecord
from app.models.user import User, UserSettings
from app.schemas.ads import (
    AdsStrategyRequest,
    AdvertisingStrategyResponse,
    BudgetEstimateRequest,
    BudgetEstimateResponse,
    BudgetTierEstimate,
)

router = APIRouter(prefix="/ads", tags=["Advertising Strategy"])


def _user_benchmarks(db: Session, user_id: str) -> tuple[float, float, float]:
    s = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
    if s:
        return s.benchmark_cpv, s.benchmark_cpm, s.benchmark_ctr
    return 0.035, 8.50, 0.012


@router.post("/budget-estimate", response_model=BudgetEstimateResponse)
def estimate_ad_budget(
    payload: BudgetEstimateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    default_cpv, default_cpm, default_ctr = _user_benchmarks(db, current_user.id)
    result = calculate_budget_tiers(
        available_budget=payload.available_budget,
        campaign_duration_days=payload.campaign_duration_days,
        currency=payload.currency,
        target_country=payload.target_country,
        industry_niche=payload.industry_niche,
        marketing_objective=payload.marketing_objective,
        base_cpv=payload.custom_cpv or default_cpv,
        base_cpm=payload.custom_cpm or default_cpm,
        base_ctr=payload.custom_ctr or default_ctr,
    )
    return BudgetEstimateResponse(
        currency=result["currency"],
        campaign_duration_days=result["campaign_duration_days"],
        formula_note=result["formula_note"],
        is_illustrative_estimate=True,
        disclaimer=result["disclaimer"],
        tiers=[BudgetTierEstimate(**t) for t in result["tiers"]],
    )


@router.post("/strategy", response_model=AdvertisingStrategyResponse, status_code=status.HTTP_201_CREATED)
def create_ads_strategy(
    payload: AdsStrategyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    default_cpv, default_cpm, default_ctr = _user_benchmarks(db, current_user.id)
    generated = generate_ads_strategy(
        campaign_name=payload.campaign_name,
        video_context=payload.video_context,
        target_country=payload.target_country,
        target_audience=payload.target_audience,
        industry_niche=payload.industry_niche,
        marketing_objective=payload.marketing_objective,
        campaign_duration_days=payload.campaign_duration_days,
        available_budget=payload.available_budget,
        currency=payload.currency,
        base_cpv=payload.custom_cpv or default_cpv,
        base_cpm=payload.custom_cpm or default_cpm,
        base_ctr=payload.custom_ctr or default_ctr,
    )

    tiers_data = generated.pop("budget_tiers", [])
    strategy = AdvertisingStrategy(
        user_id=current_user.id,
        analysis_id=payload.analysis_id,
        media_id=payload.media_id,
        campaign_name=payload.campaign_name,
        video_context=payload.video_context,
        target_country=payload.target_country,
        target_audience=payload.target_audience,
        industry_niche=payload.industry_niche,
        marketing_objective=payload.marketing_objective,
        campaign_duration_days=payload.campaign_duration_days,
        available_budget=payload.available_budget,
        currency=payload.currency.upper(),
        **generated,
    )
    db.add(strategy)
    db.flush()

    for t in tiers_data:
        db.add(
            BudgetEstimate(
                user_id=current_user.id,
                strategy_id=strategy.id,
                **t,
            )
        )

    db.add(
        CampaignRecord(
            user_id=current_user.id,
            analysis_id=payload.analysis_id,
            strategy_id=strategy.id,
            name=f"Ads Plan: {strategy.campaign_name}",
            record_type="ads_strategy",
            status="completed",
            summary=(
                f"{strategy.marketing_objective} in {strategy.target_country} — "
                f"Budget {strategy.available_budget:,.2f} {strategy.currency} over {strategy.campaign_duration_days} days."
            ),
            metadata_json={"objective": strategy.marketing_objective, "currency": strategy.currency},
        )
    )
    db.commit()

    hydrated = (
        db.query(AdvertisingStrategy)
        .options(joinedload(AdvertisingStrategy.budget_estimates))
        .filter(AdvertisingStrategy.id == strategy.id)
        .first()
    )
    return AdvertisingStrategyResponse.model_validate(hydrated)


@router.get("/history", response_model=List[AdvertisingStrategyResponse])
def list_ads_history(
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(AdvertisingStrategy)
        .options(joinedload(AdvertisingStrategy.budget_estimates))
        .filter(AdvertisingStrategy.user_id == current_user.id)
        .order_by(desc(AdvertisingStrategy.created_at))
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [AdvertisingStrategyResponse.model_validate(r) for r in rows]


@router.delete("/history/{strategy_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ads_strategy(
    strategy_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = (
        db.query(AdvertisingStrategy)
        .filter(AdvertisingStrategy.id == strategy_id, AdvertisingStrategy.user_id == current_user.id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Advertising strategy not found.")
    db.delete(row)
    db.commit()
    return None


@router.delete("/history", status_code=status.HTTP_204_NO_CONTENT)
def clear_ads_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = db.query(AdvertisingStrategy).filter(AdvertisingStrategy.user_id == current_user.id).all()
    for row in rows:
        db.delete(row)
    db.commit()
    return None
