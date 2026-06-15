"""
Dify Code：组装 erp_submit_requisition HTTP Body。
"""

import json
import uuid


def main(draft_id: str, idempotency_key: str = "") -> dict:
    did = str(draft_id or "").strip()
    key = str(idempotency_key or "").strip() or str(uuid.uuid4())
    body = {"draft_id": did, "idempotency_key": key}
    return {"body_json": json.dumps(body, ensure_ascii=False), "idempotency_key": key}
