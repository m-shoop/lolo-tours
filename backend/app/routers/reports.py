import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import CurrentUser, get_current_user
from app.reporting.query_builder import (
    ReportPermissionError,
    ReportValidationError,
    run_report,
)
from app.reporting.registry import REPORTS
from app.schemas.report import (
    FieldMeta,
    ReportMeta,
    ReportRequest,
    ReportResponse,
    ReportsListResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("", response_model=ReportsListResponse)
async def list_reports(
    current_user: CurrentUser = Depends(get_current_user),
) -> ReportsListResponse:
    report_metas = []
    for report_id, report_def in REPORTS.items():
        fields: dict[str, FieldMeta] = {}
        for field_key, field_def in report_def.fields.items():
            if (
                field_def.requires_permission
                and not current_user.can(field_def.requires_permission)
            ):
                continue
            fields[field_key] = FieldMeta(
                label=field_def.label,
                type=field_def.type,
                operators=field_def.operators,
                filterable=field_def.filterable,
                selectable=field_def.selectable,
                render_as=field_def.render_as,
                enum_options=field_def.enum_source,
            )
        report_metas.append(
            ReportMeta(
                id=report_id,
                label=report_def.label,
                fields=fields,
                default_columns=report_def.default_columns,
            )
        )
    return ReportsListResponse(reports=report_metas)


@router.post("/{report_id}", response_model=ReportResponse)
async def run_report_route(
    report_id: str,
    body: ReportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> ReportResponse:
    request = body.model_copy(update={"report": report_id})
    try:
        return await run_report(db, request, current_user.permissions)
    except ReportPermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        )
    except ReportValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        )
    except Exception:
        logger.exception("Unexpected error running report '%s'", report_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Report execution failed",
        )
