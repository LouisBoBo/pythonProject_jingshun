"""
Dify Code 节点：组装 erp_login HTTP Body，避免 password 被 Dify 插值成 JSON 数字。

输入：
  - username: string
  - password: string  必须是字符串，如 "123456"

输出：
  - body_json: string  可直接作为 HTTP Body（raw JSON）
"""


def main(username: str, password: str) -> dict:
    import json

    body = {
        "username": str(username or "").strip(),
        "password": str(password or "").strip(),
    }
    return {"body_json": json.dumps(body, ensure_ascii=False)}
