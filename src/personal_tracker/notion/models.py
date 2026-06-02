from __future__ import annotations

import copy
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, ClassVar
from zoneinfo import ZoneInfo

from dateutil.parser import isoparse

from .recurring import next_time_by_recurring_type


def _parse_dt(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    return isoparse(str(value))


@dataclass
class Task:
    notion_object_id: str
    task_name: str | None = None
    time_mark: datetime | None = None
    end_time: datetime | None = None
    deadline: datetime | None = None
    is_done: bool = False
    remind: bool = False
    recurring_type: str = "once"
    raw_data: dict[str, Any] = field(default_factory=dict)

    REQUIRED_ATTRS: ClassVar[tuple[str, ...]] = ("task_name", "time_mark", "recurring_type")

    PROPERTY_TYPES: ClassVar[dict[str, str]] = {
        "task_name": "title",
        "time_mark": "date",
        "end_time": "date",
        "deadline": "date",
        "is_done": "checkbox",
        "remind": "checkbox",
        "recurring_type": "select",
    }

    def is_valid(self) -> bool:
        if not self.notion_object_id:
            return False
        for attr in self.REQUIRED_ATTRS:
            value = getattr(self, attr)
            if value is None or (isinstance(value, str) and not value.strip()):
                return False
        return True

    def next_time_by_recurring_type(self, *, now: datetime) -> datetime | None:
        if self.time_mark is None:
            return None
        return next_time_by_recurring_type(self.time_mark, self.recurring_type, now=now)

    @classmethod
    def from_data(
        cls,
        json_data: dict[str, Any] | list[dict[str, Any]],
        attribute_names_mapping: dict[str, str],
    ) -> Task | list[Task]:
        if isinstance(json_data, list):
            return [cls._new_from_json(item, attribute_names_mapping) for item in json_data]
        return cls._new_from_json(json_data, attribute_names_mapping)

    @classmethod
    def _new_from_json(
        cls,
        json_data: dict[str, Any],
        attribute_names_mapping: dict[str, str],
    ) -> Task:
        properties = json_data.get("properties") or {}
        # Filter to only mapped properties (mirrors Ruby `slice`).
        mapped = set(attribute_names_mapping.values())
        relevant = {name: prop for name, prop in properties.items() if name in mapped}

        # property_name -> attribute_name
        prop_to_attr = {v: k for k, v in attribute_names_mapping.items()}

        attrs: dict[str, Any] = {}
        for property_name, value_obj in relevant.items():
            attr_key = prop_to_attr.get(property_name)
            if attr_key is None:
                continue
            ptype = value_obj.get("type")
            if ptype == "select":
                attrs[attr_key] = (value_obj.get("select") or {}).get("name")
            elif ptype == "date":
                date_obj = value_obj.get("date") or {}
                attrs[attr_key] = _parse_dt(date_obj.get("start"))
                end_val = date_obj.get("end")
                if end_val:
                    end_attr = prop_to_attr.get(f"{property_name} end")
                    if end_attr:
                        attrs[end_attr] = _parse_dt(end_val)
            elif ptype == "checkbox":
                attrs[attr_key] = bool(value_obj.get("checkbox"))
            elif ptype == "title":
                titles = value_obj.get("title") or []
                attrs[attr_key] = titles[0].get("plain_text") if titles else None
            else:
                attrs[attr_key] = None

        # Apply default for recurring_type if Notion returned nothing.
        if "recurring_type" in attribute_names_mapping and not attrs.get("recurring_type"):
            attrs["recurring_type"] = "once"

        return cls(
            notion_object_id=json_data["id"],
            raw_data=properties,
            **attrs,
        )

    @staticmethod
    def _empty_property(ptype: str) -> dict[str, Any]:
        if ptype == "title":
            return {"type": "title", "title": []}
        if ptype == "date":
            return {"type": "date", "date": None}
        if ptype == "checkbox":
            return {"type": "checkbox", "checkbox": False}
        if ptype == "select":
            return {"type": "select", "select": None}
        return {"type": ptype}

    def to_data(
        self,
        attribute_names_mapping: dict[str, str],
        *,
        skip_time: bool,
        tz: ZoneInfo,
    ) -> dict[str, Any]:
        result = copy.deepcopy(self.raw_data)

        for attr_name, property_name in attribute_names_mapping.items():
            if property_name in result:
                continue
            ptype = self.PROPERTY_TYPES.get(attr_name)
            if ptype is None:
                continue
            attr_value = getattr(self, attr_name, None)
            if attr_value is None and ptype != "checkbox":
                continue
            result[property_name] = self._empty_property(ptype)

        for attr_name, property_name in attribute_names_mapping.items():
            prop = result.get(property_name)
            if prop is None:
                continue
            ptype = prop.get("type")
            attr_value = getattr(self, attr_name, None)

            if ptype == "select":
                if attr_value is None:
                    prop["select"] = None
                else:
                    prop["select"] = {"name": attr_value}
            elif ptype == "date":
                old_date = prop.get("date")
                if isinstance(attr_value, datetime):
                    local = attr_value.astimezone(tz)
                    new_date = local.date().isoformat() if skip_time else local.isoformat()
                else:
                    new_date = None

                if (old_date is None or not old_date.get("start")) and new_date is None:
                    continue
                if old_date is None:
                    prop["date"] = {"start": new_date, "end": None}
                else:
                    old_date["start"] = new_date
            elif ptype == "checkbox":
                prop["checkbox"] = bool(attr_value)
            elif ptype == "title":
                content = "" if attr_value is None else str(attr_value)
                titles = prop.get("title") or []
                if titles:
                    if "text" in titles[0]:
                        titles[0]["text"]["content"] = content
                    titles[0]["plain_text"] = content
                else:
                    prop["title"] = [
                        {"type": "text", "text": {"content": content}, "plain_text": content}
                    ]
        return result
