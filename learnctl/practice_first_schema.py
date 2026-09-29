"""Validate build-time teaching prerequisites and executable exercise metadata."""
from __future__ import annotations

import ast
from typing import Any
from .errors import DataError


def validate_practice_first(curriculum: dict[str, Any]) -> None:
    if not curriculum.get('meta', {}).get('practice_first_revision'):
        return
    sections = [s for t in curriculum['tasks'] for s in t['lesson']]
    by_id = {s['id']: s for s in sections}
    positions = {s['id']: i for i,s in enumerate(sections)}
    for s in sections:
        meta = s.get('practice_first')
        if not isinstance(meta, dict):
            raise DataError(f"{s['id']} 缺少实践优先说明")
        if not isinstance(meta.get('goal'), str) or not meta['goal'].strip():
            raise DataError(f"{s['id']} 缺少明确实践目标")
        if not isinstance(meta.get('rules'), list) or not 1 <= len(meta['rules']) <= 3:
            raise DataError(f"{s['id']} 的短规则必须为 1–3 条")
        for dependency in meta.get('prerequisites', []):
            if dependency not in by_id or positions[dependency] >= positions[s['id']]:
                raise DataError(f"{s['id']} 前置知识 {dependency} 不存在或尚未教授")
            if not s.get('optional') and by_id[dependency].get('optional'):
                raise DataError(f"必修 {s['id']} 不得依赖选修 {dependency}")
        for group in ['cards', 'drills']:
            values = meta.get(group)
            if not isinstance(values, list):
                raise DataError(f"{s['id']} {group} 必须为数组")
            for item in values:
                if not isinstance(item, dict) or not isinstance(item.get('output'), str):
                    raise DataError(f"{s['id']} {group} 缺少预期输出")
                for key in (['code'] if group == 'cards' else ['starter','reference']):
                    source = item.get(key)
                    if not isinstance(source, str) or not source.strip():
                        raise DataError(f"{s['id']} {group}.{key} 不能为空")
                    try:
                        ast.parse(source, feature_version=(3,11))
                    except SyntaxError as exc:
                        raise DataError(f"{s['id']} {group}.{key} 不是合法 Python 3.11：{exc}") from exc
