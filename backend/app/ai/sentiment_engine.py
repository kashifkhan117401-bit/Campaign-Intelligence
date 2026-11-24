"""Batch YouTube comment sentiment, emotion, topic, keyword, and pain-point analyzer."""
from __future__ import annotations

import logging
import re
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

from app.ai.llm_provider import BaseLLMProvider, get_llm_provider
from app.core.config import get_settings

logger = logging.getLogger(__name__)

STOPWORDS = {
    "the", "and", "for", "that", "this", "with", "you", "your", "are", "was", "were",
    "have", "has", "had", "not", "but", "what", "when", "where", "who", "why", "how",
    "can", "could", "would", "should", "will", "just", "like", "very", "more", "most",
    "about", "from", "they", "them", "their", "there", "here", "been", "being", "into",
    "out", "all", "any", "some", "too", "than", "then", "also", "really", "actually",
    "video", "videos", "youtube", "watch", "watching", "watched", "channel", "please",
    "thanks", "thank", "much", "good", "great", "really", "make", "made", "still",
    "only", "well", "does", "did", "done", "dont", "cant", "wont", "its", "im", "ive",
}

POSITIVE_LEXICON = {
    "love", "loved", "amazing", "awesome", "helpful", "best", "saved", "clear", "honest",
    "trustworthy", "subscribed", "doubled", "improved", "excited", "practical", "brilliant",
    "fantastic", "excellent", "perfect", "recommend", "thank", "thanks", "valuable",
    "insane", "gamechanger", "solid", "incredible", "useful", "worth", "appreciate",
}

NEGATIVE_LEXICON = {
    "frustrated", "annoying", "confusing", "confused", "crashing", "crash", "skipped",
    "skeptical", "steep", "expensive", "bad", "worst", "terrible", "waste", "useless",
    "broken", "slow", "fast", "error", "errors", "problem", "issue", "fail", "failed",
    "hate", "disappointed", "misleading", "clickbait", "hard", "difficult", "bug",
}

EMOTION_KEYWORDS = {
    "frustration": {"frustrated", "annoying", "crashing", "skipped", "broken", "error", "errors", "hate", "stuck", "waste"},
    "confusion": {"confusing", "confused", "replay", "understand", "unclear", "lost", "explain", "how do"},
    "excitement": {"excited", "amazing", "awesome", "subscribed", "doubled", "gamechanger", "cant wait", "super"},
    "trust": {"honest", "trustworthy", "clear", "transparent", "practical", "reliable", "authentic"},
    "satisfaction": {"saved", "helpful", "best", "improved", "great", "solid", "valuable", "love", "loved"},
}

PURCHASE_INTENT_MARKERS = (
    "where can i buy", "take my money", "pricing", "price", "free tier", "discount",
    "team seats", "agency", "cost", "worth buying", "link to buy", "subscribe", "plan",
    "enterprise", "white-label", "budget",
)

FEATURE_REQUEST_MARKERS = (
    "please add", "would love", "can you do", "could you add", "follow-up", "deep dive",
    "downloadable", "checklist", "timestamps", "do you offer", "wish it had", "support for",
)

COMPLAINT_MARKERS = (
    "frustrated", "annoying", "skipped", "too fast", "keeps crashing", "steep",
    "broken", "throws", "permission errors", "failed", "disappointed",
)

OBJECTION_MARKERS = (
    "skeptical", "steep", "expensive", "too much", "not sure", "worth it",
    "small channels", "only for", "mac-only", "pricing", "free tier",
)


def _tokenize_keywords(text: str) -> List[str]:
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9-]{2,}", text.lower())
    return [t for t in tokens if t not in STOPWORDS and len(t) <= 28]


def _heuristic_classify_comment(comment: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministic NLP classifier grounded purely in the comment text itself."""
    text = comment.get("text_sanitized") or comment.get("text_original") or ""
    low = text.lower()
    words = set(re.findall(r"[a-zA-Z0-9'-]+", low))

    pos_hits = len(words & POSITIVE_LEXICON)
    neg_hits = len(words & NEGATIVE_LEXICON)
    has_question = "?" in text or bool(re.search(r"\b(how|why|what|where|does|can you|is there)\b", low))

    if pos_hits > neg_hits:
        sentiment = "positive"
        confidence = min(0.92, 0.68 + 0.08 * (pos_hits - neg_hits))
    elif neg_hits > pos_hits:
        sentiment = "negative"
        confidence = min(0.92, 0.68 + 0.08 * (neg_hits - pos_hits))
    else:
        sentiment = "neutral"
        confidence = 0.65

    emotion_scores = {
        emo: sum(1 for kw in kws if kw in low)
        for emo, kws in EMOTION_KEYWORDS.items()
    }
    best_emotion = max(emotion_scores, key=lambda k: emotion_scores[k])
    if emotion_scores[best_emotion] == 0:
        if sentiment == "positive":
            best_emotion = "satisfaction"
        elif sentiment == "negative":
            best_emotion = "frustration"
        elif has_question:
            best_emotion = "confusion"
        else:
            best_emotion = "trust"

    secondary = [e for e, sc in emotion_scores.items() if sc > 0 and e != best_emotion][:2]

    purchase_intent = any(m in low for m in PURCHASE_INTENT_MARKERS)
    is_feature_request = any(m in low for m in FEATURE_REQUEST_MARKERS)
    is_complaint = any(m in low for m in COMPLAINT_MARKERS) or (sentiment == "negative" and neg_hits >= 2)

    keywords = _tokenize_keywords(text)[:6]
    topics = _infer_topics_from_text(low)

    return {
        "youtube_comment_id": comment["youtube_comment_id"],
        "sentiment": sentiment,
        "confidence": round(confidence, 3),
        "primary_emotion": best_emotion,
        "secondary_emotions": secondary,
        "purchase_intent": purchase_intent,
        "is_complaint": is_complaint,
        "is_feature_request": is_feature_request,
        "is_question": has_question,
        "topics": topics,
        "keywords": keywords,
    }


def _infer_topics_from_text(low: str) -> List[str]:
    topic_map = {
        "Pricing & Value": ("price", "pricing", "cost", "free tier", "discount", "steep", "budget", "buy"),
        "Tutorials & Pacing": ("tutorial", "pacing", "too fast", "replay", "timestamps", "checklist", "step"),
        "YouTube SEO & Growth": ("seo", "ctr", "thumbnail", "titles", "chapters", "impressions", "retention", "hook"),
        "Workflow & Tools": ("workflow", "template", "notion", "editing", "export", "4k", "software", "crashing"),
        "Ads & Monetization": ("ads", "budget", "convert", "promote", "monetiz", "roi", "agency", "b2b"),
        "API & Technical Setup": ("oauth", "api", "analytics", "windows", "mac", "permission", "setup"),
        "Short-Form Content": ("shorts", "reels", "tiktok", "long-form", "faceless"),
    }
    found = [label for label, cues in topic_map.items() if any(c in low for c in cues)]
    return found[:3] if found else ["General Video Feedback"]


def _cluster_topics_with_embeddings(
    provider: BaseLLMProvider, comments: List[Dict[str, Any]]
) -> List[str]:
    """Use embeddings to surface emerging cluster themes when an LLM provider is configured."""
    if not provider.is_available() or len(comments) < 8:
        return []
    sample = comments[:80]
    texts = [c["text_sanitized"] for c in sample]
    vecs = provider.embed_texts(texts)
    if not vecs or len(vecs) != len(sample):
        return []

    mat = np.array(vecs, dtype=np.float32)
    norms = np.linalg.norm(mat, axis=1, keepdims=True) + 1e-8
    mat = mat / norms

    k = min(5, max(2, len(sample) // 12))
    rng = np.random.default_rng(42)
    centroids = mat[rng.choice(len(mat), size=k, replace=False)]
    labels = np.zeros(len(mat), dtype=int)
    for _ in range(8):
        sims = mat @ centroids.T
        labels = np.argmax(sims, axis=1)
        for idx in range(k):
            members = mat[labels == idx]
            if len(members) > 0:
                c = members.mean(axis=0)
                centroids[idx] = c / (np.linalg.norm(c) + 1e-8)

    emerging: List[str] = []
    for idx in range(k):
        member_indices = np.where(labels == idx)[0]
        if len(member_indices) < 2:
            continue
        kw_counter: Counter[str] = Counter()
        for mi in member_indices:
            kw_counter.update(_tokenize_keywords(texts[mi]))
        top_terms = [w for w, _ in kw_counter.most_common(3)]
        if top_terms:
            emerging.append(f"Cluster: {' / '.join(top_terms)} ({len(member_indices)} comments)")
    return emerging


def analyze_comments_in_batches(
    video_meta: Dict[str, Any],
    comments: List[Dict[str, Any]],
    provider: Optional[BaseLLMProvider] = None,
    progress_cb: Optional[Callable[[int, str], None]] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Analyze collected comments in batches and compute strictly grounded aggregates."""
    settings = get_settings()
    llm = provider or get_llm_provider()
    batch_size = max(10, min(settings.ANALYSIS_BATCH_SIZE, 60))

    per_comment_results: List[Dict[str, Any]] = []
    total = len(comments)

    if total == 0:
        empty_summary = _aggregate_analysis([], [], [])
        return [], empty_summary

    for start in range(0, total, batch_size):
        batch = comments[start : start + batch_size]
        batch_num = (start // batch_size) + 1
        total_batches = (total + batch_size - 1) // batch_size

        if progress_cb:
            pct = 40 + int((start / max(1, total)) * 45)
            progress_cb(pct, f"Analyzing comment batch {batch_num}/{total_batches}...")

        batch_classified: Optional[List[Dict[str, Any]]] = None
        if llm.is_available():
            try:
                batch_classified = _llm_classify_batch(llm, video_meta, batch)
            except Exception as exc:
                logger.warning("LLM batch classification failed; falling back to lexical NLP: %s", exc)

        if not batch_classified:
            batch_classified = [_heuristic_classify_comment(c) for c in batch]

        per_comment_results.extend(batch_classified)

    emerging_clusters = _cluster_topics_with_embeddings(llm, comments)
    summary = _aggregate_analysis(comments, per_comment_results, emerging_clusters)

    if llm.is_available():
        try:
            summary = _enrich_summary_with_llm(llm, video_meta, comments[:120], summary)
        except Exception as exc:
            logger.warning("LLM qualitative synthesis fallback used: %s", exc)

    return per_comment_results, summary


def _llm_classify_batch(
    llm: BaseLLMProvider,
    video_meta: Dict[str, Any],
    batch: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    numbered = []
    for i, c in enumerate(batch):
        numbered.append(
            f"[{i}] id={c['youtube_comment_id']} likes={c['like_count']} text={c['text_sanitized'][:400]}"
        )
    joined = "\n".join(numbered)

    system_prompt = (
        "You are an expert YouTube audience sentiment analyst. "
        "Classify each provided comment strictly based on its actual text. "
        "Never invent comments or modify IDs. Return JSON with key 'items', a list of objects with: "
        "youtube_comment_id (string), sentiment ('positive'|'negative'|'neutral'), "
        "confidence (float 0.0-1.0), primary_emotion ('frustration'|'satisfaction'|'confusion'|'excitement'|'trust'), "
        "secondary_emotions (list of strings), purchase_intent (bool), is_complaint (bool), "
        "is_feature_request (bool), is_question (bool), topics (list of 1-3 concise topic labels), "
        "keywords (list of 1-5 single/two-word keywords)."
    )
    user_prompt = (
        f"Video title: {video_meta.get('title', '')}\n"
        f"<UNTRUSTED_USER_DATA>\n{joined}\n</UNTRUSTED_USER_DATA>"
    )

    resp = llm.generate_json(system_prompt, user_prompt, temperature=0.1, max_tokens=3200)
    raw_items = resp.get("items", [])
    by_id = {str(item.get("youtube_comment_id")): item for item in raw_items if isinstance(item, dict)}

    normalized: List[Dict[str, Any]] = []
    for c in batch:
        cid = c["youtube_comment_id"]
        item = by_id.get(cid)
        if not item:
            normalized.append(_heuristic_classify_comment(c))
            continue

        sent = str(item.get("sentiment", "neutral")).lower()
        if sent not in ("positive", "negative", "neutral"):
            sent = "neutral"

        emo = str(item.get("primary_emotion", "satisfaction")).lower()
        if emo not in ("frustration", "satisfaction", "confusion", "excitement", "trust"):
            emo = "satisfaction" if sent == "positive" else ("frustration" if sent == "negative" else "trust")

        normalized.append(
            {
                "youtube_comment_id": cid,
                "sentiment": sent,
                "confidence": float(min(1.0, max(0.0, float(item.get("confidence", 0.78))))),
                "primary_emotion": emo,
                "secondary_emotions": [str(x) for x in (item.get("secondary_emotions") or [])[:3]],
                "purchase_intent": bool(item.get("purchase_intent", False)),
                "is_complaint": bool(item.get("is_complaint", False)),
                "is_feature_request": bool(item.get("is_feature_request", False)),
                "is_question": bool(item.get("is_question", False)),
                "topics": [str(x)[:60] for x in (item.get("topics") or ["General Feedback"])[:3]],
                "keywords": [str(x).lower()[:32] for x in (item.get("keywords") or [])[:6]],
            }
        )
    return normalized


def _aggregate_analysis(
    comments: List[Dict[str, Any]],
    results: List[Dict[str, Any]],
    emerging_clusters: List[str],
) -> Dict[str, Any]:
    total = len(results)
    if total == 0:
        return {
            "analyzed_comments_count": 0,
            "positive_count": 0,
            "negative_count": 0,
            "neutral_count": 0,
            "positive_pct": 0.0,
            "negative_pct": 0.0,
            "neutral_pct": 0.0,
            "emotion_distribution_json": {},
            "topics_json": [],
            "keywords_json": [],
            "pain_points_json": [],
            "complaints_json": [],
            "feature_requests_json": [],
            "faqs_json": [],
            "buying_objections_json": [],
            "suggestions_json": [],
            "emerging_topics_json": [],
            "sentiment_trends_json": [],
        }

    comment_by_id = {c["youtube_comment_id"]: c for c in comments}

    pos = sum(1 for r in results if r["sentiment"] == "positive")
    neg = sum(1 for r in results if r["sentiment"] == "negative")
    neu = total - pos - neg

    emotion_counter: Counter[str] = Counter()
    topic_counter: Counter[str] = Counter()
    keyword_counter: Counter[str] = Counter()
    pain_counter: Counter[str] = Counter()
    date_buckets: Dict[str, Dict[str, int]] = defaultdict(lambda: {"positive": 0, "negative": 0, "neutral": 0})

    complaints: List[str] = []
    feature_requests: List[str] = []
    faqs: List[str] = []
    buying_objections: List[str] = []
    suggestions: List[str] = []

    for r in results:
        c = comment_by_id.get(r["youtube_comment_id"], {})
        text = c.get("text_sanitized", "")
        low = text.lower()

        emotion_counter[r["primary_emotion"]] += 1
        for t in r.get("topics", []):
            topic_counter[t] += 1
            if r["sentiment"] == "negative" or r["is_complaint"] or r["primary_emotion"] in ("frustration", "confusion"):
                pain_counter[t] += 1

        for kw in r.get("keywords", []):
            if kw and kw not in STOPWORDS and len(kw) > 2:
                keyword_counter[kw] += 1

        pub = c.get("published_at")
        if isinstance(pub, datetime):
            day_key = pub.strftime("%Y-%m-%d")
            date_buckets[day_key][r["sentiment"]] += 1

        if r["is_complaint"] and text and text not in complaints:
            complaints.append(text[:220])
        if r["is_feature_request"] and text and text not in feature_requests:
            feature_requests.append(text[:220])
        if r["is_question"] and text and text not in faqs:
            faqs.append(text[:220])
        if any(m in low for m in OBJECTION_MARKERS) and text and text not in buying_objections:
            buying_objections.append(text[:220])
        if (r["is_feature_request"] or "recommend" in low or "should" in low) and text and text not in suggestions:
            suggestions.append(text[:220])

    topics_ranked = [
        {"topic": topic, "count": count, "share_pct": round((count / total) * 100, 1)}
        for topic, count in topic_counter.most_common(12)
    ]
    keywords_ranked = [
        {"keyword": kw, "count": count}
        for kw, count in keyword_counter.most_common(25)
    ]
    pain_points_ranked = [
        {
            "pain_point": topic,
            "mentions": count,
            "severity_score": round(min(100.0, (count / max(1, total)) * 240.0), 1),
        }
        for topic, count in pain_counter.most_common(8)
    ]

    trends = [
        {
            "date": day,
            "positive": vals["positive"],
            "negative": vals["negative"],
            "neutral": vals["neutral"],
            "total": vals["positive"] + vals["negative"] + vals["neutral"],
        }
        for day, vals in sorted(date_buckets.items())
    ]

    emerging = emerging_clusters or [
        f"{t['topic']} ({t['share_pct']}% of comments)" for t in topics_ranked[:5]
    ]

    return {
        "analyzed_comments_count": total,
        "positive_count": pos,
        "negative_count": neg,
        "neutral_count": neu,
        "positive_pct": round((pos / total) * 100, 2),
        "negative_pct": round((neg / total) * 100, 2),
        "neutral_pct": round((neu / total) * 100, 2),
        "emotion_distribution_json": dict(emotion_counter),
        "topics_json": topics_ranked,
        "keywords_json": keywords_ranked,
        "pain_points_json": pain_points_ranked,
        "complaints_json": complaints[:10],
        "feature_requests_json": feature_requests[:10],
        "faqs_json": faqs[:10],
        "buying_objections_json": buying_objections[:10],
        "suggestions_json": suggestions[:10],
        "emerging_topics_json": emerging[:8],
        "sentiment_trends_json": trends,
    }


def _enrich_summary_with_llm(
    llm: BaseLLMProvider,
    video_meta: Dict[str, Any],
    sample_comments: List[Dict[str, Any]],
    summary: Dict[str, Any],
) -> Dict[str, Any]:
    """Use LLM to distill cleaner human-readable lists strictly from the collected comments."""
    snippets = "\n".join(f"- {c['text_sanitized'][:260]}" for c in sample_comments[:80])
    resp = llm.generate_json(
        system_prompt=(
            "Synthesize concise, accurate lists grounded ONLY in the supplied YouTube comments. "
            "Do not invent metrics or facts not present in the comments. Return JSON with keys: "
            "complaints (list[str]), feature_requests (list[str]), faqs (list[str]), "
            "buying_objections (list[str]), suggestions (list[str]), emerging_topics (list[str])."
        ),
        user_prompt=(
            f"Video: {video_meta.get('title', '')}\n"
            f"<UNTRUSTED_USER_DATA>\n{snippets}\n</UNTRUSTED_USER_DATA>"
        ),
        temperature=0.2,
        max_tokens=1600,
    )
    for key_out, key_in in (
        ("complaints_json", "complaints"),
        ("feature_requests_json", "feature_requests"),
        ("faqs_json", "faqs"),
        ("buying_objections_json", "buying_objections"),
        ("suggestions_json", "suggestions"),
        ("emerging_topics_json", "emerging_topics"),
    ):
        vals = resp.get(key_in)
        if isinstance(vals, list) and vals:
            summary[key_out] = [str(v)[:260] for v in vals[:10]]
    return summary
