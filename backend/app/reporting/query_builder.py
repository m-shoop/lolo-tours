"""SQL query builder for reports defined in ``app.reporting.registry``.

The builder walks a ``ReportRequest`` (filters, columns, sort, pagination),
validates each piece against the report's ``FieldDefinition``\\s, and emits a
parameterised SQL statement. Inputs are never interpolated as raw SQL — they
travel as bound parameters.
"""
from __future__ import annotations

import logging
from datetime import date as _date
from datetime import datetime as _datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.reporting.registry import (
    ENTITY_TABLE,
    REPORTS,
    FieldDefinition,
    ReportDefinition,
)
from app.schemas.report import (
    FilterCondition,
    FilterGroup,
    ReportRequest,
    ReportResponse,
)

logger = logging.getLogger(__name__)


class ReportValidationError(ValueError):
    pass


class ReportPermissionError(PermissionError):
    pass


def _coerce_param(value, field_type: str):
    if field_type == "date" and isinstance(value, str):
        return _date.fromisoformat(value)
    if field_type == "datetime" and isinstance(value, str):
        return _datetime.fromisoformat(value)
    if field_type == "integer" and isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return value
    if field_type == "boolean" and isinstance(value, str):
        return value.lower() in ("true", "1", "yes")
    return value


def _build_condition(
    field_def: FieldDefinition,
    field_key: str,
    condition: FilterCondition,
    params: dict,
) -> str:
    if condition.op not in field_def.operators:
        raise ReportValidationError(
            f"Operator '{condition.op}' is not allowed for field '{field_key}'"
        )

    col = field_def.column
    base = f"p{len(params)}"
    op = condition.op
    ft = field_def.type

    if op == "equals":
        params[base] = _coerce_param(condition.value, ft)
        return f"{col} = :{base}"
    if op == "contains":
        params[base] = f"%{condition.value}%"
        return f"{col} ILIKE :{base}"
    if op == "starts_with":
        params[base] = f"{condition.value}%"
        return f"{col} ILIKE :{base}"
    if op == "in":
        values = condition.value if isinstance(condition.value, list) else [condition.value]
        placeholders = []
        for i, v in enumerate(values):
            k = f"{base}_{i}"
            params[k] = _coerce_param(v, ft)
            placeholders.append(f":{k}")
        return f"{col} IN ({', '.join(placeholders)})"
    if op == "between":
        values = condition.value if isinstance(condition.value, list) else [condition.value]
        if len(values) != 2:
            raise ReportValidationError(
                f"'between' requires exactly 2 values for '{field_key}'"
            )
        params[f"{base}_lo"] = _coerce_param(values[0], ft)
        params[f"{base}_hi"] = _coerce_param(values[1], ft)
        return f"{col} BETWEEN :{base}_lo AND :{base}_hi"
    if op == "before":
        params[base] = _coerce_param(condition.value, ft)
        return f"{col} < :{base}"
    if op == "after":
        params[base] = _coerce_param(condition.value, ft)
        return f"{col} > :{base}"
    if op == "is_empty":
        return f"({col} IS NULL OR {col} = '')"
    if op == "is_not_empty":
        return f"({col} IS NOT NULL AND {col} != '')"

    raise ReportValidationError(f"Unknown operator: '{op}'")


def _build_filter_group(
    report: ReportDefinition,
    group: FilterGroup,
    params: dict,
    user_permissions: frozenset[str],
) -> tuple[str, set[str]]:
    parts: list[str] = []
    required_joins: set[str] = set()

    for condition in group.conditions:
        field_def = report.fields.get(condition.field)
        if field_def is None:
            raise ReportValidationError(f"Unknown field: '{condition.field}'")
        if not field_def.filterable:
            raise ReportValidationError(
                f"Field '{condition.field}' is not filterable"
            )
        if (
            field_def.requires_permission
            and field_def.requires_permission not in user_permissions
        ):
            raise ReportPermissionError(
                f"Insufficient permissions for field '{condition.field}'"
            )
        if field_def.join:
            required_joins.add(field_def.join)
        parts.append(_build_condition(field_def, condition.field, condition, params))

    for subgroup in group.groups:
        sub_sql, sub_joins = _build_filter_group(
            report, subgroup, params, user_permissions
        )
        required_joins |= sub_joins
        parts.append(f"({sub_sql})")

    if not parts:
        return "TRUE", required_joins

    return f" {group.logic} ".join(parts), required_joins


def _resolve_join_order(
    report: ReportDefinition, required: set[str]
) -> list[str]:
    full: set[str] = set(required)
    changed = True
    while changed:
        changed = False
        for key in list(full):
            dep = report.joins[key].depends_on
            if dep and dep not in full:
                full.add(dep)
                changed = True

    ordered: list[str] = []
    remaining = set(full)
    while remaining:
        for key in sorted(remaining):
            dep = report.joins[key].depends_on
            if dep is None or dep in ordered:
                ordered.append(key)
                remaining.remove(key)
                break
        else:
            raise ReportValidationError(
                "Circular dependency detected in report joins"
            )
    return ordered


def _build_join_sql(report: ReportDefinition, join_keys: list[str]) -> str:
    parts = []
    for key in join_keys:
        jd = report.joins[key]
        table = ENTITY_TABLE[jd.entity]
        table_ref = f"{table} AS {jd.alias}" if jd.alias else table
        clause = f"{jd.join_type} JOIN {table_ref} ON {jd.on}"
        for cond in jd.fixed_conditions:
            clause += f" AND {cond}"
        parts.append(clause)
    return "\n".join(parts)


async def run_report(
    db: AsyncSession,
    request: ReportRequest,
    user_permissions: frozenset[str],
) -> ReportResponse:
    report = REPORTS.get(request.report)
    if report is None:
        raise ReportValidationError(f"Unknown report: '{request.report}'")

    columns = request.columns if request.columns else report.default_columns
    for col in columns:
        field = report.fields.get(col)
        if field is None:
            raise ReportValidationError(f"Unknown column: '{col}'")
        if not field.selectable:
            raise ReportValidationError(f"Column '{col}' is not selectable")
        if (
            field.requires_permission
            and field.requires_permission not in user_permissions
        ):
            raise ReportPermissionError(
                f"Insufficient permissions for column '{col}'"
            )

    params: dict = {}
    where_sql, filter_joins = _build_filter_group(
        report, request.filters, params, user_permissions
    )
    if report.base_conditions:
        base_sql = " AND ".join(report.base_conditions)
        where_sql = (
            f"{base_sql} AND ({where_sql})"
            if where_sql != "TRUE"
            else base_sql
        )

    sort_fields: list[FieldDefinition] = []
    for sort_key in request.sort_by:
        sf = report.fields.get(sort_key)
        if sf is None:
            raise ReportValidationError(f"Unknown sort field: '{sort_key}'")
        if sf.aggregate:
            raise ReportValidationError(
                f"Cannot sort by aggregate field '{sort_key}'"
            )
        sort_fields.append(sf)

    required_joins: set[str] = set(filter_joins)
    for col in columns:
        field = report.fields[col]
        if field.join:
            required_joins.add(field.join)
    for sf in sort_fields:
        if sf.join:
            required_joins.add(sf.join)

    join_keys = _resolve_join_order(report, required_joins)
    join_sql = _build_join_sql(report, join_keys)
    base_table = ENTITY_TABLE[report.base_entity]

    select_exprs = ", ".join(
        f"{report.fields[c].aggregate} AS {c}"
        if report.fields[c].aggregate
        else f"{report.fields[c].column} AS {c}"
        for c in columns
    )

    if sort_fields:
        sort_dir_sql = "DESC" if request.sort_dir == "desc" else "ASC"
        order_by_clause = "ORDER BY " + ", ".join(
            f"{sf.column} {sort_dir_sql}" for sf in sort_fields
        )
    else:
        order_by_clause = ""

    query = text(
        f"SELECT {select_exprs}"
        f" FROM {base_table}"
        f" {join_sql}"
        f" WHERE {where_sql}"
        f" {order_by_clause}"
        f" LIMIT :_limit OFFSET :_offset"
    )
    count_query = text(
        f"SELECT COUNT(DISTINCT {base_table}.id)"
        f" FROM {base_table}"
        f" {join_sql}"
        f" WHERE {where_sql}"
    )

    params["_limit"] = request.page_size
    params["_offset"] = (request.page - 1) * request.page_size
    count_params = {k: v for k, v in params.items() if not k.startswith("_")}

    result = await db.execute(query, params)
    rows = [dict(zip(columns, raw_row)) for raw_row in result.fetchall()]

    count_result = await db.execute(count_query, count_params)
    total = count_result.scalar() or 0

    return ReportResponse(
        report=request.report,
        columns=columns,
        rows=rows,
        total=total,
        page=request.page,
        page_size=request.page_size,
    )
