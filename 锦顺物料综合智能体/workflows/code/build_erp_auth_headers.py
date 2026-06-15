"""
Dify Code：组装 erp_* HTTP 请求头（Authorization 由画布绑定，不交给 LLM）。

输入：
  - auth_token: string  conversation.auth_token

输出：
  - authorization: string  供 HTTP Header Authorization
  - ngrok_skip: string     固定 "true"
"""


def main(auth_token: str) -> dict:
    token = str(auth_token or "").strip()
    if token.lower().startswith("bearer "):
        auth = token
    elif token:
        auth = f"Bearer {token}"
    else:
        auth = ""
    return {"authorization": auth, "ngrok_skip": "true"}
