from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class UserRecord:
    user_id: str
    username: str
    password: str
    name: str
    dept_id: str
    dept_name: str
    factory_id: str
    factory_name: str
    warehouse_id: str
    warehouse_name: str
    roles: list[str]
    disabled: bool = False


@dataclass
class TokenRecord:
    token: str
    user_id: str
    expires_at: datetime


@dataclass
class MaterialRecord:
    material_code: str
    material_name: str
    spec: str
    unit: str
    category: str
    on_hand_qty: float
    reserved_qty: float
    warehouse_id: str
    warehouse_name: str
    factory_id: str


@dataclass
class DraftRecord:
    draft_id: str
    user_id: str
    dept_id: str
    warehouse_id: str
    purpose: str
    remark: str
    items: list[dict[str, Any]]
    status: str = "DRAFT"
    updated_at: datetime = field(default_factory=utcnow)


@dataclass
class RequisitionRecord:
    requisition_no: str
    draft_id: str
    user_id: str
    applicant: str
    dept_id: str
    dept_name: str
    warehouse_id: str
    warehouse_name: str
    purpose: str
    remark: str
    items: list[dict[str, Any]]
    status: str
    create_date: datetime
    idempotency_key: str | None = None
    audit_by: str | None = None
    audit_date: datetime | None = None


class InMemoryStore:
    def __init__(self) -> None:
        self.tokens: dict[str, TokenRecord] = {}
        self.drafts: dict[str, DraftRecord] = {}
        self.requisitions: dict[str, RequisitionRecord] = {}
        self.idempotency_map: dict[str, str] = {}
        self.draft_seq = 0
        self.requisition_seq = 0

    def issue_token(self, user: UserRecord, expires_in: int = 7200) -> TokenRecord:
        token = secrets.token_urlsafe(32)
        record = TokenRecord(
            token=token,
            user_id=user.user_id,
            expires_at=utcnow() + timedelta(seconds=expires_in),
        )
        self.tokens[token] = record
        return record

    def get_user_by_token(self, token: str) -> UserRecord | None:
        record = self.tokens.get(token)
        if not record:
            return None
        if record.expires_at <= utcnow():
            self.tokens.pop(token, None)
            return None
        return USERS.get(record.user_id)

    def next_draft_id(self) -> str:
        self.draft_seq += 1
        day = utcnow().strftime("%Y%m%d")
        return f"DRAFT-{day}-{self.draft_seq:03d}"

    def next_requisition_no(self) -> str:
        self.requisition_seq += 1
        day = utcnow().strftime("%Y%m%d")
        return f"GON{day}{self.requisition_seq:03d}"


USERS: dict[str, UserRecord] = {
    "U001": UserRecord(
        user_id="U001",
        username="zhangsan",
        password="123456",
        name="张三",
        dept_id="D001",
        dept_name="高精密事业部",
        factory_id="F001",
        factory_name="高精密事业部",
        warehouse_id="W001",
        warehouse_name="原材料仓",
        roles=["material_request"],
    ),
    "U002": UserRecord(
        user_id="U002",
        username="lisi",
        password="123456",
        name="李四",
        dept_id="D002",
        dept_name="单面事业部",
        factory_id="F002",
        factory_name="单面事业部",
        warehouse_id="W001",
        warehouse_name="原材料仓",
        roles=["material_request"],
    ),
    "U003": UserRecord(
        user_id="U003",
        username="disabled",
        password="123456",
        name="停用账号",
        dept_id="D001",
        dept_name="高精密事业部",
        factory_id="F001",
        factory_name="高精密事业部",
        warehouse_id="W001",
        warehouse_name="原材料仓",
        roles=[],
        disabled=True,
    ),
}

USERNAME_INDEX = {u.username: u for u in USERS.values()}

MATERIALS: list[MaterialRecord] = [
    MaterialRecord(
        material_code="M001234",
        material_name="阻焊油墨",
        spec="KB-6160",
        unit="KG",
        category="油墨",
        on_hand_qty=500,
        reserved_qty=0,
        warehouse_id="W001",
        warehouse_name="原材料仓",
        factory_id="F001",
    ),
    # 与 DATA Fast / Text2SQL 返回的 JS-NZ-* 料号对齐（领料选型联调）
    MaterialRecord(
        material_code="JS-NZ-045",
        material_name="液态感光阻焊油墨",
        spec="",
        unit="KG",
        category="油墨",
        on_hand_qty=2420,
        reserved_qty=0,
        warehouse_id="W001",
        warehouse_name="原材料仓",
        factory_id="F001",
    ),
    MaterialRecord(
        material_code="JS-NZ-046",
        material_name="液态感光阻焊油墨",
        spec="",
        unit="KG",
        category="油墨",
        on_hand_qty=1720,
        reserved_qty=0,
        warehouse_id="W001",
        warehouse_name="原材料仓",
        factory_id="F001",
    ),
    MaterialRecord(
        material_code="JS-NZ-117",
        material_name="液态感光阻焊油墨",
        spec="",
        unit="KG",
        category="油墨",
        on_hand_qty=1460,
        reserved_qty=0,
        warehouse_id="W001",
        warehouse_name="原材料仓",
        factory_id="F001",
    ),
    MaterialRecord(
        material_code="JS-NZ-116",
        material_name="DI液态感光阻焊油墨",
        spec="",
        unit="KG",
        category="油墨",
        on_hand_qty=315,
        reserved_qty=0,
        warehouse_id="W001",
        warehouse_name="原材料仓",
        factory_id="F001",
    ),
    MaterialRecord(
        material_code="JS-NZ-109",
        material_name="液态感光阻焊油墨",
        spec="",
        unit="KG",
        category="油墨",
        on_hand_qty=290,
        reserved_qty=0,
        warehouse_id="W001",
        warehouse_name="原材料仓",
        factory_id="F001",
    ),
    MaterialRecord(
        material_code="JS-NZ-078",
        material_name="液态感光阻焊油墨",
        spec="",
        unit="KG",
        category="油墨",
        on_hand_qty=280,
        reserved_qty=0,
        warehouse_id="W001",
        warehouse_name="原材料仓",
        factory_id="F001",
    ),
    MaterialRecord(
        material_code="JS-NZ-085",
        material_name="液态感光阻焊油墨",
        spec="",
        unit="KG",
        category="油墨",
        on_hand_qty=280,
        reserved_qty=0,
        warehouse_id="W001",
        warehouse_name="原材料仓",
        factory_id="F001",
    ),
    MaterialRecord(
        material_code="JS-NZ-101",
        material_name="液态感光阻焊油墨",
        spec="",
        unit="KG",
        category="油墨",
        on_hand_qty=240,
        reserved_qty=0,
        warehouse_id="W001",
        warehouse_name="原材料仓",
        factory_id="F001",
    ),
    MaterialRecord(
        material_code="JS-NZ-040",
        material_name="液态感光阻焊油墨",
        spec="",
        unit="KG",
        category="油墨",
        on_hand_qty=220,
        reserved_qty=0,
        warehouse_id="W001",
        warehouse_name="原材料仓",
        factory_id="F001",
    ),
    MaterialRecord(
        material_code="JS-NZ-006",
        material_name="液态感光阻焊油墨",
        spec="",
        unit="KG",
        category="油墨",
        on_hand_qty=200,
        reserved_qty=0,
        warehouse_id="W001",
        warehouse_name="原材料仓",
        factory_id="F001",
    ),
    MaterialRecord(
        material_code="M002001",
        material_name="覆铜板",
        spec="1.2MM/1240*1035",
        unit="张",
        category="覆铜板",
        on_hand_qty=120,
        reserved_qty=10,
        warehouse_id="W001",
        warehouse_name="原材料仓",
        factory_id="F001",
    ),
    MaterialRecord(
        material_code="M003015",
        material_name="过硫酸钠",
        spec="工业级",
        unit="KG",
        category="化学用品",
        on_hand_qty=8,
        reserved_qty=2,
        warehouse_id="W001",
        warehouse_name="原材料仓",
        factory_id="F002",
    ),
    MaterialRecord(
        material_code="M004088",
        material_name="锡膏",
        spec="SAC305",
        unit="KG",
        category="锡膏",
        on_hand_qty=15,
        reserved_qty=0,
        warehouse_id="W001",
        warehouse_name="原材料仓",
        factory_id="F001",
    ),
]

# 联调测试用：提交领料会累加 reserved_qty，多次测试后可用量可能归零
SEED_INVENTORY: dict[str, tuple[float, float]] = {
    m.material_code: (m.on_hand_qty, m.reserved_qty) for m in MATERIALS
}


def reset_materials_inventory() -> list[dict[str, float]]:
    """将各物料库存恢复为 SEED_INVENTORY 初始值（不清草稿/单号）。"""
    result: list[dict[str, float]] = []
    for material in MATERIALS:
        on_hand, reserved = SEED_INVENTORY[material.material_code]
        material.on_hand_qty = on_hand
        material.reserved_qty = reserved
        result.append(
            {
                "material_code": material.material_code,
                "on_hand_qty": on_hand,
                "reserved_qty": reserved,
                "available_qty": max(on_hand - reserved, 0),
            }
        )
    return result


store = InMemoryStore()
