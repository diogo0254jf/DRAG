from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.models import Prompt
from app.db.session import get_session
from app.schemas import PromptCreate, PromptOut, PromptUpdate
from app.services.prompts import normalize_placeholders, validate_template

router = APIRouter(prefix="/prompts", tags=["prompts"])


@router.get("", response_model=list[PromptOut])
def list_prompts(db: Session = Depends(get_session)) -> list[PromptOut]:
    prompts = db.query(Prompt).order_by(Prompt.key.asc()).all()
    return [
        PromptOut(
            key=p.key,
            template=p.template,
            required_placeholders=p.required_placeholders,
            updated_at=p.updated_at,
        )
        for p in prompts
    ]


@router.post("", response_model=PromptOut, status_code=201)
def create_prompt(payload: PromptCreate, db: Session = Depends(get_session)) -> PromptOut:
    existing = db.get(Prompt, payload.key)
    if existing is not None:
        raise HTTPException(status_code=409, detail="Prompt already exists")

    required_placeholders = normalize_placeholders(payload.required_placeholders)
    validate_template(payload.template, required_placeholders)

    prompt = Prompt(
        key=payload.key,
        template=payload.template,
        required_placeholders=required_placeholders,
    )
    db.add(prompt)
    db.commit()
    db.refresh(prompt)

    return PromptOut(
        key=prompt.key,
        template=prompt.template,
        required_placeholders=prompt.required_placeholders,
        updated_at=prompt.updated_at,
    )


@router.put("/{key}", response_model=PromptOut)
def update_prompt(key: str, payload: PromptUpdate, db: Session = Depends(get_session)) -> PromptOut:
    prompt = db.get(Prompt, key)
    if prompt is None:
        raise HTTPException(status_code=404, detail="Prompt not found")

    new_template = payload.template if payload.template is not None else prompt.template
    new_required = (
        normalize_placeholders(payload.required_placeholders)
        if payload.required_placeholders is not None
        else prompt.required_placeholders
    )

    try:
        validate_template(new_template, new_required)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    prompt.template = new_template
    prompt.required_placeholders = new_required
    prompt.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(prompt)
    return PromptOut(
        key=prompt.key,
        template=prompt.template,
        required_placeholders=prompt.required_placeholders,
        updated_at=prompt.updated_at,
    )
