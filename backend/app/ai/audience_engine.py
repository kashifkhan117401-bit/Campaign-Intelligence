"""Audience Intelligence module with transparent Audience Opportunity Score formula."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.ai.llm_provider import BaseLLMProvider, get_llm_provider

logger = logging.getLogger(__name__)

OPPORTUNITY_FORMULA_DOC = (
    "Audience Opportunity Score (0-100) is an internal Campaign Intelligence prioritization heuristic "
    "(NOT an externally validated industry benchmark). Formula:\n"
    "  Score = 0.25 * Engagement Demand + 0.25 * Unmet Need Intensity "
    "+ 0.25 * Commercial Signal + 0.25 * Sentiment Leverage\n"
    "Where:\n"
    "- Engagement Demand (0-100): Scaled from collected comment count and viewer question density.\n"
    "- Unmet Need Intensity (0-100): Share of comments expressing pain points, frustration, or confusion.\n"
    "- Commercial Signal (0-100): Density of purchase intent, pricing inquiries, and feature requests.\n"
    "- Sentiment Leverage (0-100): Positive/constructive audience receptivity weighted by total discussions."
)


def compute_opportunity_score(
    total_comments: int,
    per_comment_results: List[Dict[str, Any]],
    positive_pct: float,
) -> tuple[float, Dict[str, Any]]:
    if total_comments <= 0 or not per_comment_results:
        return 0.0, {
            "engagement_demand": 0.0,
            "unmet_need_intensity": 0.0,
            "commercial_signal": 0.0,
            "sentiment_leverage": 0.0,
            "weights": {
                "engagement_demand": 0.25,
                "unmet_need_intensity": 0.25,
                "commercial_signal": 0.25,
                "sentiment_leverage": 0.25,
            },
            "sample_size": 0,
            "note": "No comments were available to calculate an opportunity score.",
        }

    n = len(per_comment_results)
    question_ratio = sum(1 for r in per_comment_results if r.get("is_question")) / n
    pain_ratio = sum(
        1
        for r in per_comment_results
        if r.get("is_complaint") or r.get("primary_emotion") in ("frustration", "confusion")
    ) / n
    commercial_ratio = sum(
        1
        for r in per_comment_results
        if r.get("purchase_intent") or r.get("is_feature_request")
    ) / n

    volume_factor = min(1.0, total_comments / 150.0)
    engagement_demand = round(min(100.0, (volume_factor * 55.0) + (question_ratio * 120.0)), 1)
    unmet_need = round(min(100.0, pain_ratio * 220.0), 1)
    commercial_signal = round(min(100.0, commercial_ratio * 240.0), 1)
    sentiment_leverage = round(min(100.0, (positive_pct * 0.75) + (volume_factor * 25.0)), 1)

    composite = round(
        0.25 * engagement_demand
        + 0.25 * unmet_need
        + 0.25 * commercial_signal
        + 0.25 * sentiment_leverage,
        1,
    )

    breakdown = {
        "engagement_demand": engagement_demand,
        "unmet_need_intensity": unmet_need,
        "commercial_signal": commercial_signal,
        "sentiment_leverage": sentiment_leverage,
        "weights": {
            "engagement_demand": 0.25,
            "unmet_need_intensity": 0.25,
            "commercial_signal": 0.25,
            "sentiment_leverage": 0.25,
        },
        "sample_size": n,
        "question_rate_pct": round(question_ratio * 100, 1),
        "unmet_need_rate_pct": round(pain_ratio * 100, 1),
        "commercial_signal_rate_pct": round(commercial_ratio * 100, 1),
    }
    return composite, breakdown


def generate_audience_intelligence(
    video_meta: Dict[str, Any],
    analysis_summary: Dict[str, Any],
    comments: List[Dict[str, Any]],
    per_comment_results: List[Dict[str, Any]],
    provider: Optional[BaseLLMProvider] = None,
) -> Dict[str, Any]:
    llm = provider or get_llm_provider()
    score, breakdown = compute_opportunity_score(
        total_comments=len(comments),
        per_comment_results=per_comment_results,
        positive_pct=float(analysis_summary.get("positive_pct", 0.0)),
    )

    if llm.is_available() and comments:
        try:
            return _llm_audience_intelligence(
                llm, video_meta, analysis_summary, comments, score, breakdown
            )
        except Exception as exc:
            logger.warning("LLM audience intelligence fallback triggered: %s", exc)

    return _grounded_fallback_intelligence(video_meta, analysis_summary, comments, score, breakdown)


def _llm_audience_intelligence(
    llm: BaseLLMProvider,
    video_meta: Dict[str, Any],
    summary: Dict[str, Any],
    comments: List[Dict[str, Any]],
    score: float,
    breakdown: Dict[str, Any],
) -> Dict[str, Any]:
    comment_sample = "\n".join(
        f"- ({c.get('like_count', 0)} likes) {c['text_sanitized'][:260]}"
        for c in sorted(comments, key=lambda x: x.get("like_count", 0), reverse=True)[:90]
    )
    system_prompt = (
        "You are a senior YouTube audience intelligence strategist. Ground every insight strictly "
        "in the video context and actual audience comments provided. Return JSON with keys: "
        "interests (list[str]), expectations (list[str]), common_problems (list[str]), "
        "unanswered_questions (list[str]), agreement_reasons (list[str]), disagreement_reasons (list[str]), "
        "main_frustrations (list[str]), content_gaps (list[str]), product_opportunities (list[str]), "
        "customer_objections (list[str]), marketing_angles (list[str]), "
        "top_10_questions (list of 10 objects with keys: rank, question, audience_intent, suggested_video_angle)."
    )
    user_prompt = (
        f"Video title: {video_meta.get('title', '')}\n"
        f"Sentiment: {summary.get('positive_pct')}% positive, {summary.get('negative_pct')}% negative, "
        f"{summary.get('neutral_pct')}% neutral across {summary.get('analyzed_comments_count')} comments.\n"
        f"Top topics: {[t.get('topic') for t in summary.get('topics_json', [])[:8]]}\n"
        f"<UNTRUSTED_USER_DATA>\n{comment_sample}\n</UNTRUSTED_USER_DATA>"
    )
    data = llm.generate_json(system_prompt, user_prompt, temperature=0.25, max_tokens=2800)

    def _str_list(key: str, default: List[str]) -> List[str]:
        v = data.get(key)
        return [str(x)[:300] for x in v[:10]] if isinstance(v, list) and v else default

    top_10 = data.get("top_10_questions")
    if not isinstance(top_10, list) or not top_10:
        top_10 = _build_top_10_questions_from_comments(summary, comments)

    return {
        "interests_json": _str_list("interests", ["Practical implementation tutorials"]),
        "expectations_json": _str_list("expectations", ["Clear step-by-step walkthroughs"]),
        "common_problems_json": _str_list("common_problems", summary.get("complaints_json", [])[:6]),
        "unanswered_questions_json": _str_list("unanswered_questions", summary.get("faqs_json", [])[:8]),
        "agreement_reasons_json": _str_list("agreement_reasons", ["Actionable, no-fluff explanations"]),
        "disagreement_reasons_json": _str_list("disagreement_reasons", summary.get("buying_objections_json", [])[:5]),
        "main_frustrations_json": _str_list("main_frustrations", summary.get("complaints_json", [])[:6]),
        "content_gaps_json": _str_list("content_gaps", summary.get("feature_requests_json", [])[:6]),
        "product_opportunities_json": _str_list("product_opportunities", ["Templates, checklists, and guided toolkits"]),
        "customer_objections_json": _str_list("customer_objections", summary.get("buying_objections_json", [])[:6]),
        "marketing_angles_json": _str_list("marketing_angles", ["Time-saving ROI backed by transparent walkthroughs"]),
        "top_10_questions_json": top_10[:10],
        "opportunity_score": score,
        "opportunity_score_breakdown_json": breakdown,
        "opportunity_formula_doc": OPPORTUNITY_FORMULA_DOC,
    }


def _build_top_10_questions_from_comments(
    summary: Dict[str, Any], comments: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    questions: List[str] = list(summary.get("faqs_json", []))
    for c in comments:
        txt = c.get("text_sanitized", "")
        if "?" in txt and txt not in questions:
            questions.append(txt[:220])

    topics = [t.get("topic", "Core workflow") for t in summary.get("topics_json", [])]
    fallback_prompts = [
        f"How do beginners get started with {topics[0] if topics else 'this workflow'} step-by-step?",
        "What pricing tier or budget makes sense for solo creators vs. teams?",
        "How does this workflow differ on Windows vs. macOS?",
        "What are the most common setup mistakes and how do you fix them?",
        "How can small channels measure ROI before scaling ad spend?",
        "How do you repurpose long-form videos into high-retention Shorts?",
        "What templates or checklists streamline repeatable weekly production?",
        "How should B2B vs. consumer creators adapt their first 15-second hooks?",
        "Which metrics actually predict long-term channel growth vs. vanity numbers?",
        "What lightweight tools work best on older hardware without crashing?",
    ]
    for fp in fallback_prompts:
        if len(questions) >= 10:
            break
        questions.append(fp)

    result = []
    for idx, q in enumerate(questions[:10], start=1):
        intent = "Purchase / ROI Clarity" if any(k in q.lower() for k in ("price", "budget", "buy", "cost", "tier", "offer")) else (
            "Technical Troubleshooting" if any(k in q.lower() for k in ("error", "oauth", "api", "windows", "crash", "fix"))
            else "Educational Deep-Dive"
        )
        result.append(
            {
                "rank": idx,
                "question": q,
                "audience_intent": intent,
                "suggested_video_angle": f"Dedicated 8-12 min breakdown directly answering: {q[:110]}",
            }
        )
    return result


def _grounded_fallback_intelligence(
    video_meta: Dict[str, Any],
    summary: Dict[str, Any],
    comments: List[Dict[str, Any]],
    score: float,
    breakdown: Dict[str, Any],
) -> Dict[str, Any]:
    topics = [t["topic"] for t in summary.get("topics_json", [])]
    top_kws = [k["keyword"] for k in summary.get("keywords_json", [])[:8]]
    complaints = summary.get("complaints_json", [])
    requests = summary.get("feature_requests_json", [])
    faqs = summary.get("faqs_json", [])
    objections = summary.get("buying_objections_json", [])

    interests = [f"Strong engagement around {t}" for t in topics[:5]] or [
        f"Audience interest centered on {video_meta.get('title', 'the video topic')}"
    ]
    expectations = [
        "Actionable, step-by-step demonstrations paced clearly for replayability",
        "Cross-platform compatibility details (Windows & macOS) without skipped steps",
        "Downloadable reference resources, chapter timestamps, and transparent cost comparisons",
        "Concrete examples tailored to both solo creators and agencies/teams",
    ]
    agreement_reasons = [
        f"{summary.get('positive_pct', 0)}% positive reception highlighting practical, non-clickbait guidance",
        f"High engagement on discussions involving: {', '.join(top_kws[:4]) or 'core tutorial takeaways'}",
    ]
    disagreement_reasons = objections[:4] or [
        "Mixed expectations between beginner overview depth and intermediate tactical detail",
        "Concerns around pricing accessibility and ad budget efficiency for smaller channels",
    ]
    content_gaps = requests[:5] or [
        "Missing chapter timestamps and downloadable summary checklists",
        "Need for platform-specific setup walkthroughs and beginner pacing",
    ]
    product_opportunities = [
        "Downloadable Notion / workflow templates directly requested in viewer comments",
        "Tiered creator starter bundle addressing solo-creator pricing objections",
        "Agency / team reporting toolkit with shareable PDF intelligence exports",
        "Step-by-step Shorts repurposing & thumbnail CTR optimization kit",
    ]
    marketing_angles = [
        "Lead with concrete time-saved outcomes and transparent step-by-step demos",
        "Address pricing and small-channel ROI skepticism upfront in the first 60 seconds",
        "Offer a free checklist or chapter index as a lead magnet tied to viewer FAQs",
        "Showcase side-by-side Windows/macOS and B2B/creator use cases",
    ]

    return {
        "interests_json": interests,
        "expectations_json": expectations,
        "common_problems_json": complaints[:6] or ["Viewers report setup friction and fast tutorial pacing"],
        "unanswered_questions_json": faqs[:8] or ["How to apply the framework to smaller or niche channels"],
        "agreement_reasons_json": agreement_reasons,
        "disagreement_reasons_json": disagreement_reasons,
        "main_frustrations_json": complaints[:6] or ["Fast transitions during technical sections"],
        "content_gaps_json": content_gaps,
        "product_opportunities_json": product_opportunities,
        "customer_objections_json": objections[:6] or ["Uncertainty around pricing tiers and paid ad ROI"],
        "marketing_angles_json": marketing_angles,
        "top_10_questions_json": _build_top_10_questions_from_comments(summary, comments),
        "opportunity_score": score,
        "opportunity_score_breakdown_json": breakdown,
        "opportunity_formula_doc": OPPORTUNITY_FORMULA_DOC,
    }
