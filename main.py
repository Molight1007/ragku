from __future__ import annotations

from rag_service import rag_answer


def main() -> None:
    print("本地知识库问答系统（基于阿里云通义千问 + RAG）")
    print("输入问题并回车，输入 q 或 quit 退出。")

    while True:
        query = input("\n请输入你的问题：").strip()
        if query.lower() in {"q", "quit", "exit"}:
            print("已退出。")
            break
        if not query:
            continue

        try:
            answer, contexts = rag_answer(query)
        except Exception as e:  # noqa: BLE001
            print(f"发生错误：{e}")
            continue

        print("\n===== 模型回答 =====")
        print(answer)

        print("\n===== 参考片段（用于比赛展示可解释性） =====")
        for idx, c in enumerate(contexts, start=1):
            print(f"\n[片段{idx}] 来源文件: {c.get('source', '')}")
            preview = c.get("text", "")
            if len(preview) > 200:
                preview = preview[:200] + "..."
            print(preview)


if __name__ == "__main__":
    main()

