"""JSON persistence shared by the desktop UI and future integrations."""
import copy
import json
import logging
import math
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from config import DEFAULT_STATE
from income import validate_income, validate_schedule


def preserve_invalid(path):
    backup = path.with_name(f"{path.name}.invalid-{datetime.now():%Y%m%d-%H%M%S}-{uuid4().hex[:8]}.bak")
    shutil.copy2(path, backup)
    logging.warning("Invalid data preserved at %s", backup)


def read_json(path, default, expected_type=None):
    path = Path(path)
    if not path.exists():
        return copy.deepcopy(default)
    try:
        with path.open(encoding="utf-8") as stream:
            value = json.load(stream)
        if expected_type is not None and not isinstance(value, expected_type):
            raise ValueError("Unexpected JSON root type")
        return value
    except (ValueError, UnicodeError):
        # Permission and I/O failures must propagate, not silently reset data.
        preserve_invalid(path)
        return copy.deepcopy(default)


def write_json(path, value):
    """Replace only after serialization and writing succeed; reject NaN/Infinity."""
    path = Path(path)
    payload = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def merge_defaults(default, loaded, repairs=None):
    """Keep extension fields, repairing incompatible shapes in known fields."""
    if isinstance(default, dict):
        if not isinstance(loaded, dict) and repairs is not None:
            repairs.append(True)
        result = copy.deepcopy(loaded) if isinstance(loaded, dict) else {}
        for key, value in default.items():
            result[key] = merge_defaults(value, result.get(key, value), repairs)
        return result
    if default is None:
        return copy.deepcopy(loaded)
    if isinstance(default, (int, float)) and not isinstance(default, bool):
        if not isinstance(loaded, (int, float)) or isinstance(loaded, bool) or not math.isfinite(loaded):
            if repairs is not None:
                repairs.append(True)
            return default
    elif not isinstance(loaded, type(default)):
        if repairs is not None:
            repairs.append(True)
        return copy.deepcopy(default)
    return copy.deepcopy(loaded)


class DataStore:
    def __init__(self, path):
        self.path = Path(path)
        loaded = read_json(self.path, DEFAULT_STATE, dict)
        repairs = []
        self.state = merge_defaults(DEFAULT_STATE, loaded, repairs)
        income = self.state["income"]
        try:
            validate_income(income["monthly_net_salary"], income["weekly_work_hours"], income["employment_start"])
            validate_schedule(income["work_start"], income["work_end"])
        except (ValueError, TypeError):
            repairs.append(True)
            income.update(copy.deepcopy(DEFAULT_STATE["income"]))
        if repairs and self.path.exists():
            preserve_invalid(self.path)
        display = self.state["salary_display"]
        if not .01 <= display["goal_amount"] <= 1000000:
            display["goal_amount"] = DEFAULT_STATE["salary_display"]["goal_amount"]
        display["collected_today"] = max(0, display["collected_today"])
        # Unknown fields survive round trips so later applications can extend state.
        self.state.setdefault("schema_version", 1)
        if not self.path.exists():
            self.save()

    def save(self, data=None):
        write_json(self.path, self.state if data is None else data)
