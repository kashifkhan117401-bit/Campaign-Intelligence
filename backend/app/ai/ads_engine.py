"""YouTube Advertising Strategy Planner & transparent 3-tier Budget Calculator."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.ai.llm_provider import BaseLLMProvider, get_llm_provider

logger = logging.getLogger(__name__)

# Configurable regional & objective benchmark multipliers (illustrative only)
COUNTRY_CPV_MULTIPLIER: Dict[str, float] = {
    "united states": 1.25,
    "usa": 1.25,
    "us": 1.25,
    "united kingdom": 1.15,
    "uk": 1.15,
    "canada": 1.15,
    "australia": 1.18,
    "germany": 1.10,
    "france": 1.02,
    "united arab emirates": 1.10,
    "singapore": 1.12,
    "india": 0.42,
    "pakistan": 0.35,
    "brazil": 0.52,
    "mexico": 0.58,
    "philippines": 0.45,
}

OBJECTIVE_PROFILES: Dict[str, Dict[str, Any]] = {
    "Brand awareness": {
        "campaign_type": "Video Reach Campaign (Skippable In-Stream + Bumper Ads, subject to Google Ads availability)",
        "cpv_mult": 0.90,
        "cpm_mult": 0.92,
        "ctr_mult": 0.85,
        "avg_frequency": 2.4,
    },
    "Reach": {
        "campaign_type": "Video Reach Campaign (Efficient Reach: Skippable In-Stream, Bumper & In-Feed)",
        "cpv_mult": 0.85,
        "cpm_mult": 0.85,
        "ctr_mult": 0.80,
        "avg_frequency": 2.1,
    },
    "Video views": {
        "campaign_type": "Video Views Campaign (Skippable In-Stream, In-Feed Video & Shorts Ads)",
        "cpv_mult": 1.00,
        "cpm_mult": 1.00,
        "ctr_mult": 1.00,
        "avg_frequency": 1.8,
    },
    "Website traffic": {
        "campaign_type": "Demand Gen / Video Action Campaign (In-Stream + YouTube Shorts + Feed)",
        "cpv_mult": 1.15,
        "cpm_mult": 1.12,
        "ctr_mult": 1.25,
        "avg_frequency": 2.0,
    },
    "Lead generation": {
        "campaign_type": "Demand Gen / Video Action with Lead Form Extensions (where available in Google Ads)",
        "cpv_mult": 1.25,
        "cpm_mult": 1.22,
        "ctr_mult": 1.30,
        "avg_frequency": 2.3,
    },
    "Product promotion": {
        "campaign_type": "Demand Gen / Video Action with Product Feed Integration",
        "cpv_mult": 1.20,
        "cpm_mult": 1.18,
        "ctr_mult": 1.28,
        "avg_frequency": 2.2,
    },
    "Conversions": {
        "campaign_type": "Demand Gen / Video Action (Maximize Conversions / Target CPA where eligible)",
        "cpv_mult": 1.35,
        "cpm_mult": 1.30,
        "ctr_mult": 1.35,
        "avg_frequency": 2.5,
    },
}

ILLUSTRATIVE_DISCLAIMER = (
    "ILLUSTRATIVE ESTIMATE ONLY: Live Google Ads auction forecasting is not connected. "
    "Impressions, views, clicks, reach, and CPV/CPM figures are calculated mathematically from "
    "configurable benchmark assumptions (Estimated Views = Campaign Budget / Assumed CPV) and "
    "are NOT guaranteed results."
)


def calculate_budget_tiers(
    *,
    available_budget: float,
    campaign_duration_days: int,
    currency: str,
    target_country: str,
    industry_niche: str,
    marketing_objective: str,
    base_cpv: float = 0.035,
    base_cpm: float = 8.50,
    base_ctr: float = 0.012,
) -> Dict[str, Any]:
    country_mult = COUNTRY_CPV_MULTIPLIER.get(target_country.strip().lower(), 0.95)
    profile = OBJECTIVE_PROFILES.get(marketing_objective, OBJECTIVE_PROFILES["Video views"])

    niche_low = industry_niche.lower()
    niche_mult = 1.20 if any(k in niche_low for k in ("saas", "finance", "b2b", "crypto", "legal", "real estate")) else (
        0.90 if any(k in niche_low for k in ("gaming", "entertainment", "music", "vlog")) else 1.0
    )

    assumed_cpv = round(max(0.005, base_cpv * country_mult * profile["cpv_mult"] * niche_mult), 4)
    assumed_cpm = round(max(1.0, base_cpm * country_mult * profile["cpm_mult"] * niche_mult), 2)
    assumed_ctr = round(min(0.15, max(0.002, base_ctr * profile["ctr_mult"])), 4)
    avg_freq = float(profile["avg_frequency"])

    tier_defs = [
        ("low", 0.60, "Conservative testing allocation (60% of available budget) to validate hooks & targeting."),
        ("balanced", 1.00, "Recommended baseline allocation (100% of available budget) balancing reach and learning speed."),
        ("aggressive", 1.60, "Accelerated scale scenario (160% of baseline budget) for faster creative testing and market share."),
    ]

    tiers: List[Dict[str, Any]] = []
    for tier_name, budget_mult, rationale in tier_defs:
        total_budget = round(available_budget * budget_mult, 2)
        daily_budget = round(total_budget / max(1, campaign_duration_days), 2)

        # Core explicit formulas
        estimated_views = int(round(total_budget / assumed_cpv))
        estimated_impressions = int(round((total_budget / assumed_cpm) * 1000.0))
        estimated_clicks = int(round(estimated_impressions * assumed_ctr))
        estimated_reach = int(round(estimated_impressions / avg_freq))

        tiers.append(
            {
                "tier": tier_name,
                "currency": currency.upper(),
                "campaign_duration_days": campaign_duration_days,
                "daily_budget": daily_budget,
                "total_budget": total_budget,
                "assumed_cpv": assumed_cpv,
                "assumed_cpm": assumed_cpm,
                "assumed_ctr": assumed_ctr,
                "estimated_impressions": estimated_impressions,
                "estimated_views": estimated_views,
                "estimated_clicks": estimated_clicks,
                "estimated_reach": estimated_reach,
                "assumptions_json": {
                    "rationale": rationale,
                    "country_multiplier": country_mult,
                    "niche_multiplier": niche_mult,
                    "objective_multiplier": profile["cpv_mult"],
                    "assumed_frequency": avg_freq,
                    "formulas": {
                        "estimated_views": "Campaign Budget / Assumed CPV",
                        "estimated_impressions": "(Campaign Budget / Assumed CPM) * 1000",
                        "estimated_clicks": "Estimated Impressions * Assumed CTR",
                        "estimated_reach": "Estimated Impressions / Assumed Avg Frequency",
                    },
                },
                "disclaimer": ILLUSTRATIVE_DISCLAIMER,
            }
        )

    return {
        "currency": currency.upper(),
        "campaign_duration_days": campaign_duration_days,
        "formula_note": (
            f"Estimated Views = Campaign Budget / Assumed CPV ({assumed_cpv} {currency.upper()}); "
            f"Estimated Impressions = (Budget / Assumed CPM {assumed_cpm}) * 1000; "
            f"Estimated Clicks = Impressions * Assumed CTR ({round(assumed_ctr * 100, 2)}%)."
        ),
        "is_illustrative_estimate": True,
        "disclaimer": ILLUSTRATIVE_DISCLAIMER,
        "tiers": tiers,
    }


def generate_ads_strategy(
    *,
    campaign_name: str,
    video_context: str,
    target_country: str,
    target_audience: str,
    industry_niche: str,
    marketing_objective: str,
    campaign_duration_days: int,
    available_budget: float,
    currency: str,
    base_cpv: float = 0.035,
    base_cpm: float = 8.50,
    base_ctr: float = 0.012,
    provider: Optional[BaseLLMProvider] = None,
) -> Dict[str, Any]:
    budget_calc = calculate_budget_tiers(
        available_budget=available_budget,
        campaign_duration_days=campaign_duration_days,
        currency=currency,
        target_country=target_country,
        industry_niche=industry_niche,
        marketing_objective=marketing_objective,
        base_cpv=base_cpv,
        base_cpm=base_cpm,
        base_ctr=base_ctr,
    )
    balanced = next((t for t in budget_calc["tiers"] if t["tier"] == "balanced"), budget_calc["tiers"][0])
    profile = OBJECTIVE_PROFILES.get(marketing_objective, OBJECTIVE_PROFILES["Video views"])

    llm = provider or get_llm_provider()
    if llm.is_available():
        try:
            return _llm_ads_strategy(
                llm=llm,
                campaign_name=campaign_name,
                video_context=video_context,
                target_country=target_country,
                target_audience=target_audience,
                industry_niche=industry_niche,
                marketing_objective=marketing_objective,
                campaign_duration_days=campaign_duration_days,
                available_budget=available_budget,
                currency=currency,
                balanced=balanced,
                budget_tiers=budget_calc["tiers"],
                default_campaign_type=profile["campaign_type"],
            )
        except Exception as exc:
            logger.warning("LLM ads strategy fallback used: %s", exc)

    return _fallback_ads_strategy(
        campaign_name=campaign_name,
        video_context=video_context,
        target_country=target_country,
        target_audience=target_audience,
        industry_niche=industry_niche,
        marketing_objective=marketing_objective,
        campaign_duration_days=campaign_duration_days,
        available_budget=available_budget,
        currency=currency,
        balanced=balanced,
        budget_tiers=budget_calc["tiers"],
        campaign_type=profile["campaign_type"],
    )


def _llm_ads_strategy(
    *,
    llm: BaseLLMProvider,
    campaign_name: str,
    video_context: str,
    target_country: str,
    target_audience: str,
    industry_niche: str,
    marketing_objective: str,
    campaign_duration_days: int,
    available_budget: float,
    currency: str,
    balanced: Dict[str, Any],
    budget_tiers: List[Dict[str, Any]],
    default_campaign_type: str,
) -> Dict[str, Any]:
    system_prompt = (
        "You are a senior Google & YouTube Ads media buyer. Produce a realistic, transparent "
        "YouTube advertising strategy. Never guarantee views, clicks, ROAS, or conversions. "
        "Note that campaign formats are subject to current Google Ads availability. "
        "Return JSON with keys: recommended_objective (str), audience_segments (list[str]), "
        "geographic_targeting ({primary_markets: [str], language_targeting: [str], bid_notes: str}), "
        "audience_interests (list[str]), campaign_type_and_format (str), placement_strategy (list[str]), "
        "creative_recommendations (list[str]), ab_testing_ideas (list[str]), "
        "optimization_strategy (list[str]), executive_report (str, 3-4 concise paragraphs)."
    )
    user_prompt = (
        f"Campaign: {campaign_name}\nObjective: {marketing_objective}\nCountry: {target_country}\n"
        f"Audience: {target_audience}\nIndustry/Niche: {industry_niche}\n"
        f"Duration: {campaign_duration_days} days\nBudget: {available_budget} {currency}\n"
        f"<UNTRUSTED_USER_DATA>\nVideo Context: {video_context[:1800]}\n</UNTRUSTED_USER_DATA>"
    )
    data = llm.generate_json(system_prompt, user_prompt, temperature=0.35, max_tokens=2400)
    fallback = _fallback_ads_strategy(
        campaign_name=campaign_name,
        video_context=video_context,
        target_country=target_country,
        target_audience=target_audience,
        industry_niche=industry_niche,
        marketing_objective=marketing_objective,
        campaign_duration_days=campaign_duration_days,
        available_budget=available_budget,
        currency=currency,
        balanced=balanced,
        budget_tiers=budget_tiers,
        campaign_type=default_campaign_type,
    )
    return {
        "recommended_objective": str(data.get("recommended_objective") or fallback["recommended_objective"]),
        "audience_segments_json": data.get("audience_segments") or fallback["audience_segments_json"],
        "geographic_targeting_json": data.get("geographic_targeting") or fallback["geographic_targeting_json"],
        "audience_interests_json": data.get("audience_interests") or fallback["audience_interests_json"],
        "campaign_type_and_format": str(data.get("campaign_type_and_format") or default_campaign_type),
        "placement_strategy_json": data.get("placement_strategy") or fallback["placement_strategy_json"],
        "suggested_daily_budget": balanced["daily_budget"],
        "suggested_total_budget": balanced["total_budget"],
        "creative_recommendations_json": data.get("creative_recommendations") or fallback["creative_recommendations_json"],
        "ab_testing_ideas_json": data.get("ab_testing_ideas") or fallback["ab_testing_ideas_json"],
        "optimization_strategy_json": data.get("optimization_strategy") or fallback["optimization_strategy_json"],
        "executive_report": str(data.get("executive_report") or fallback["executive_report"]),
        "disclaimer": ILLUSTRATIVE_DISCLAIMER,
        "is_demo_data": False,
        "budget_tiers": budget_tiers,
    }


def _fallback_ads_strategy(
    *,
    campaign_name: str,
    video_context: str,
    target_country: str,
    target_audience: str,
    industry_niche: str,
    marketing_objective: str,
    campaign_duration_days: int,
    available_budget: float,
    currency: str,
    balanced: Dict[str, Any],
    budget_tiers: List[Dict[str, Any]],
    campaign_type: str,
) -> Dict[str, Any]:
    return {
        "recommended_objective": f"{marketing_objective} — aligned with {campaign_type}",
        "audience_segments_json": [
            f"Custom Intent Segment: Users actively searching {industry_niche} tutorials & comparisons",
            f"In-Market Buyers: High-intent {target_audience} evaluating solutions",
            "Remarketing Pool: Engaged channel viewers (30-day video watchers & website visitors)",
            f"Lookalike / Optimized Targeting Expansion grounded in {industry_niche} converters",
        ],
        "geographic_targeting_json": {
            "primary_markets": [target_country],
            "language_targeting": ["English (adjust to local primary language as needed)"],
            "location_option": "Presence: People in or regularly in your targeted locations",
            "bid_notes": f"Start with national targeting in {target_country}, then segment top-performing metro regions after Day 7.",
        },
        "audience_interests_json": [
            f"{industry_niche} tools & software",
            "Creator economy & digital growth strategies",
            "How-to tutorials & product comparisons",
            f"Decision-makers within {target_audience}",
        ],
        "campaign_type_and_format": campaign_type,
        "placement_strategy_json": [
            "YouTube Watch Page (Skippable In-Stream Ads) for high-intent long-form viewers",
            "YouTube Home & Search In-Feed placements for active discovery",
            "YouTube Shorts vertical cutdowns (9:16, 15-30s) for efficient incremental reach",
            "Exclude irrelevant kids/gaming channels and mobile app interstitials to protect budget quality",
        ],
        "suggested_daily_budget": balanced["daily_budget"],
        "suggested_total_budget": balanced["total_budget"],
        "creative_recommendations_json": [
            "Deliver the core value proposition and pattern interrupt within the first 5 seconds before the Skip button appears",
            "Add burned-in bold captions so silent-autoplay mobile viewers immediately grasp the hook",
            f"Include a single clear CTA matched to '{marketing_objective}' with a matching landing page headline",
            "Prepare both 16:9 landscape (In-Stream/In-Feed) and 9:16 vertical (Shorts) edits of the top hook",
        ],
        "ab_testing_ideas_json": [
            "Hook Test: Pain-point question opener vs. measurable outcome opener (first 5 seconds)",
            "Format Test: 30-second punchy cut vs. 60-second mini-demo creative",
            "Audience Test: Custom Search Intent segment vs. Topic/Channel curated placement list",
            "CTA Overlay Test: 'Watch Free Guide' vs. 'Get the Checklist' companion banner",
        ],
        "optimization_strategy_json": [
            "Days 1-5 (Learning Phase): Avoid drastic daily budget changes (>20%) while Google Ads gathers view & click signals",
            "Day 7 Review: Pause creatives with <20% 30-second view rate or below-median CTR; reallocate spend to top 2 variations",
            "Day 14 Refinement: Exclude underperforming placements/devices and tighten geographic bids to top-converting regions",
            "Frequency Cap: Cap ad impressions at 3-4 per user per week to prevent creative fatigue",
        ],
        "executive_report": (
            f"Executive Advertising Brief — {campaign_name}\n\n"
            f"Campaign Alignment: For a {campaign_duration_days}-day {marketing_objective.lower()} initiative in "
            f"{target_country} targeting {target_audience} ({industry_niche}), we recommend running {campaign_type}. "
            f"Your balanced baseline budget of {balanced['total_budget']:,.2f} {currency.upper()} "
            f"({balanced['daily_budget']:,.2f} {currency.upper()}/day) supports structured creative testing while "
            f"allowing sufficient learning volume.\n\n"
            f"Illustrative Delivery Model: Under our disclosed benchmark assumptions (CPV {balanced['assumed_cpv']} "
            f"{currency.upper()}, CPM {balanced['assumed_cpm']} {currency.upper()}, CTR {round(balanced['assumed_ctr']*100, 2)}%), "
            f"the balanced tier illustrates approximately {balanced['estimated_views']:,} views, "
            f"{balanced['estimated_impressions']:,} impressions, and {balanced['estimated_clicks']:,} clicks. "
            f"These are illustrative planning calculations rather than live Google Ads forecasts.\n\n"
            f"Execution Focus: Anchor creative testing around the core video promise ({video_context[:180]}...), "
            f"exclude low-relevance placements early, and evaluate true CPA/CPV from live Google Ads reporting after week one."
        ),
        "disclaimer": ILLUSTRATIVE_DISCLAIMER,
        "is_demo_data": True,
        "budget_tiers": budget_tiers,
    }
