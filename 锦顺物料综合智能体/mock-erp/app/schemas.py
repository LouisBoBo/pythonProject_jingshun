from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    success: bool = False
    code: str
    message: str


class LoginRequest(BaseModel):
    username: str
    password: str


class UserInfo(BaseModel):
    user_id: str
    username: str
    name: str
    dept_id: str
    dept_name: str
    factory_id: str
    factory_name: str
    roles: list[str]


class LoginResponse(BaseModel):
    access_token: str
    expires_in: int = 7200
    token_type: str = "Bearer"
    user: UserInfo


class RefreshRequest(BaseModel):
    refresh_token: str | None = None


class MaterialItem(BaseModel):
    material_code: str
    material_name: str
    spec: str
    unit: str
    category: str


class MaterialSearchResponse(BaseModel):
    items: list[MaterialItem]
    total: int


class InventoryCheckResponse(BaseModel):
    material_code: str
    material_name: str
    unit: str
    available_qty: float
    on_hand_qty: float
    reserved_qty: float
    warehouse_name: str
    sufficient: bool


class DraftItem(BaseModel):
    material_code: str
    quantity: float
    unit: str | None = None


class DraftRequest(BaseModel):
    draft_id: str | None = None
    dept_id: str | None = None
    warehouse_id: str | None = None
    purpose: str = "生产补料"
    remark: str = ""
    items: list[DraftItem]


class DraftResponse(BaseModel):
    draft_id: str
    status: str
    summary: str


class SubmitRequest(BaseModel):
    draft_id: str
    idempotency_key: str | None = None


class SubmitResponse(BaseModel):
    success: bool = True
    requisition_no: str
    status: str
    message: str


class RequisitionItem(BaseModel):
    material_code: str
    material_name: str
    quantity: float
    unit: str


class RequisitionDetail(BaseModel):
    requisition_no: str
    status: str
    create_date: str
    applicant: str
    dept_name: str
    warehouse_name: str
    purpose: str
    remark: str
    items: list[RequisitionItem]
    audit_by: str | None = None
    audit_date: str | None = None


class RequisitionListResponse(BaseModel):
    items: list[RequisitionDetail]
    total: int
    page: int
    page_size: int
