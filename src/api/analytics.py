"""
Analytics routes: KPI tracking, time-series data, performance trends.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Request

from src.api.middleware import get_current_user
from src.core import database as db

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/overview")
async def get_overview(request: Request, days: int = 30):
    """Get analytics overview for the specified time period."""
    user = get_current_user(request)
    analytics = await db.get_analytics(user["user_id"], days)

    if not analytics:
        return {
            "period_days": days,
            "total_sessions": 0,
            "total_minutes": 0,
            "avg_score": 0,
            "score_trend": [],
            "category_averages": {},
            "objection_stats": {"faced": 0, "resolved": 0, "rate": 0},
            "style_distribution": {},
        }

    total_sessions = sum(a.get("sessions_count", 0) for a in analytics)
    total_minutes = sum(a.get("total_minutes", 0) for a in analytics)
    overall_scores = [a["avg_overall"] for a in analytics if a.get("avg_overall") is not None and a.get("sessions_count", 0) > 0]
    avg_score = sum(overall_scores) / len(overall_scores) if overall_scores else 0

    # Score trend over time
    score_trend = [
        {"date": str(a["date"]), "score": a.get("avg_overall", 0)}
        for a in analytics
    ]

    # Category averages
    categories = [
        "tonality", "rapport", "questions", "compliance", "flow",
        "trust", "objection_handling", "preframing", "presentation",
        "close", "underwriting",
    ]
    category_averages = {}
    for cat in categories:
        key = f"avg_{cat}"
        vals = [a.get(key, 0) for a in analytics if a.get(key) is not None and a.get("sessions_count", 0) > 0]
        category_averages[cat] = sum(vals) / len(vals) if vals else 0

    # Objection stats
    total_faced = sum(a.get("objections_faced", 0) for a in analytics)
    total_resolved = sum(a.get("objections_resolved", 0) for a in analytics)

    # Style distribution
    styles = {}
    for a in analytics:
        dist = a.get("style_distribution", {})
        if isinstance(dist, str):
            import json
            dist = json.loads(dist)
        for style, count in dist.items():
            styles[style] = styles.get(style, 0) + count

    # Close probability trend
    close_trend = [
        {"date": str(a["date"]), "probability": a.get("avg_close_probability", 0)}
        for a in analytics
    ]

    return {
        "period_days": days,
        "total_sessions": total_sessions,
        "total_minutes": round(total_minutes, 1),
        "avg_score": round(avg_score, 1),
        "score_trend": score_trend,
        "close_probability_trend": close_trend,
        "category_averages": {k: round(v, 1) for k, v in category_averages.items()},
        "objection_stats": {
            "faced": total_faced,
            "resolved": total_resolved,
            "rate": round(total_resolved / total_faced * 100, 1) if total_faced > 0 else 0,
        },
        "style_distribution": styles,
    }


@router.get("/trends")
async def get_trends(request: Request, days: int = 30):
    """Get detailed daily trends for charting."""
    user = get_current_user(request)
    analytics = await db.get_analytics(user["user_id"], days)

    return {
        "period_days": days,
        "daily": [
            {
                "date": str(a["date"]),
                "sessions": a.get("sessions_count", 0),
                "minutes": round(a.get("total_minutes", 0), 1),
                "overall": round(a.get("avg_overall", 0), 1),
                "tonality": round(a.get("avg_tonality", 0), 1),
                "rapport": round(a.get("avg_rapport", 0), 1),
                "questions": round(a.get("avg_questions", 0), 1),
                "compliance": round(a.get("avg_compliance", 0), 1),
                "flow": round(a.get("avg_flow", 0), 1),
                "trust": round(a.get("avg_trust", 0), 1),
                "objection_handling": round(a.get("avg_objection_handling", 0), 1),
                "preframing": round(a.get("avg_preframing", 0), 1),
                "presentation": round(a.get("avg_presentation", 0), 1),
                "close": round(a.get("avg_close", 0), 1),
                "underwriting": round(a.get("avg_underwriting", 0), 1),
                "close_probability": round(a.get("avg_close_probability", 0), 1),
                "objections_faced": a.get("objections_faced", 0),
                "objections_resolved": a.get("objections_resolved", 0),
            }
            for a in analytics
        ],
    }


@router.get("/report-cards")
async def list_report_cards(request: Request, limit: int = 50, offset: int = 0):
    """Get all report cards for the user."""
    user = get_current_user(request)
    return await db.get_user_report_cards(user["user_id"], limit, offset)


@router.get("/report-cards/by-session/{session_id}")
async def get_report_by_session(session_id: str, request: Request):
    """Look up a report card by its training session ID."""
    from fastapi import HTTPException
    user = get_current_user(request)
    report = await db.get_report_card_by_session(session_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found for this session")
    if str(report["user_id"]) != user["user_id"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    return report


@router.get("/report-cards/{report_id}")
async def get_report_card(report_id: str, request: Request):
    from fastapi import HTTPException
    user = get_current_user(request)
    report = await db.get_report_card(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if str(report["user_id"]) != user["user_id"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    return report
