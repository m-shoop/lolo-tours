"""Registry of available reports.

Each ``ReportDefinition`` declares a base table, optional joins, and field
definitions. Fields advertise their type, operators, filterability, etc., which
the query builder consumes to build a parameterised SQL statement.

Adding a new report = add an entry to ``REPORTS``.
"""
from typing import Literal

from pydantic import BaseModel


class FieldDefinition(BaseModel):
    column: str
    type: Literal["date", "datetime", "text", "boolean", "integer", "enum"]
    operators: list[str]
    filterable: bool = True
    selectable: bool = True
    join: str | None = None
    aggregate: str | None = None
    requires_permission: str | None = None
    label: str
    render_as: Literal["text", "date", "datetime", "badge", "currency_cents"] = "text"
    enum_source: list[str] | None = None


class JoinDefinition(BaseModel):
    entity: str
    on: str
    join_type: Literal["LEFT", "INNER"] = "LEFT"
    depends_on: str | None = None
    fixed_conditions: list[str] = []
    alias: str | None = None


class ReportDefinition(BaseModel):
    label: str
    base_entity: str
    base_conditions: list[str] = []
    joins: dict[str, JoinDefinition] = {}
    fields: dict[str, FieldDefinition]
    default_columns: list[str]


ENTITY_TABLE: dict[str, str] = {
    "Tour": "tours",
    "TourImage": "tour_images",
    "TourSlot": "tour_slots",
    "User": "users",
}


_TEXT_OPS = ["equals", "contains", "starts_with", "is_empty", "is_not_empty"]
_INT_OPS = ["equals", "between", "before", "after", "in"]
_DATE_OPS = ["equals", "between", "before", "after"]
_ENUM_OPS = ["equals", "in"]
_BOOL_OPS = ["equals"]


REPORTS: dict[str, ReportDefinition] = {
    "tours": ReportDefinition(
        label="Tours",
        base_entity="Tour",
        joins={
            "thumbnail": JoinDefinition(
                entity="TourImage",
                alias="thumb",
                on="thumb.tour_id = tours.id",
                join_type="LEFT",
                fixed_conditions=["thumb.use_as_thumbnail = TRUE"],
            ),
        },
        fields={
            "id": FieldDefinition(
                column="tours.id",
                type="text",
                operators=["equals"],
                label="ID",
            ),
            "name": FieldDefinition(
                column="tours.name",
                type="text",
                operators=_TEXT_OPS,
                label="Name",
            ),
            "description": FieldDefinition(
                column="tours.description",
                type="text",
                operators=_TEXT_OPS,
                label="Description",
            ),
            "price_per_person": FieldDefinition(
                column="tours.price_per_person",
                type="integer",
                operators=_INT_OPS,
                label="Price (cents)",
                render_as="currency_cents",
            ),
            "duration_minutes": FieldDefinition(
                column="tours.duration_minutes",
                type="integer",
                operators=_INT_OPS,
                label="Duration (min)",
            ),
            "max_capacity": FieldDefinition(
                column="tours.max_capacity",
                type="integer",
                operators=_INT_OPS,
                label="Max capacity",
            ),
            "is_active": FieldDefinition(
                column="tours.is_active",
                type="boolean",
                operators=_BOOL_OPS,
                label="Active",
                render_as="badge",
            ),
            "thumbnail_url": FieldDefinition(
                column="thumb.image_url",
                type="text",
                operators=[],
                filterable=False,
                label="Thumbnail",
                join="thumbnail",
            ),
            "thumbnail_alt": FieldDefinition(
                column="thumb.image_alt",
                type="text",
                operators=[],
                filterable=False,
                label="Thumbnail alt text",
                join="thumbnail",
            ),
            "created_at": FieldDefinition(
                column="tours.created_at",
                type="datetime",
                operators=_DATE_OPS,
                label="Created",
                render_as="datetime",
            ),
            "updated_at": FieldDefinition(
                column="tours.updated_at",
                type="datetime",
                operators=_DATE_OPS,
                label="Updated",
                render_as="datetime",
            ),
        },
        default_columns=[
            "id",
            "name",
            "thumbnail_url",
            "thumbnail_alt",
            "is_active",
            "max_capacity",
            "duration_minutes",
            "price_per_person",
        ],
    ),
    "tour-slots": ReportDefinition(
        label="Tour slots",
        base_entity="TourSlot",
        joins={
            "tour": JoinDefinition(
                entity="Tour",
                on="tours.id = tour_slots.tour_id",
                join_type="INNER",
            ),
        },
        fields={
            "id": FieldDefinition(
                column="tour_slots.id",
                type="text",
                operators=["equals"],
                label="ID",
            ),
            "tour_id": FieldDefinition(
                column="tour_slots.tour_id",
                type="text",
                operators=["equals", "in"],
                label="Tour",
            ),
            "tour_name": FieldDefinition(
                column="tours.name",
                type="text",
                operators=_TEXT_OPS,
                label="Tour name",
                join="tour",
            ),
            "start_time": FieldDefinition(
                column="tour_slots.start_time",
                type="datetime",
                operators=_DATE_OPS,
                label="Start time",
                render_as="datetime",
            ),
            "capacity": FieldDefinition(
                column="tour_slots.capacity",
                type="integer",
                operators=_INT_OPS,
                label="Capacity",
            ),
            "price_per_participant_cents": FieldDefinition(
                column="tour_slots.price_per_participant_cents",
                type="integer",
                operators=_INT_OPS,
                label="Price (cents)",
                render_as="currency_cents",
            ),
            "status": FieldDefinition(
                column="tour_slots.status",
                type="enum",
                operators=_ENUM_OPS,
                label="Status",
                render_as="badge",
                enum_source=["scheduled", "cancelled", "completed"],
            ),
            "notes": FieldDefinition(
                column="tour_slots.notes",
                type="text",
                operators=_TEXT_OPS,
                label="Notes",
            ),
            "created_at": FieldDefinition(
                column="tour_slots.created_at",
                type="datetime",
                operators=_DATE_OPS,
                label="Created",
                render_as="datetime",
            ),
        },
        default_columns=[
            "id",
            "tour_name",
            "start_time",
            "capacity",
            "status",
        ],
    ),
}
