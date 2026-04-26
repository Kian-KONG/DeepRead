from __future__ import annotations

from textwrap import dedent
from typing import List


# ------------------------------
# Agent loop helpers
# ------------------------------
def build_system_prompt(doc_index: DocIndex, tool_names: List[str], enable_reasoning: bool = True) -> str:
    overview = doc_index.overview()
    search_tools = [t for t in tool_names if ("search" in (t or "")) or ("retrieval" in (t or ""))]
    search_cmd = f"Use {', '.join(search_tools)}" if search_tools else "Search"

    constraints = [
        f"{search_cmd} to locate relevant nodes based on the directory.",
        "Answer strictly based on the provided corpus; do not fabricate.",
        "The hierarchical structure of documents is represented in the Directory Structure. Parsing errors may cause body text to be mistakenly treated as hierarchical elements (or headings), rendering the heading text inaccessible to search and reading tools. Please make reasonable inferences based on the structure and the content returned by the tool.",
        "Respond in the User's language; align queries with the Directory Structure.",
        "Usually, you need to think step by step and then call tools to locate or read, iterating in this way until you can answer the question.",
        "When calling tools, DO NOT write tool invocations in plain text. Use the structured tool call interface (tool_calls) only.",
    ]

    constraints_block = "\n".join(f"- {c}" for c in constraints)

    return dedent(
        f"""
        You are a documents assistant and will receive one or more documents
        structured as follows:
        `- (doc_id) [node_id] Title | paragraphs=Num | tokens=Num | children=[ID list]`.
        Use this structure and your available tools to answer the user's question.

        ## Guidelines
        {constraints_block}

        ## Directory Structure
        {overview}
        """
    ).strip()
