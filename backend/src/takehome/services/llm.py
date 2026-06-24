from __future__ import annotations

from collections.abc import AsyncIterator

from pydantic_ai import Agent

from takehome.config import settings  # noqa: F401 — triggers ANTHROPIC_API_KEY export

CITATION_MARKER = "<<<CITATIONS>>>"

agent = Agent(
    "anthropic:claude-haiku-4-5-20251001",
    system_prompt=(
        "You are a helpful legal document assistant for commercial real estate lawyers. "
        "You help lawyers review and understand documents during due diligence.\n\n"
        "IMPORTANT INSTRUCTIONS:\n"
        "- Answer questions based ONLY on the document content provided. Never use outside knowledge.\n"
        "- Be concise and precise. Lawyers value accuracy over verbosity.\n"
        "- When several documents are provided, attribute each fact to the document it came "
        "from, by name.\n"
        "- If the documents do not contain the answer, say so clearly and plainly. "
        "Do NOT fabricate clauses, figures, or sections — being wrong is worse than being unsure.\n\n"
        "CITATIONS (required):\n"
        f"After your prose answer, output a line containing EXACTLY `{CITATION_MARKER}` and then "
        "a single JSON object on the following lines, with this shape:\n"
        '{\n'
        '  "grounded": true | false,        // is the answer actually supported by the documents?\n'
        '  "confidence": "high" | "medium" | "low",\n'
        '  "citations": [\n'
        '    {\n'
        '      "document": "<exact filename of the source document>",\n'
        '      "quote": "<a short phrase copied VERBATIM, character-for-character, from that document>",\n'
        '      "label": "<optional 2-4 word description, e.g. \'break notice period\'>"\n'
        '    }\n'
        '  ]\n'
        '}\n'
        "Rules for citations:\n"
        "- Every factual claim you make about a document MUST be backed by a citation whose "
        "'quote' is copied EXACTLY from that document (do not paraphrase or normalise the quote — "
        "it is checked against the source text).\n"
        "- Keep each quote short (a sentence or clause), enough to locate the passage.\n"
        "- If the answer is not in the documents: set grounded=false, confidence=low, citations=[].\n"
        "- Use confidence 'low' when the documents only partially or indirectly address the question.\n"
        f"- The `{CITATION_MARKER}` line and JSON are mandatory on every response."
    ),
)


async def generate_title(user_message: str) -> str:
    """Generate a 3-5 word conversation title from the first user message."""
    result = await agent.run(
        f"Generate a concise 3-5 word title for a conversation that starts with: '{user_message}'. "
        "Return only the title, nothing else."
    )
    title = str(result.output).strip().strip('"').strip("'")
    # Truncate if too long
    if len(title) > 100:
        title = title[:97] + "..."
    return title


async def chat_with_document(
    user_message: str,
    documents: list[dict[str, str]],
    conversation_history: list[dict[str, str]],
) -> AsyncIterator[str]:
    """Stream a response to the user's message, yielding text chunks.

    ``documents`` is a list of ``{"filename": ..., "text": ...}`` dicts for every
    document in the conversation. The prompt labels each one so the model can
    answer questions that span multiple documents and attribute facts to the
    correct source.
    """
    # Build the full prompt with context
    prompt_parts: list[str] = []

    # Add document context if available
    if documents:
        filenames = ", ".join(f'"{d["filename"]}"' for d in documents)
        prompt_parts.append(
            f"The conversation has {len(documents)} uploaded document(s): {filenames}.\n"
            "Each document's full text is provided below, wrapped in a <document> tag "
            "whose 'name' attribute is the exact filename. When you answer, attribute "
            "facts to the specific document they came from by name.\n"
        )
        for d in documents:
            prompt_parts.append(
                f'<document name="{d["filename"]}">\n{d["text"]}\n</document>\n'
            )
    else:
        prompt_parts.append(
            "No document has been uploaded yet. If the user asks about a document, "
            "let them know they need to upload one first.\n"
        )

    # Add conversation history
    if conversation_history:
        prompt_parts.append("Previous conversation:\n")
        for msg in conversation_history:
            role = msg["role"]
            content = msg["content"]
            if role == "user":
                prompt_parts.append(f"User: {content}\n")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}\n")
        prompt_parts.append("\n")

    # Add the current user message
    prompt_parts.append(f"User: {user_message}")

    full_prompt = "\n".join(prompt_parts)

    async with agent.run_stream(full_prompt) as result:
        async for text in result.stream_text(delta=True):
            yield text
