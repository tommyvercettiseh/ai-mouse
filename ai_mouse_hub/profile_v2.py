from __future__ import annotations

from datetime import datetime
from typing import Iterable

from .core import DATA, PROFILES, Session, _path_features, atomic_json, load_points, normalize_path
from .human_profile import extract_aim_lab_templates, extract_click_templates


def build_master_profile(sessions: Iterable[Session]) -> dict:
    """Build one local profile from normal recordings and human Aim Lab runs.

    Normal recordings preserve spontaneous behaviour. Human Aim Lab runs have
    known targets and therefore receive a higher selection weight.
    """
    session_list = [session for session in sessions if session.included]
    legacy_paths: list[list[tuple[float, float]]] = []
    human_templates: list[dict] = []
    source_ids: list[str] = []
    labels: set[str] = set()

    for session in session_list:
        points_path = session.folder / "points.csv"
        normalized = normalize_path(load_points(points_path))
        if normalized:
            legacy_paths.append(normalized)
            source_ids.append(session.session_id)
            labels.add(session.label)

        for template in extract_click_templates(points_path, session.label):
            item = template.to_dict()
            item.update({
                "source_type": "recording",
                "source_session": session.session_id,
                "selection_weight": round(max(0.1, template.quality), 3),
            })
            human_templates.append(item)

    aim_templates = extract_aim_lab_templates(DATA / "aim_lab")
    for item in aim_templates:
        enriched = dict(item)
        enriched["source_type"] = "aim_lab"
        enriched["selection_weight"] = round(max(0.25, float(item.get("quality", 0.5))) * 2.0, 3)
        human_templates.append(enriched)
        labels.add(str(item.get("context") or "Gaming"))

    if not legacy_paths and not human_templates:
        raise ValueError("Geen bruikbare recordings of menselijke Aim Lab-runs gevonden")

    features = [_path_features(path) for path in legacy_paths]
    feature_summary = {}
    if features:
        feature_summary = {
            key: {
                "min": min(item[key] for item in features),
                "mean": sum(item[key] for item in features) / len(features),
                "max": max(item[key] for item in features),
            }
            for key in features[0]
        }

    human_templates.sort(
        key=lambda item: (
            float(item.get("selection_weight", 0.0)),
            float(item.get("quality", 0.0)),
        ),
        reverse=True,
    )
    human_templates = human_templates[:5000]

    aim_count = sum(1 for item in human_templates if item.get("source_type") == "aim_lab")
    recording_count = sum(1 for item in human_templates if item.get("source_type") == "recording")
    profile = {
        "profile_id": "standalone_ai_mouse_profile",
        "profile_version": "0.9.1",
        "created": datetime.now().isoformat(timespec="seconds"),
        "source_count": len(source_ids),
        "source_ids": source_ids,
        "labels": sorted(labels),
        "features": feature_summary,
        "templates": legacy_paths[:200],
        "human_templates": human_templates,
        "human_template_count": len(human_templates),
        "recording_template_count": recording_count,
        "aim_lab_template_count": aim_count,
        "selection_policy": {
            "aim_lab_weight": 2.0,
            "recording_weight": 1.0,
            "reason": "Aim Lab targets are known; recordings preserve spontaneous behaviour.",
        },
    }
    atomic_json(PROFILES / "master_profile.json", profile)
    atomic_json(PROFILES / f"master_profile_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.json", profile)
    return profile
