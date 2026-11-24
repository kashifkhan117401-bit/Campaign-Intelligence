"""AI Content Generation Studio grounded in real video analysis & audience intelligence."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.ai.llm_provider import BaseLLMProvider, get_llm_provider

logger = logging.getLogger(__name__)

CONTENT_DISCLAIMER = (
    "Generated titles, keywords, and hashtags are AI-crafted creative suggestions informed by "
    "audience signals. Rankings, clicks, and trending performance are never guaranteed."
)


def generate_content_suite(
    *,
    tone: str,
    topic_brief: str,
    target_audience: str = "",
    custom_instructions: str = "",
    analysis_context: Optional[Dict[str, Any]] = None,
    provider: Optional[BaseLLMProvider] = None,
) -> Dict[str, Any]:
    llm = provider or get_llm_provider()
    if llm.is_available():
        try:
            return _llm_generate_content_suite(
                llm=llm,
                tone=tone,
                topic_brief=topic_brief,
                target_audience=target_audience,
                custom_instructions=custom_instructions,
                analysis_context=analysis_context,
            )
        except Exception as exc:
            logger.warning("LLM content generation fallback used: %s", exc)

    return _structured_fallback_content_suite(
        tone=tone,
        topic_brief=topic_brief,
        target_audience=target_audience,
        analysis_context=analysis_context,
    )


def _llm_generate_content_suite(
    *,
    llm: BaseLLMProvider,
    tone: str,
    topic_brief: str,
    target_audience: str,
    custom_instructions: str,
    analysis_context: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    ctx_lines = []
    if analysis_context:
        ctx_lines.append(f"Source video title: {analysis_context.get('video_title', '')}")
        ctx_lines.append(
            f"Sentiment: {analysis_context.get('positive_pct', 0)}% pos / "
            f"{analysis_context.get('negative_pct', 0)}% neg"
        )
        ctx_lines.append(f"Top keywords: {analysis_context.get('keywords', [])[:12]}")
        ctx_lines.append(f"Pain points: {analysis_context.get('pain_points', [])[:6]}")
        ctx_lines.append(f"Top audience questions: {analysis_context.get('top_questions', [])[:6]}")
        ctx_lines.append(f"Content gaps: {analysis_context.get('content_gaps', [])[:5]}")

    system_prompt = (
        "You are a senior YouTube growth strategist and scriptwriter. Generate a complete, "
        "production-ready content package strictly aligned with the requested tone and audience context. "
        "Never claim keywords or hashtags are guaranteed to rank or trend. "
        "Return JSON with exactly 4 top-level keys:\n"
        "1. 'youtube_content': {title_options: [5 strings], hooks: [3 strings], script: {introduction: str, "
        "main_sections: [{heading: str, talking_points: [str], script_body: str}], conclusion: str, call_to_action: str}}\n"
        "2. 'seo': {description: str, hashtags: [18 strings starting with #], tags: [15 strings], "
        "primary_keyword: str, secondary_keywords: [8 strings], search_intent: str, title_variations: [5 strings]}\n"
        "3. 'social_media': {youtube_shorts_scripts: [{title: str, hook: str, body: str, cta: str}], "
        "instagram_reels_captions: [2 strings], facebook_post: str, linkedin_post: str, x_post: str}\n"
        "4. 'content_strategy': {future_video_ideas: [10 objects with title, angle, target_pain_point], "
        "content_calendar: [4 objects with week, format, topic, goal], publishing_frequency: str, "
        "audience_recommendations: [5 strings]}"
    )
    user_prompt = (
        f"Tone: {tone}\n"
        f"Topic / Brief: {topic_brief}\n"
        f"Target Audience: {target_audience or 'Creators & digital marketers'}\n"
        f"Custom Instructions: {custom_instructions or 'None'}\n"
        f"<UNTRUSTED_USER_DATA>\n" + "\n".join(ctx_lines) + "\n</UNTRUSTED_USER_DATA>"
    )
    data = llm.generate_json(system_prompt, user_prompt, temperature=0.55, max_tokens=3800)

    fallback = _structured_fallback_content_suite(
        tone=tone,
        topic_brief=topic_brief,
        target_audience=target_audience,
        analysis_context=analysis_context,
    )
    return {
        "title": (
            (data.get("youtube_content", {}).get("title_options") or [fallback["title"]])[0]
            if isinstance(data.get("youtube_content"), dict)
            else fallback["title"]
        ),
        "youtube_content_json": data.get("youtube_content") or fallback["youtube_content_json"],
        "seo_json": data.get("seo") or fallback["seo_json"],
        "social_media_json": data.get("social_media") or fallback["social_media_json"],
        "content_strategy_json": data.get("content_strategy") or fallback["content_strategy_json"],
        "disclaimer": CONTENT_DISCLAIMER,
        "is_demo_data": False,
    }


def _structured_fallback_content_suite(
    *,
    tone: str,
    topic_brief: str,
    target_audience: str,
    analysis_context: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    ctx = analysis_context or {}
    base_topic = (topic_brief or ctx.get("video_title") or "YouTube Growth & Audience Strategy").strip()
    clean_topic = base_topic.replace("[DEMO DATA]", "").strip()
    keywords: List[str] = [str(k) for k in ctx.get("keywords", []) if k][:12]
    if not keywords:
        keywords = ["youtube strategy", "audience retention", "content workflow", "seo metadata", "creator growth"]
    primary_kw = keywords[0]
    pain_points: List[str] = [str(p) for p in ctx.get("pain_points", [])][:5] or [
        "Unclear step-by-step setup",
        "Low click-through rate on titles",
        "Pricing and ROI uncertainty",
    ]
    top_qs: List[str] = [str(q) for q in ctx.get("top_questions", [])][:5] or [
        f"How do beginners implement {clean_topic} quickly?",
        "What tools and budget are needed to get reliable results?",
        "How do you avoid the biggest retention drop-offs?",
    ]
    audience = target_audience or "YouTube creators, marketers, and growth teams"

    tone_openers = {
        "Professional": "Here is an evidence-backed framework built directly from viewer feedback:",
        "Educational": "Let's break this down step by step so you can apply every stage immediately:",
        "Conversational": "If you've ever paused a tutorial three times trying to figure out what actually works, this is for you:",
        "Persuasive": "Stop guessing what your viewers want—your comment section is already handing you the blueprint:",
        "Entertaining": "We read every single comment so you don't have to—and what viewers actually asked for surprised us:",
    }
    opener = tone_openers.get(tone, tone_openers["Professional"])

    title_options = [
        f"{clean_topic}: The Complete Audience-Backed Playbook",
        f"We Analyzed Real Viewer Feedback on {clean_topic} — Here's What Actually Works",
        f"Stop Making These 5 Mistakes in {clean_topic} ({tone} Guide)",
        f"{clean_topic} Explained Step-by-Step (Answering Your Top Questions)",
        f"How {audience.split(',')[0]} Can Master {clean_topic} Without Wasting Time",
    ]

    hooks = [
        f"{opener} Most creators miss the #1 pain point viewers keep bringing up: {pain_points[0]}. In the next 10 minutes, we solve it cleanly.",
        f"Look at the top question your audience keeps asking: '{top_qs[0]}' — let's answer it with a repeatable system you can use today.",
        f"Before you publish your next video on {primary_kw}, check these 3 audience objections that silently kill retention and conversions.",
    ]

    script = {
        "introduction": (
            f"{hooks[0]}\n\n"
            f"Welcome back! Today's walkthrough is crafted in a {tone.lower()} style specifically for {audience}. "
            f"We've structured chapters below so you can jump straight to setup, optimization, or Q&A."
        ),
        "main_sections": [
            {
                "heading": f"1. Diagnosing the Core Audience Pain Point ({pain_points[0]})",
                "talking_points": [
                    f"Why viewers struggle with {pain_points[0]}",
                    "Real comment signals showing where drop-offs happen",
                    "Quick diagnostic checklist before recording",
                ],
                "script_body": (
                    f"When we reviewed audience discussions around {clean_topic}, one pattern stood out immediately: "
                    f"viewers don't want vague theory—they want clear solutions for {pain_points[0]}. "
                    f"Start by writing down the single measurable result your viewer should achieve by minute 5."
                ),
            },
            {
                "heading": f"2. Step-by-Step Implementation for {primary_kw.title()}",
                "talking_points": [
                    "Cross-platform setup walkthrough (no skipped steps)",
                    "Templates and repeatability checklist",
                    "Live quality check before export",
                ],
                "script_body": (
                    f"Let's walk through the exact workflow at a clear pace. Step one: anchor your outline around "
                    f"'{top_qs[0]}'. Step two: tighten your first 30 seconds by stating the payoff visually on screen. "
                    f"Step three: add clear timestamps and an explicit resource summary in the description."
                ),
            },
            {
                "heading": "3. Overcoming Objections & Scaling Results",
                "talking_points": [
                    f"Addressing common questions: {top_qs[1] if len(top_qs) > 1 else 'budget & ROI'}",
                    "Testing title/thumbnail variations methodically",
                    "Turning long-form takeaways into Shorts & cross-platform posts",
                ],
                "script_body": (
                    "Many viewers ask whether this scales for smaller channels or solo teams. The key is keeping "
                    "your production loop lightweight: validate one audience question per video, track comment sentiment, "
                    "and iterate weekly rather than guessing."
                ),
            },
        ],
        "conclusion": (
            f"To recap: build around real audience questions, pace every technical walkthrough clearly, "
            f"and close each video with a concrete next step tailored to {audience}."
        ),
        "call_to_action": (
            "Drop your biggest bottleneck in the comments below—we read every question and turn the top requests "
            "into next week's deep-dive tutorial. Subscribe and grab the chapter checklist in the pinned comment."
        ),
    }

    hashtag_seeds = [
        primary_kw, *keywords[1:8], "YouTubeGrowth", "CreatorStrategy", "VideoMarketing",
        "ContentCreation", "YouTubeSEO", "AudienceIntelligence", "DigitalMarketing",
        "CreatorEconomy", "YouTubeTips", "VideoStrategy", "ContentMarketing",
    ]
    hashtags = []
    seen_tags = set()
    for h in hashtag_seeds:
        cleaned = "#" + "".join(ch for ch in h.title() if ch.isalnum())
        if len(cleaned) > 2 and cleaned.lower() not in seen_tags:
            seen_tags.add(cleaned.lower())
            hashtags.append(cleaned)
    hashtags = hashtags[:18]

    seo = {
        "description": (
            f"In this {tone.lower()} guide to {clean_topic}, we address the top questions and frustrations raised by "
            f"{audience}.\n\n"
            f"What you'll learn:\n"
            f"- 00:00 Why audience-driven content outperforms guesswork\n"
            f"- 01:30 Solving {pain_points[0]}\n"
            f"- 04:45 Complete step-by-step workflow for {primary_kw}\n"
            f"- 08:20 Answering top viewer questions & scaling across Shorts\n\n"
            f"Note: All strategies are illustrated as actionable best practices; actual channel metrics vary.\n\n"
            + " ".join(hashtags[:8])
        ),
        "hashtags": hashtags,
        "tags": list(dict.fromkeys([primary_kw, clean_topic[:60], *keywords, "youtube tutorial", "creator workflow", "video seo"]))[:15],
        "primary_keyword": primary_kw,
        "secondary_keywords": list(dict.fromkeys(keywords[1:9] + ["youtube audience analysis", "video script framework"]))[:8],
        "search_intent": "Informational & Commercial Investigation (viewers seeking practical setup guidance and tool/workflow comparisons)",
        "title_variations": [
            f"How to Fix {pain_points[0][:45]} in 10 Minutes",
            f"{primary_kw.title()} Tutorial for Beginners & Teams (2026)",
            f"The Honest Truth About {clean_topic[:55]}",
            f"7 Audience Questions About {primary_kw.title()} Answered",
            f"My Repeatable {clean_topic[:50]} System (Free Checklist)",
        ],
    }

    social_media = {
        "youtube_shorts_scripts": [
            {
                "title": f"Fix {pain_points[0][:40]} in 45 Seconds",
                "hook": f"Viewers keep complaining about {pain_points[0]}—here's the 3-step fix.",
                "body": f"Step 1: Front-load your main answer in 15 seconds. Step 2: Add clear chapter timestamps. Step 3: Pin a quick-start checklist directly answering '{top_qs[0][:70]}'.",
                "cta": "Full 10-minute walkthrough linked in the related video below!",
            },
            {
                "title": f"Top Question About {primary_kw.title()}",
                "hook": f"Everyone keeps asking: '{top_qs[0][:80]}'",
                "body": "Here's the short answer: start lean, validate with your comment section first, and optimize retention before spending on ads.",
                "cta": "Comment your niche and I'll reply with a tailored hook idea.",
            },
        ],
        "instagram_reels_captions": [
            f"We turned real viewer feedback on {clean_topic} into a repeatable 3-step system. Save this for your next shoot! {' '.join(hashtags[:5])}",
            f"Stop guessing your next content topic. Answer the #1 question your audience is already asking: {top_qs[0][:90]} 👇 {' '.join(hashtags[:5])}",
        ],
        "facebook_post": (
            f"New deep dive live! We analyzed real viewer questions around {clean_topic} and put together a clear, "
            f"no-fluff walkthrough covering {pain_points[0]} and step-by-step setup. Watch the full breakdown and tell us which chapter helped most!"
        ),
        "linkedin_post": (
            f"Most video marketing fails before the camera even turns on—because teams guess topics instead of listening to audience objections.\n\n"
            f"In our latest breakdown of {clean_topic}, three themes stood out from viewer conversations:\n"
            f"1. Clarity beats speed during technical demos\n"
            f"2. Viewers want transparent pricing & ROI expectations upfront\n"
            f"3. Chaptered, actionable walkthroughs drive deeper trust\n\n"
            f"How is your team turning audience comments into your next quarter's content roadmap?\n"
            + " ".join(hashtags[:4])
        ),
        "x_post": (
            f"Your comment section is your highest-ROI content strategist.\n\n"
            f"We broke down top viewer questions on {clean_topic[:60]} into a step-by-step playbook—zero fluff, full chapters. "
            f"{' '.join(hashtags[:3])}"
        ),
    }

    future_ideas = [
        {
            "title": f"Answering Your Top 5 Questions About {primary_kw.title()}",
            "angle": "Direct Q&A compilation addressing recurring comment threads",
            "target_pain_point": pain_points[0],
        },
        {
            "title": f"{clean_topic[:50]}: Beginner vs. Pro Workflow Compared",
            "angle": "Side-by-side comparison resolving mixed-skill audience feedback",
            "target_pain_point": "Pacing mismatch between beginners and advanced viewers",
        },
        {
            "title": "Complete Windows & macOS Setup Walkthrough (No Steps Skipped)",
            "angle": "Cross-platform troubleshooting guide",
            "target_pain_point": "Platform-specific setup frustration",
        },
        {
            "title": f"Is Paid Promotion Worth It for {primary_kw.title()}? Budget Breakdown",
            "angle": "Transparent cost-per-view & budget tier analysis",
            "target_pain_point": "Skepticism about YouTube Ads ROI for smaller channels",
        },
        {
            "title": "How to Turn 1 Long-Form Video into 7 High-Retention Shorts",
            "angle": "Repurposing playbook for busy creators",
            "target_pain_point": "Time constraints in multi-platform publishing",
        },
        {
            "title": "Free Template Walkthrough: Our Complete Pre-Publish Checklist",
            "angle": "Lead-magnet tutorial fulfilling viewer template requests",
            "target_pain_point": "Missing downloadable reference materials",
        },
        {
            "title": "Fixing the Top 3 Retention Drop-Offs in Tutorial Videos",
            "angle": "Analytics-backed hook & pacing clinic",
            "target_pain_point": "Viewers replaying confusing sections or dropping early",
        },
        {
            "title": "Budget Tools That Won't Crash on Older Laptops",
            "angle": "Accessible tool stack comparison",
            "target_pain_point": "Software crashes and steep pricing tiers",
        },
        {
            "title": "B2B vs. Creator Hooks: Writing Openings That Hold Attention",
            "angle": "Niche-specific hook workshop",
            "target_pain_point": "Adapting creator frameworks to business audiences",
        },
        {
            "title": "30-Day Channel Audit: Applying Audience Intelligence Live",
            "angle": "Case-study format showing before/after workflow upgrades",
            "target_pain_point": "Need for real-world proof and transparent methodology",
        },
    ]

    content_calendar = [
        {"week": "Week 1", "format": "Long-Form Deep Dive + 2 Shorts", "topic": title_options[0], "goal": "Capture core search intent & solve top pain point"},
        {"week": "Week 2", "format": "Q&A Tutorial + LinkedIn Carousel", "topic": future_ideas[0]["title"], "goal": "Build trust by directly answering viewer comments"},
        {"week": "Week 3", "format": "Comparison / Tool Stack + 2 Shorts", "topic": future_ideas[1]["title"], "goal": "Address buying objections & pricing clarity"},
        {"week": "Week 4", "format": "Case Study + Downloadable Checklist", "topic": future_ideas[5]["title"], "goal": "Drive email/lead capture & community engagement"},
    ]

    return {
        "title": title_options[0],
        "youtube_content_json": {
            "title_options": title_options,
            "hooks": hooks,
            "script": script,
        },
        "seo_json": seo,
        "social_media_json": social_media,
        "content_strategy_json": {
            "future_video_ideas": future_ideas,
            "content_calendar": content_calendar,
            "publishing_frequency": "1 high-depth long-form video (10-14 min) + 2-3 companion YouTube Shorts per week",
            "audience_recommendations": [
                f"Maintain a consistent {tone.lower()} voice tailored to {audience}",
                "Add timestamped chapters in every video description to reduce pacing frustration",
                "Pin a structured resource or FAQ comment within 5 minutes of publishing",
                "Review comment sentiment 72 hours post-upload to pick next week's follow-up topic",
                "Pair each tutorial with a concise visual checklist to capture high-intent leads",
            ],
        },
        "disclaimer": CONTENT_DISCLAIMER,
        "is_demo_data": True,
    }
