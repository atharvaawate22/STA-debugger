import json

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from .. import config
from ..auth import get_current_user
from ..database import get_db
from ..db_models import Analysis, ApiKey, User
from ..compare import compare_results
from ..llm import ExplanationError, explain_path
from ..rules import analyze_report
from ..schemas import (
    AnalysisDetail,
    AnalysisListItem,
    AnalysisResult,
    ComparisonResult,
    ExplainRequest,
    ExplainResponse,
)
from ..sta_parser import STAParser

router = APIRouter(prefix="/api/analyses", tags=["analyses"])


def _get_owned_analysis(analysis_id: int, user: User, db: Session) -> Analysis:
    analysis = (
        db.query(Analysis)
        .filter(Analysis.id == analysis_id, Analysis.user_id == user.id)
        .first()
    )
    if analysis is None:
        raise HTTPException(404, "Analysis not found.")
    return analysis


@router.post("", response_model=AnalysisDetail, status_code=201)
async def create_analysis(
    file: UploadFile,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    raw = await file.read()
    if len(raw) > config.MAX_UPLOAD_BYTES:
        raise HTTPException(413, "Report file is too large (2 MB limit).")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(400, "Report must be a plain-text file.")

    parser = STAParser(text)
    paths = parser.parse()
    if not paths:
        raise HTTPException(
            422,
            "No timing paths found. Expected an OpenSTA-style report with "
            "'Startpoint:' blocks and slack lines.",
        )

    result = analyze_report(paths, skipped_blocks=parser.skipped)

    analysis = Analysis(
        user_id=user.id,
        filename=file.filename or "report.txt",
        result_json=result.model_dump_json(),
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    return AnalysisDetail(
        id=analysis.id,
        filename=analysis.filename,
        created_at=analysis.created_at,
        result=result,
    )


@router.get("", response_model=list[AnalysisListItem])
def list_analyses(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    analyses = (
        db.query(Analysis)
        .filter(Analysis.user_id == user.id)
        .order_by(Analysis.created_at.desc())
        .all()
    )
    items = []
    for analysis in analyses:
        result = json.loads(analysis.result_json)
        items.append(AnalysisListItem(
            id=analysis.id,
            filename=analysis.filename,
            created_at=analysis.created_at,
            summary=result["summary"],
        ))
    return items


@router.get("/compare", response_model=ComparisonResult)
def compare(
    base_id: int,
    new_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Declared before /{analysis_id} so "compare" isn't parsed as an id.
    base = _get_owned_analysis(base_id, user, db)
    new = _get_owned_analysis(new_id, user, db)
    return compare_results(
        AnalysisResult.model_validate_json(base.result_json),
        AnalysisResult.model_validate_json(new.result_json),
        base.id, new.id, base.filename, new.filename,
    )


@router.get("/{analysis_id}", response_model=AnalysisDetail)
def get_analysis(
    analysis_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    analysis = _get_owned_analysis(analysis_id, user, db)
    return AnalysisDetail(
        id=analysis.id,
        filename=analysis.filename,
        created_at=analysis.created_at,
        result=json.loads(analysis.result_json),
    )


@router.delete("/{analysis_id}", status_code=204)
def delete_analysis(
    analysis_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    analysis = _get_owned_analysis(analysis_id, user, db)
    db.delete(analysis)
    db.commit()


@router.post("/{analysis_id}/paths/{path_index}/explain", response_model=ExplainResponse)
def explain(
    analysis_id: int,
    path_index: int,
    body: ExplainRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    analysis = _get_owned_analysis(analysis_id, user, db)
    result = AnalysisResult.model_validate_json(analysis.result_json)

    if not 0 <= path_index < len(result.paths):
        raise HTTPException(404, "Path index out of range.")

    api_key = _resolve_api_key(body.api_key_id, db)

    try:
        explanation = explain_path(result.paths[path_index], api_key)
    except ExplanationError as exc:
        raise HTTPException(502, str(exc))

    return ExplainResponse(explanation=explanation)


def _resolve_api_key(api_key_id, db: Session) -> str:
    """Turn a chosen pool-key id into an actual secret.

    Users can only reference keys the admin has provisioned. If none is
    specified we fall back to the single active pool key, then to the server's
    GROQ_API_KEY env var — but a user can never supply a raw key of their own.
    """
    if api_key_id is not None:
        key = (
            db.query(ApiKey)
            .filter(ApiKey.id == api_key_id, ApiKey.is_active.is_(True))
            .first()
        )
        if key is None:
            raise HTTPException(400, "That API key is not available.")
        return key.secret

    active = db.query(ApiKey).filter(ApiKey.is_active.is_(True)).all()
    if len(active) == 1:
        return active[0].secret
    if len(active) > 1:
        raise HTTPException(400, "Select which API key to use.")

    if config.GROQ_API_KEY:
        return config.GROQ_API_KEY
    raise HTTPException(
        400,
        "No API key is available. Ask an administrator to add a Groq key to the pool.",
    )
