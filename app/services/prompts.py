import json
import os

from app.db.models import Prompt


def normalize_placeholders(placeholders: list[str] | None) -> list[str]:
    if not placeholders:
        return []
    cleaned = [item.strip() for item in placeholders if item and item.strip()]
    return sorted(set(cleaned))


def validate_template(template: str, required_placeholders: list[str]) -> None:
    missing = [name for name in required_placeholders if f"{{{name}}}" not in template]
    if missing:
        missing_text = ", ".join(sorted(missing))
        raise ValueError(f"Missing placeholders: {missing_text}")


def load_seed_prompts(seed_path: str) -> list[dict]:
    if not seed_path or not os.path.exists(seed_path):
        return []
    with open(seed_path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        raise ValueError("Prompt seed file must be a list of prompt objects")
    return data


def seed_prompts(db, seed_path: str) -> None:
    prompts = load_seed_prompts(seed_path)
    if not prompts:
        return

    for entry in prompts:
        key = entry.get("key")
        template = entry.get("template")
        placeholders = normalize_placeholders(entry.get("required_placeholders"))
        if not key or not template:
            continue

        validate_template(template, placeholders)

        existing = db.get(Prompt, key)
        if existing is None:
            db.add(
                Prompt(
                    key=key,
                    template=template,
                    required_placeholders=placeholders,
                )
            )
        else:
            # Update existing prompt if template changed
            if existing.template != template:
                existing.template = template
                existing.required_placeholders = placeholders
    db.commit()


def get_prompt(db, key: str) -> Prompt | None:
    return db.get(Prompt, key)
