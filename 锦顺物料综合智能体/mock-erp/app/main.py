from __future__ import annotations

from typing import Annotated, Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.schemas import (
    DraftRequest,
    DraftResponse,
    ErrorResponse,
    InventoryCheckResponse,
    LoginRequest,
    LoginResponse,
    MaterialItem,
    MaterialSearchResponse,
    RefreshRequest,
    RequisitionDetail,
    RequisitionItem,
    RequisitionListResponse,
    SubmitRequest,
    SubmitResponse,
    UserInfo,
)
from app.store import (
    MATERIALS,
    USERNAME_INDEX,
    DraftRecord,
    MaterialRecord,
    RequisitionRecord,
    UserRecord,
    reset_materials_inventory,
    store,
    utcnow,
)

API_PREFIX = "/api"

app = FastAPI(
    title="锦顺 ERP Mock API",
    description=(
        "模拟锦顺 ERP 登录与领料申请接口，供 Dify 综合智能体联调。\n\n"
        "**领料调用顺序**：login → search(可选) → inventory(必) → draft → 用户确认 → submit\n\n"
        "**数据分析**请使用 Dify Tool `query_material_data`，不走本服务。\n\n"
        "契约详见 docs/04-ERP-API对接规范.md"
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def error(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(code=code, message=message).model_dump(),
    )


def find_material_by_code(code: str) -> MaterialRecord | None:
    for item in MATERIALS:
        if item.material_code == code:
            return item
    return None


def search_materials(keyword: str) -> list[MaterialRecord]:
    key = keyword.strip().lower()
    if not key:
        return []
    results: list[MaterialRecord] = []
    for item in MATERIALS:
        haystack = " ".join(
            [
                item.material_code,
                item.material_name,
                item.spec,
                item.category,
            ]
        ).lower()
        if key in haystack:
            results.append(item)
    return results


def material_to_item(item: MaterialRecord) -> MaterialItem:
    return MaterialItem(
        material_code=item.material_code,
        material_name=item.material_name,
        spec=item.spec,
        unit=item.unit,
        category=item.category,
    )


def build_summary(items: list[dict[str, Any]], dept_name: str) -> str:
    parts: list[str] = []
    for row in items:
        material = find_material_by_code(row["material_code"])
        name = material.material_name if material else row["material_code"]
        parts.append(f"{name} × {row['quantity']} {row.get('unit') or (material.unit if material else '')}")
    return " · ".join(parts) + f" · {dept_name}"


def get_current_user(authorization: Annotated[str | None, Header()] = None) -> UserRecord:
    if not authorization:
        raise HTTPException(status_code=401, detail="缺少 Authorization 头")
    token = authorization.removeprefix("Bearer ").strip()
    user = store.get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="登录已过期或 token 无效")
    return user


@app.get("/health", summary="健康检查", tags=["系统"])
def health() -> dict[str, str]:
    """
    **用途**：确认 Mock ERP 服务是否在线。

    - 部署探活、本地启动自检
    - 不承载业务逻辑，无需鉴权
    - Dify 一般不配置为 Tool
    """
    return {"status": "ok", "service": "jingshun-mock-erp"}


@app.post(
    f"{API_PREFIX}/dev/reset-inventory",
    summary="重置物料库存（联调专用）",
    tags=["系统"],
)
def dev_reset_inventory() -> dict[str, Any]:
    """
    **用途**：多次 submit 后 reserved_qty 会占满可用量；本接口恢复为 seed 初始库存。

    无需鉴权，仅 Mock 环境使用。不清草稿与已提交单号。
    """
    items = reset_materials_inventory()
    return {"ok": True, "message": "库存已恢复为初始值", "materials": items}


@app.post(
    f"{API_PREFIX}/auth/login",
    response_model=LoginResponse,
    summary="用户登录",
    tags=["认证"],
)
def login(body: LoginRequest):
    """
    **用途**：验证工号/密码，签发访问令牌，返回用户身份与默认部门。

    **Dify Tool 名**：`erp_login`

    **何时调用**：
    - 用户说「登录 工号 密码」
    - 调用任何领料接口前发现未登录或返回 401

    **成功后**：将 `access_token` 写入会话变量 `auth_token`，`user` 写入 `user_profile`

    **无需** Authorization Header。
    """
    user = USERNAME_INDEX.get(body.username.strip())
    if not user or user.password != body.password:
        return error(401, "INVALID_CREDENTIALS", "用户名或密码错误")
    if user.disabled:
        return error(403, "ACCOUNT_DISABLED", "账号已禁用，请联系管理员")

    token_record = store.issue_token(user)
    return LoginResponse(
        access_token=token_record.token,
        expires_in=7200,
        user=UserInfo(
            user_id=user.user_id,
            username=user.username,
            name=user.name,
            dept_id=user.dept_id,
            dept_name=user.dept_name,
            factory_id=user.factory_id,
            factory_name=user.factory_name,
            roles=user.roles,
        ),
    )


@app.post(
    f"{API_PREFIX}/auth/refresh",
    response_model=LoginResponse,
    summary="刷新访问令牌",
    tags=["认证"],
)
def refresh(body: RefreshRequest, user: UserRecord = Depends(get_current_user)):
    """
    **用途**：在 token 即将过期时换取新 token，避免用户重复输入密码。

    **Dify Tool 名**：`erp_refresh`（可选，非必须）

    **何时调用**：业务接口返回 401 且确认是过期而非密码错误时；或门户 SSO 续期场景。

    **需要** Authorization: Bearer {旧 token}。
    """
    store.tokens = {k: v for k, v in store.tokens.items() if v.user_id != user.user_id}
    token_record = store.issue_token(user)
    return LoginResponse(
        access_token=token_record.token,
        expires_in=7200,
        user=UserInfo(
            user_id=user.user_id,
            username=user.username,
            name=user.name,
            dept_id=user.dept_id,
            dept_name=user.dept_name,
            factory_id=user.factory_id,
            factory_name=user.factory_name,
            roles=user.roles,
        ),
    )


@app.get(
    f"{API_PREFIX}/materials/search",
    response_model=MaterialSearchResponse,
    summary="物料检索",
    tags=["物料"],
)
def materials_search(
    keyword: str = Query(..., min_length=1, description="物料名、料号、规格、类别关键字"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=50, description="每页条数"),
    user: UserRecord = Depends(get_current_user),
):
    """
    **用途**：按关键字模糊搜索物料主数据，供用户选型或 Agent 解析料号。

    **Dify Tool 名**：`erp_search_material`

    **何时调用**：
    - 用户描述模糊，如「帮我领阻焊油墨」但未给料号
    - 同名/多规格物料需列出供用户选择

    **领料链位置**：search → **inventory** → draft → submit（本接口为第一步，料号明确时可跳过）
    """
    _ = user
    matched = search_materials(keyword)
    start = (page - 1) * page_size
    end = start + page_size
    page_items = [material_to_item(item) for item in matched[start:end]]
    return MaterialSearchResponse(items=page_items, total=len(matched))


@app.get(
    f"{API_PREFIX}/inventory/check",
    response_model=InventoryCheckResponse,
    summary="库存校验",
    tags=["物料"],
)
def inventory_check(
    material_code: str | None = Query(None, description="物料料号，与 material_keyword 二选一"),
    material_keyword: str | None = Query(None, description="物料关键字，取匹配第一条"),
    warehouse_id: str | None = Query(None, description="仓库 ID，可选"),
    factory_id: str | None = Query(None, description="工厂/事业部 ID，可选"),
    user: UserRecord = Depends(get_current_user),
):
    """
    **用途**：查询指定物料的现存量、可用量，判断能否满足领料数量。

    **Dify Tool 名**：`erp_check_inventory`

    **何时调用**：
    - 用户问「还有多少库存」「够领吗」
    - **创建草稿或提交前必调**（方案铁律）
    - 混合任务「先查库存再申请」

    **领料链位置**：search → **inventory** → draft → submit

    **注意**：库存口径以 ERP/Mock 为准，与 Text2SQL 数据分析可能略有差异。
    """
    material: MaterialRecord | None = None
    if material_code:
        material = find_material_by_code(material_code)
    elif material_keyword:
        matched = search_materials(material_keyword)
        material = matched[0] if matched else None
    else:
        return error(400, "INVALID_PARAMS", "material_code 与 material_keyword 至少提供一个")

    if not material:
        return error(404, "MATERIAL_NOT_FOUND", "未找到对应物料，请更换关键词后重试")

    if warehouse_id and material.warehouse_id != warehouse_id:
        return error(404, "MATERIAL_NOT_FOUND", "指定仓库下未找到该物料")

    if factory_id and material.factory_id != factory_id:
        return error(404, "MATERIAL_NOT_FOUND", "指定工厂下未找到该物料")

    available = max(material.on_hand_qty - material.reserved_qty, 0)
    return InventoryCheckResponse(
        material_code=material.material_code,
        material_name=material.material_name,
        unit=material.unit,
        available_qty=available,
        on_hand_qty=material.on_hand_qty,
        reserved_qty=material.reserved_qty,
        warehouse_name=material.warehouse_name,
        sufficient=available > 0,
    )


@app.post(
    f"{API_PREFIX}/requisition/draft",
    response_model=DraftResponse,
    summary="创建/更新领料草稿",
    tags=["领料"],
)
def save_draft(body: DraftRequest, user: UserRecord = Depends(get_current_user)):
    """
    **用途**：保存领料申请草稿（未进入审批），支持多轮修改数量、用途、明细行。

    **Dify Tool 名**：`erp_save_draft`

    **何时调用**：
    - 物料、数量、部门等已齐，但用户**尚未确认提交**
    - 用户说「改成 15KG」「加一行物料」时带原 `draft_id` 更新

    **领料链位置**：search → inventory → **draft** → [用户确认] → submit

    **禁止**：未经用户确认直接调用 submit；本接口不会扣减最终库存（submit 时才校验并占用）。
    """
    if not body.items:
        return error(400, "INVALID_PARAMS", "items 不能为空")

    dept_id = body.dept_id or user.dept_id
    warehouse_id = body.warehouse_id or user.warehouse_id

    normalized_items: list[dict[str, Any]] = []
    for item in body.items:
        material = find_material_by_code(item.material_code)
        if not material:
            return error(404, "MATERIAL_NOT_FOUND", f"物料不存在: {item.material_code}")
        normalized_items.append(
            {
                "material_code": item.material_code,
                "material_name": material.material_name,
                "quantity": item.quantity,
                "unit": item.unit or material.unit,
            }
        )

    if body.draft_id:
        draft = store.drafts.get(body.draft_id)
        if not draft or draft.user_id != user.user_id:
            return error(404, "DRAFT_EXPIRED", "草稿不存在或已过期，请重新创建")
        draft.dept_id = dept_id
        draft.warehouse_id = warehouse_id
        draft.purpose = body.purpose
        draft.remark = body.remark
        draft.items = normalized_items
        draft.updated_at = utcnow()
    else:
        draft_id = store.next_draft_id()
        store.drafts[draft_id] = DraftRecord(
            draft_id=draft_id,
            user_id=user.user_id,
            dept_id=dept_id,
            warehouse_id=warehouse_id,
            purpose=body.purpose,
            remark=body.remark,
            items=normalized_items,
        )
        body.draft_id = draft_id

    draft = store.drafts[body.draft_id]
    return DraftResponse(
        draft_id=draft.draft_id,
        status=draft.status,
        summary=build_summary(draft.items, user.dept_name),
    )


@app.post(
    f"{API_PREFIX}/requisition/submit",
    response_model=SubmitResponse,
    summary="提交领料审批",
    tags=["领料"],
)
def submit_requisition(body: SubmitRequest, user: UserRecord = Depends(get_current_user)):
    """
    **用途**：将草稿正式提交为领料单（出仓单），进入待审批状态，返回单号 GON 号。

    **Dify Tool 名**：`erp_submit_requisition`

    **何时调用**：
    - 用户明确回复「确认提交」「好的提交」等
    - 必须已有 `draft_id`

    **领料链位置**：… → draft → **用户确认** → **submit**

    **幂等**：同一 `idempotency_key` 重复提交返回同一单号，防止 Agent 连调两次产生重复单。

    **幂等**：同一 `idempotency_key` 重复提交返回同一单号，防止 Agent 连调两次产生重复单。

    **库存**：不在 submit 扣减/占用库存；够不够领由查数+确认卡片决定（见 doc22）。
    """
    if body.idempotency_key:
        existing_no = store.idempotency_map.get(body.idempotency_key)
        if existing_no:
            existing = store.requisitions[existing_no]
            return SubmitResponse(
                requisition_no=existing.requisition_no,
                status=existing.status,
                message="已提交，等待仓库审核",
            )

    draft = store.drafts.get(body.draft_id)
    if not draft or draft.user_id != user.user_id:
        return error(404, "DRAFT_EXPIRED", "草稿不存在或已过期，请重新创建")

    for row in draft.items:
        material = find_material_by_code(row["material_code"])
        if not material:
            return error(404, "MATERIAL_NOT_FOUND", f"物料不存在: {row['material_code']}")

    requisition_no = store.next_requisition_no()
    record = RequisitionRecord(
        requisition_no=requisition_no,
        draft_id=draft.draft_id,
        user_id=user.user_id,
        applicant=user.name,
        dept_id=draft.dept_id,
        dept_name=user.dept_name,
        warehouse_id=draft.warehouse_id,
        warehouse_name=user.warehouse_name,
        purpose=draft.purpose,
        remark=draft.remark,
        items=draft.items,
        status="PENDING_APPROVAL",
        create_date=utcnow(),
        idempotency_key=body.idempotency_key,
    )
    store.requisitions[requisition_no] = record
    if body.idempotency_key:
        store.idempotency_map[body.idempotency_key] = requisition_no

    draft.status = "SUBMITTED"
    return SubmitResponse(
        requisition_no=requisition_no,
        status="PENDING_APPROVAL",
        message="已提交，等待仓库审核",
    )


def to_requisition_detail(record: RequisitionRecord) -> RequisitionDetail:
    return RequisitionDetail(
        requisition_no=record.requisition_no,
        status=record.status,
        create_date=record.create_date.isoformat(),
        applicant=record.applicant,
        dept_name=record.dept_name,
        warehouse_name=record.warehouse_name,
        purpose=record.purpose,
        remark=record.remark,
        items=[
            RequisitionItem(
                material_code=row["material_code"],
                material_name=row["material_name"],
                quantity=row["quantity"],
                unit=row["unit"],
            )
            for row in record.items
        ],
        audit_by=record.audit_by,
        audit_date=record.audit_date.isoformat() if record.audit_date else None,
    )


@app.get(
    f"{API_PREFIX}/requisition/{{requisition_no}}",
    response_model=RequisitionDetail,
    summary="查询领料单详情",
    tags=["领料"],
)
def get_requisition(requisition_no: str, user: UserRecord = Depends(get_current_user)):
    """
    **用途**：按出仓单号查询单笔领料申请的状态、明细、申请人、审批信息。

    **Dify Tool 名**：`erp_get_requisition`

    **何时调用**：
    - 用户问「GON20260309001 到哪了」「这张单审批了吗」
    - 提交成功后用户要再看单号详情

    **与 list 区别**：本接口查**指定单号**；list 查**当前用户全部/筛选列表**。
    """
    record = store.requisitions.get(requisition_no)
    if not record or record.user_id != user.user_id:
        return error(404, "NOT_FOUND", "未找到对应领料单")
    return to_requisition_detail(record)


@app.get(
    f"{API_PREFIX}/requisition/list",
    response_model=RequisitionListResponse,
    summary="我的领料申请列表",
    tags=["领料"],
)
def list_requisitions(
    status: str | None = Query(None, description="按状态筛选，如 PENDING_APPROVAL"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    user: UserRecord = Depends(get_current_user),
):
    """
    **用途**：分页列出**当前登录用户**的领料申请，可按状态筛选。

    **Dify Tool 名**：`erp_list_requisition`（可选）

    **何时调用**：
    - 用户问「我最近的领料单」「有哪些待审批的申请」
    - 未提供具体单号时的泛查询

    **与 get 区别**：list 为列表；get 为单笔详情。
    """
    records = [item for item in store.requisitions.values() if item.user_id == user.user_id]
    if status:
        records = [item for item in records if item.status == status]
    records.sort(key=lambda item: item.create_date, reverse=True)
    start = (page - 1) * page_size
    end = start + page_size
    page_items = [to_requisition_detail(item) for item in records[start:end]]
    return RequisitionListResponse(
        items=page_items,
        total=len(records),
        page=page,
        page_size=page_size,
    )


@app.get("/", summary="服务信息", tags=["系统"])
def root() -> dict[str, Any]:
    """
    **用途**：返回 Mock 服务说明、文档入口、测试账号（便于人工排查）。

    Dify 不配置为 Tool。
    """
    return {
        "service": "jingshun-mock-erp",
        "docs": "/docs",
        "openapi": "/openapi.json",
        "base_url_for_dify": "http://<host>:8900/api",
        "test_users": [
            {"username": "zhangsan", "password": "123456", "dept": "高精密事业部"},
            {"username": "lisi", "password": "123456", "dept": "单面事业部"},
        ],
    }
