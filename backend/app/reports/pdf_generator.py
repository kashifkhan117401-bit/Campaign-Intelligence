"""Professional multi-page ReportLab PDF generator for TubeMind AI (18 sections)."""
from __future__ import annotations

import html
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.shapes import Drawing, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

NAVY = colors.HexColor("#0B2A22")
INDIGO = colors.HexColor("#168A57")
PURPLE = colors.HexColor("#198754")
SLATE = colors.HexColor("#334155")
MUTED = colors.HexColor("#64748B")
LIGHT_BG = colors.HexColor("#F7F6F0")
BORDER = colors.HexColor("#CBD5E1")
GREEN = colors.HexColor("#168A57")
RED = colors.HexColor("#EF4444")
AMBER = colors.HexColor("#E9A22E")


def _esc(val: Any) -> str:
    return html.escape(str(val or "")).replace("\n", "<br/>")


def _build_styles():
    base = getSampleStyleSheet()
    return {
        "cover_brand": ParagraphStyle(
            "CoverBrand",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=12,
            textColor=INDIGO,
            spaceAfter=8,
        ),
        "cover_title": ParagraphStyle(
            "CoverTitle",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=24,
            leading=30,
            textColor=NAVY,
            alignment=0,
            spaceAfter=14,
        ),
        "cover_sub": ParagraphStyle(
            "CoverSub",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=11,
            leading=16,
            textColor=SLATE,
            spaceAfter=8,
        ),
        "h1": ParagraphStyle(
            "SectionH1",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            textColor=NAVY,
            spaceBefore=14,
            spaceAfter=6,
        ),
        "h2": ParagraphStyle(
            "SectionH2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=15,
            textColor=INDIGO,
            spaceBefore=10,
            spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "BodyTextTM",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=14,
            textColor=SLATE,
            spaceAfter=6,
        ),
        "bullet": ParagraphStyle(
            "BulletTM",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9.2,
            leading=13.5,
            leftIndent=14,
            textColor=SLATE,
            spaceAfter=3,
        ),
        "note": ParagraphStyle(
            "NoteTM",
            parent=base["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=8.5,
            leading=12,
            textColor=MUTED,
            spaceAfter=6,
        ),
    }


def _styled_table(data: List[List[Any]], col_widths: Optional[List[float]] = None) -> Table:
    tbl = Table(data, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 9),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 7),
                ("TOPPADDING", (0, 0), (-1, 0), 7),
                ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
                ("TEXTCOLOR", (0, 1), (-1, -1), SLATE),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -1), 8.5),
                ("TOPPADDING", (0, 1), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
                ("GRID", (0, 0), (-1, -1), 0.4, BORDER),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return tbl


def _sentiment_pie_chart(pos: float, neg: float, neu: float) -> Drawing:
    d = Drawing(440, 175)
    pie = Pie()
    pie.x = 130
    pie.y = 20
    pie.width = 130
    pie.height = 130
    values = [max(0.1, pos), max(0.1, neg), max(0.1, neu)]
    pie.data = values
    pie.labels = [f"Positive ({pos:.1f}%)", f"Negative ({neg:.1f}%)", f"Neutral ({neu:.1f}%)"]
    pie.slices[0].fillColor = GREEN
    pie.slices[1].fillColor = RED
    pie.slices[2].fillColor = AMBER
    pie.sideLabels = True
    d.add(pie)
    d.add(String(12, 160, "Sentiment Distribution Chart (AI-Classified Comments)", fontName="Helvetica-Bold", fontSize=10, fillColor=NAVY))
    return d


def _emotion_bar_chart(emotions: Dict[str, int]) -> Drawing:
    d = Drawing(450, 175)
    items = list(emotions.items())[:6] if emotions else [("satisfaction", 0)]
    labels = [k.title() for k, _ in items]
    counts = [int(v) for _, v in items]

    bc = VerticalBarChart()
    bc.x = 45
    bc.y = 32
    bc.height = 110
    bc.width = 380
    bc.data = [counts]
    bc.categoryAxis.categoryNames = labels
    bc.categoryAxis.labels.fontSize = 8
    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = max(5, max(counts) + 2)
    bc.bars[0].fillColor = INDIGO
    d.add(bc)
    d.add(String(12, 158, "Audience Emotion Distribution", fontName="Helvetica-Bold", fontSize=10, fillColor=NAVY))
    return d


def generate_intelligence_pdf(
    *,
    output_path: str,
    report_title: str,
    video: Dict[str, Any],
    analysis: Dict[str, Any],
    insight: Optional[Dict[str, Any]] = None,
    content: Optional[Dict[str, Any]] = None,
    strategy: Optional[Dict[str, Any]] = None,
    budget_tiers: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[int, int]:
    """Build the 18-section TubeMind AI PDF report and return (file_size_bytes, page_count)."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    styles = _build_styles()
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    page_counter = {"count": 0}

    def _on_page(canvas, doc):
        page_counter["count"] = max(page_counter["count"], doc.page)
        canvas.saveState()
        w, h = letter
        # Top accent strip
        canvas.setFillColor(INDIGO)
        canvas.rect(0, h - 10, w, 10, fill=1, stroke=0)
        if doc.page > 1:
            canvas.setFont("Helvetica-Bold", 8)
            canvas.setFillColor(NAVY)
            canvas.drawString(0.75 * inch, h - 30, "CAMPAIGN INTELLIGENCE  |  AUDIENCE & MARKETING INTELLIGENCE REPORT")
            canvas.setStrokeColor(BORDER)
            canvas.line(0.75 * inch, h - 36, w - 0.75 * inch, h - 36)
        # Footer
        canvas.setStrokeColor(BORDER)
        canvas.line(0.75 * inch, 0.65 * inch, w - 0.75 * inch, 0.65 * inch)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(MUTED)
        canvas.drawString(0.75 * inch, 0.48 * inch, f"© {datetime.now(timezone.utc).year} Kashif Hafeez. All rights reserved.  |  Generated {generated_at}")
        canvas.drawRightString(w - 0.75 * inch, 0.48 * inch, f"Page {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.85 * inch,
        title=report_title,
        author="Campaign Intelligence",
    )

    story: List[Any] = []

    # --- 1. COVER PAGE ---
    story.append(Spacer(1, 0.9 * inch))
    story.append(Paragraph("CAMPAIGN INTELLIGENCE  //  KNOW PAKISTAN'S AUDIENCE BEFORE YOU SPEND A RUPEE", styles["cover_brand"]))
    story.append(Paragraph(_esc(report_title), styles["cover_title"]))
    story.append(
        Paragraph(
            f"Comprehensive YouTube Sentiment, Audience Intelligence, SEO Content &amp; Advertising Strategy Report",
            styles["cover_sub"],
        )
    )
    story.append(Spacer(1, 0.25 * inch))

    is_demo = bool(analysis.get("is_demo_data") or video.get("is_demo_data"))
    if is_demo:
        story.append(
            Paragraph(
                "<b>DEVELOPMENT DEMO DATA NOTICE:</b> This report includes visibly labeled demo data because "
                "external API credentials were not configured during generation.",
                styles["note"],
            )
        )

    cover_meta = [
        ["Field", "Details"],
        ["Target Video", Paragraph(_esc(video.get("title", "N/A")), styles["body"])],
        ["YouTube URL", Paragraph(_esc(video.get("url", "N/A")), styles["body"])],
        ["Channel", _esc(video.get("channel_title", "N/A"))],
        ["Report Generated", generated_at],
        ["Comments Analyzed", str(analysis.get("analyzed_comments_count", 0))],
        ["Positive / Negative / Neutral", f"{analysis.get('positive_pct', 0)}% / {analysis.get('negative_pct', 0)}% / {analysis.get('neutral_pct', 0)}%"],
    ]
    story.append(_styled_table(cover_meta, col_widths=[1.8 * inch, 5.2 * inch]))
    story.append(Spacer(1, 0.4 * inch))
    story.append(
        Paragraph(
            "Confidential Strategy Brief prepared by Campaign Intelligence (© Kashif Hafeez. All rights reserved.). "
            "Sentiment classifications are AI-generated and advertising projections represent illustrative benchmark estimates.",
            styles["note"],
        )
    )
    story.append(PageBreak())

    # --- 2. VIDEO INFORMATION ---
    story.append(Paragraph("2. Video Information", styles["h1"]))
    vid_table = [
        ["Metric", "Value", "Metric", "Value"],
        ["Video ID", _esc(video.get("youtube_video_id")), "Views", f"{int(video.get('view_count', 0)):,}"],
        ["Channel", _esc(video.get("channel_title")), "Likes", f"{int(video.get('like_count', 0)):,}"],
        ["Duration", _esc(video.get("duration_iso") or "N/A"), "Total Comments (API)", f"{int(video.get('comment_count', 0)):,}"],
        ["Comments Disabled", "Yes" if video.get("comments_disabled") else "No", "Collected Sample", str(analysis.get("collected_comments_count", 0))],
    ]
    story.append(_styled_table(vid_table, col_widths=[1.4 * inch, 2.1 * inch, 1.5 * inch, 2.0 * inch]))

    # --- 3. EXECUTIVE SUMMARY ---
    story.append(Paragraph("3. Executive Summary", styles["h1"]))
    top_topic = (analysis.get("topics_json") or [{}])[0].get("topic", "core video themes")
    opp_score = insight.get("opportunity_score", 0.0) if insight else 0.0
    story.append(
        Paragraph(
            f"Campaign Intelligence analyzed <b>{analysis.get('analyzed_comments_count', 0)}</b> collected top-level comments "
            f"on <b>{_esc(video.get('title'))}</b>. Overall audience sentiment measured "
            f"<b>{analysis.get('positive_pct', 0)}% Positive</b>, <b>{analysis.get('negative_pct', 0)}% Negative</b>, "
            f"and <b>{analysis.get('neutral_pct', 0)}% Neutral</b>. The dominant theme discussed by viewers was "
            f"<b>{_esc(top_topic)}</b>, yielding an internal Audience Opportunity Score of <b>{opp_score}/100</b>.",
            styles["body"],
        )
    )

    # --- 4. COMMENT COLLECTION METHODOLOGY ---
    story.append(Paragraph("4. Comment Collection Methodology", styles["h1"]))
    story.append(
        Paragraph(
            f"Public top-level comments were retrieved via YouTube Data API v3 pagination (capped at "
            f"{analysis.get('requested_max_comments', 500)} requested / up to 2,000 max accessible comments), "
            f"sanitized as untrusted user-generated text to prevent prompt injection, and evaluated in structured batches. "
            f"Collected comments: <b>{analysis.get('collected_comments_count', 0)}</b>; analyzed: "
            f"<b>{analysis.get('analyzed_comments_count', 0)}</b>. No synthetic comments were added in live mode.",
            styles["body"],
        )
    )

    # --- 5. SENTIMENT ANALYSIS ---
    story.append(Paragraph("5. Sentiment Analysis", styles["h1"]))
    sent_rows = [
        ["Category", "Comment Count", "Share (%)"],
        ["Positive", str(analysis.get("positive_count", 0)), f"{analysis.get('positive_pct', 0):.2f}%"],
        ["Negative", str(analysis.get("negative_count", 0)), f"{analysis.get('negative_pct', 0):.2f}%"],
        ["Neutral", str(analysis.get("neutral_count", 0)), f"{analysis.get('neutral_pct', 0):.2f}%"],
        ["Total Analyzed", str(analysis.get("analyzed_comments_count", 0)), "100.00%"],
    ]
    story.append(_styled_table(sent_rows, col_widths=[2.4 * inch, 2.3 * inch, 2.3 * inch]))
    story.append(Paragraph(_esc(analysis.get("ai_disclaimer")), styles["note"]))

    # --- 6. SENTIMENT DISTRIBUTION CHARTS ---
    story.append(Paragraph("6. Sentiment Distribution Charts", styles["h1"]))
    story.append(
        _sentiment_pie_chart(
            float(analysis.get("positive_pct", 0)),
            float(analysis.get("negative_pct", 0)),
            float(analysis.get("neutral_pct", 0)),
        )
    )

    # --- 7. AUDIENCE EMOTIONS ---
    story.append(Paragraph("7. Audience Emotions", styles["h1"]))
    emotions = analysis.get("emotion_distribution_json") or {}
    story.append(_emotion_bar_chart(emotions))
    if emotions:
        emo_rows = [["Emotion", "Comment Count"]] + [
            [k.title(), str(v)] for k, v in sorted(emotions.items(), key=lambda kv: kv[1], reverse=True)
        ]
        story.append(_styled_table(emo_rows, col_widths=[3.5 * inch, 3.5 * inch]))

    # --- 8. MAIN AUDIENCE PAIN POINTS ---
    story.append(Paragraph("8. Main Audience Pain Points", styles["h1"]))
    pains = analysis.get("pain_points_json") or []
    if pains:
        pain_rows = [["Pain Point / Friction Area", "Mentions", "Severity Index"]] + [
            [_esc(p.get("pain_point")), str(p.get("mentions", 0)), f"{p.get('severity_score', 0)}/100"]
            for p in pains[:8]
        ]
        story.append(_styled_table(pain_rows, col_widths=[4.2 * inch, 1.4 * inch, 1.4 * inch]))
    else:
        story.append(Paragraph("No concentrated negative pain points were detected in the analyzed sample.", styles["body"]))

    # --- 9. FREQUENTLY ASKED QUESTIONS ---
    story.append(Paragraph("9. Frequently Asked Questions", styles["h1"]))
    faqs = analysis.get("faqs_json") or []
    for q in faqs[:8]:
        story.append(Paragraph(f"&bull; {_esc(q)}", styles["bullet"]))
    if not faqs:
        story.append(Paragraph("No recurring viewer questions were found in the collected sample.", styles["body"]))

    # --- 10. KEYWORD ANALYSIS ---
    story.append(Paragraph("10. Keyword Analysis", styles["h1"]))
    kws = analysis.get("keywords_json") or []
    if kws:
        kw_rows = [["Keyword", "Frequency", "Keyword", "Frequency"]]
        half = (min(len(kws), 16) + 1) // 2
        for i in range(half):
            left = kws[i]
            right = kws[i + half] if i + half < len(kws) else {"keyword": "-", "count": "-"}
            kw_rows.append([_esc(left["keyword"]), str(left["count"]), _esc(right["keyword"]), str(right["count"])])
        story.append(_styled_table(kw_rows, col_widths=[2.3 * inch, 1.2 * inch, 2.3 * inch, 1.2 * inch]))
    else:
        story.append(Paragraph("No high-frequency keywords extracted.", styles["body"]))

    story.append(PageBreak())

    # --- 11. AUDIENCE INTELLIGENCE ---
    story.append(Paragraph("11. Audience Intelligence", styles["h1"]))
    if insight:
        story.append(
            Paragraph(
                f"<b>Audience Opportunity Score: {insight.get('opportunity_score', 0)}/100</b> "
                f"(Internal transparent scoring heuristic — see Section 18 for formula).",
                styles["body"],
            )
        )
        for label, key in (
            ("Audience Interests", "interests_json"),
            ("Content Gaps", "content_gaps_json"),
            ("Product / Service Opportunities", "product_opportunities_json"),
            ("Customer Objections", "customer_objections_json"),
            ("Recommended Marketing Angles", "marketing_angles_json"),
        ):
            items = insight.get(key) or []
            if items:
                story.append(Paragraph(label, styles["h2"]))
                for it in items[:5]:
                    story.append(Paragraph(f"&bull; {_esc(it)}", styles["bullet"]))
    else:
        story.append(Paragraph("Audience intelligence synthesis has not been generated for this analysis.", styles["body"]))

    # --- 12, 13, 14, 15: CONTENT, SEO, HASHTAGS, FUTURE IDEAS ---
    yt_c = (content or {}).get("youtube_content_json") or {}
    seo_c = (content or {}).get("seo_json") or {}
    strat_c = (content or {}).get("content_strategy_json") or {}

    story.append(Paragraph("12. Recommended Video Content", styles["h1"]))
    if yt_c:
        story.append(Paragraph("Attention-Grabbing Hooks", styles["h2"]))
        for h in (yt_c.get("hooks") or [])[:3]:
            story.append(Paragraph(f"&bull; {_esc(h)}", styles["bullet"]))
        script = yt_c.get("script") or {}
        if script.get("introduction"):
            story.append(Paragraph("Script Introduction", styles["h2"]))
            story.append(Paragraph(_esc(script["introduction"]), styles["body"]))
        if script.get("call_to_action"):
            story.append(Paragraph("Call to Action", styles["h2"]))
            story.append(Paragraph(_esc(script["call_to_action"]), styles["body"]))
    else:
        story.append(Paragraph("Generate a content pack in AI Content Studio to attach full scripts and hooks to this report.", styles["body"]))

    story.append(Paragraph("13. SEO Titles and Descriptions", styles["h1"]))
    if yt_c.get("title_options") or seo_c.get("description"):
        for t in (yt_c.get("title_options") or [])[:5]:
            story.append(Paragraph(f"&bull; {_esc(t)}", styles["bullet"]))
        if seo_c.get("description"):
            story.append(Paragraph("SEO-Optimized Description", styles["h2"]))
            story.append(Paragraph(_esc(seo_c["description"][:1400]), styles["body"]))
    else:
        story.append(Paragraph("No SEO content pack attached yet.", styles["body"]))

    story.append(Paragraph("14. Hashtag Recommendations", styles["h1"]))
    hashtags = seo_c.get("hashtags") or []
    if hashtags:
        story.append(Paragraph(_esc("  ".join(hashtags[:25])), styles["body"]))
        story.append(Paragraph("Note: Hashtags are relevance-based suggestions and are not guaranteed to trend or rank.", styles["note"]))
    else:
        story.append(Paragraph("Generate an SEO pack in AI Content Studio to populate recommended hashtags.", styles["body"]))

    story.append(Paragraph("15. Future Content Ideas", styles["h1"]))
    ideas = strat_c.get("future_video_ideas") or []
    if ideas:
        idea_rows = [["#", "Video Idea", "Strategic Angle"]] + [
            [str(i), Paragraph(_esc(it.get("title")), styles["body"]), Paragraph(_esc(it.get("angle")), styles["body"])]
            for i, it in enumerate(ideas[:10], start=1)
        ]
        story.append(_styled_table(idea_rows, col_widths=[0.4 * inch, 3.1 * inch, 3.5 * inch]))
    elif insight and insight.get("top_10_questions_json"):
        for q in insight["top_10_questions_json"][:10]:
            story.append(Paragraph(f"&bull; {_esc(q.get('question'))}", styles["bullet"]))
    else:
        story.append(Paragraph("No future content roadmap attached.", styles["body"]))

    story.append(PageBreak())

    # --- 16. YOUTUBE ADVERTISING STRATEGY ---
    story.append(Paragraph("16. YouTube Advertising Strategy", styles["h1"]))
    if strategy:
        story.append(Paragraph(f"<b>Campaign:</b> {_esc(strategy.get('campaign_name'))} ({_esc(strategy.get('marketing_objective'))})", styles["body"]))
        story.append(Paragraph(f"<b>Recommended Format:</b> {_esc(strategy.get('campaign_type_and_format'))}", styles["body"]))
        story.append(Paragraph(f"<b>Target Market &amp; Audience:</b> {_esc(strategy.get('target_country'))} — {_esc(strategy.get('target_audience'))}", styles["body"]))
        if strategy.get("executive_report"):
            story.append(Paragraph(_esc(strategy["executive_report"]), styles["body"]))
        for label, key in (
            ("Audience Segments", "audience_segments_json"),
            ("Creative Recommendations", "creative_recommendations_json"),
            ("A/B Testing Ideas", "ab_testing_ideas_json"),
        ):
            arr = strategy.get(key) or []
            if arr:
                story.append(Paragraph(label, styles["h2"]))
                for item in arr[:4]:
                    story.append(Paragraph(f"&bull; {_esc(item)}", styles["bullet"]))
    else:
        story.append(Paragraph("Create an Ads Strategy in the Ads Strategy Planner to include campaign targeting recommendations.", styles["body"]))

    # --- 17. ADVERTISING BUDGET RECOMMENDATIONS ---
    story.append(Paragraph("17. Advertising Budget Recommendations", styles["h1"]))
    tiers = budget_tiers or []
    if tiers:
        b_rows = [["Tier", "Daily Budget", "Total Budget", "Assumed CPV", "Est. Views", "Est. Impressions", "Est. Clicks"]]
        for t in tiers:
            cur = t.get("currency", "USD")
            b_rows.append(
                [
                    str(t.get("tier", "")).title(),
                    f"{t.get('daily_budget', 0):,.2f} {cur}",
                    f"{t.get('total_budget', 0):,.2f} {cur}",
                    f"{t.get('assumed_cpv', 0):.4f}",
                    f"{int(t.get('estimated_views', 0)):,}",
                    f"{int(t.get('estimated_impressions', 0)):,}",
                    f"{int(t.get('estimated_clicks', 0)):,}",
                ]
            )
        story.append(_styled_table(b_rows, col_widths=[0.8 * inch, 1.1 * inch, 1.1 * inch, 0.95 * inch, 1.0 * inch, 1.1 * inch, 0.95 * inch]))
        story.append(
            Paragraph(
                "Illustrative benchmark estimates (Estimated Views = Campaign Budget / Assumed CPV). "
                "Actual YouTube Ads performance varies by auction competition and creative quality.",
                styles["note"],
            )
        )
    else:
        story.append(Paragraph("No budget tier calculation attached.", styles["body"]))

    # --- 18. ASSUMPTIONS AND LIMITATIONS ---
    story.append(Paragraph("18. Assumptions and Limitations", styles["h1"]))
    limitations = [
        "AI Sentiment & Emotion Classification: Automated classifications from public comments may misinterpret sarcasm, cultural slang, or nuanced context.",
        "Audience Opportunity Score: An internal weighted heuristic (25% Engagement Demand, 25% Unmet Need Intensity, 25% Commercial Signal, 25% Sentiment Leverage) — not an externally validated benchmark.",
        "SEO & Content Suggestions: Generated titles, keywords, and hashtags are creative recommendations and never guarantee YouTube search rankings or trending placement.",
        "Advertising Estimates: Where live Google Ads forecasting is not connected, all impression, view, reach, and click numbers are illustrative estimates derived from disclosed benchmark assumptions.",
        "Data Scope: Comment collection reflects accessible top-level public comments retrieved via YouTube Data API v3 at the time of analysis (up to 2,000 comments).",
    ]
    for lim in limitations:
        story.append(Paragraph(f"&bull; {_esc(lim)}", styles["bullet"]))

    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
    file_size = Path(output_path).stat().st_size if Path(output_path).exists() else 0
    return file_size, max(1, page_counter["count"])
