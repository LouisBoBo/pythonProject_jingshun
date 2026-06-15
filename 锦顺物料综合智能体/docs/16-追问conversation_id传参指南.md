# 追问 conversation_id 传参

> **已合并至** [17-主助手路由与传参一览.md](17-主助手路由与传参一览.md) §4、§5。  
> 本文保留作快捷跳转。

**要点**：

1. 传 **`data_analysis_conversation_id`**，不是 `sys.conversation_id`  
2. 主助手 **不判追问**；DATA 全走 Fast，**`build_chat_messages_body.py`** 有 id 就带  
3. 首问 Assigner 必须写入 uuid；追问才能带上  

代码：[`build_chat_messages_body.py`](../workflows/code/build_chat_messages_body.py)
