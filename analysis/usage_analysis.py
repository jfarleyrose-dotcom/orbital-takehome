"""Beta usage analysis — the evidence behind the Part 2 feature choice.

Run from anywhere:

    python analysis/usage_analysis.py

Reads ../data/usage_events.csv and reproduces the three findings that drove the
roadmap decision. Standard library only — no dependencies.

The CSV is an *event log*: one row per event, not one row per answer. The columns
that matter here:
    event_type      session_start | conversation_created | document_uploaded
                    | prompt_submitted | response_received | feedback_given | session_end
    conversation_id groups events within a single chat
    sources_cited   only on `response_received` rows — how many citations the answer had
    feedback        only on `feedback_given` rows — thumbs_up | thumbs_down
    document_hash   stable id for a document; same file re-uploaded shares a hash
"""

from __future__ import annotations

import collections
import csv
from pathlib import Path

CSV_PATH = Path(__file__).resolve().parent.parent / "data" / "usage_events.csv"


def load_rows() -> list[dict[str, str]]:
    with CSV_PATH.open() as f:
        rows = list(csv.DictReader(f))
    rows.sort(key=lambda r: r["timestamp"])  # chronological order
    return rows


def _rule(title: str) -> None:
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


# --------------------------------------------------------------------------- #
# Finding 1 — Citations are the trust lever
# --------------------------------------------------------------------------- #
def citations_vs_feedback(rows: list[dict[str, str]]) -> None:
    """Do answers that cite sources get better feedback?

    Feedback and citation-count live on separate rows, so we link each
    `feedback_given` to the most recent `response_received` in the same
    conversation (one sorted pass, carrying the last citation count forward),
    then split by 0 vs 1+ citations and compare the thumbs-down rate.
    """
    _rule("FINDING 1 — Citations are the trust lever")

    last_citation_count: dict[str, int] = {}
    pairs: list[tuple[int, str]] = []  # (citations_of_rated_answer, feedback)

    for r in rows:
        conv = r["conversation_id"]
        if r["event_type"] == "response_received":
            last_citation_count[conv] = int(r["sources_cited"] or 0)
        elif r["event_type"] == "feedback_given" and conv in last_citation_count:
            pairs.append((last_citation_count[conv], r["feedback"]))

    def neg_rate(bucket: list[str]) -> str:
        down = bucket.count("thumbs_down")
        n = len(bucket)
        return f"{down}/{n} negative = {down / n * 100:.0f}%" if n else "n/a"

    zero = [fb for sc, fb in pairs if sc == 0]
    some = [fb for sc, fb in pairs if sc >= 1]

    print(f"Rated answers linked to a response: {len(pairs)}")
    print(f"  Answer cited 0 sources : {neg_rate(zero)}")
    print(f"  Answer cited 1+ sources: {neg_rate(some)}")
    print(
        "\n  -> Same model, same users. Whether the answer pointed to the document\n"
        "     is the single biggest swing in satisfaction. (0-cite bucket is small,\n"
        "     n={}, so the rate is directional — but the effect size is large.)".format(
            len(zero)
        )
    )


# --------------------------------------------------------------------------- #
# Finding 2 — Re-uploading the same document (validates multi-document)
# --------------------------------------------------------------------------- #
def reupload_pain(rows: list[dict[str, str]]) -> None:
    """How often is the SAME document re-uploaded across different conversations?"""
    _rule("FINDING 2 — The same document is re-uploaded across many chats")

    convs_by_doc: dict[str, set[str]] = collections.defaultdict(set)
    name_by_doc: dict[str, str] = {}
    for r in rows:
        if r["event_type"] == "document_uploaded":
            convs_by_doc[r["document_hash"]].add(r["conversation_id"])
            name_by_doc[r["document_hash"]] = r["document_name"]

    ranked = sorted(convs_by_doc.items(), key=lambda kv: -len(kv[1]))
    print(f"Unique documents: {len(convs_by_doc)}")
    print("Most re-uploaded (document -> number of separate conversations):")
    for doc_hash, convs in ranked[:5]:
        print(f"  {len(convs):>2}x  {name_by_doc[doc_hash]}")
    print(
        "\n  -> Users re-upload the same file into chat after chat because a\n"
        "     conversation only held one document. Validates multi-document (Part 1)."
    )


# --------------------------------------------------------------------------- #
# Finding 3 — The retention story the data does NOT support
# --------------------------------------------------------------------------- #
def retention_myth_check(rows: list[dict[str, str]]) -> None:
    """Tempting claim: bad (uncited) answers drive users away. Test it."""
    _rule("FINDING 3 — Myth-bust: uncited answers do NOT visibly drive churn")

    sessions: dict[str, set[str]] = collections.defaultdict(set)
    prompts: dict[str, int] = collections.defaultdict(int)
    hit_zero: dict[str, bool] = collections.defaultdict(bool)

    for r in rows:
        u = r["user_id"]
        sessions[u].add(r["session_id"])
        if r["event_type"] == "prompt_submitted":
            prompts[u] += 1
        if r["event_type"] == "response_received" and int(r["sources_cited"] or 0) == 0:
            hit_zero[u] = True

    def mean(values: list[float]) -> float:
        return sum(values) / len(values) if values else 0.0

    got_zero = [u for u in sessions if hit_zero[u]]
    never = [u for u in sessions if not hit_zero[u]]

    sess_zero = mean([len(sessions[u]) for u in got_zero])
    sess_never = mean([len(sessions[u]) for u in never])
    prompts_zero = mean([prompts[u] for u in got_zero])
    prompts_never = mean([prompts[u] for u in never])

    print(f"Users who ever got a 0-citation answer: {len(got_zero)} | never: {len(never)}")
    print(f"  avg sessions  — got-zero: {sess_zero:.2f}  vs never: {sess_never:.2f}")
    print(f"  avg prompts   — got-zero: {prompts_zero:.2f}  vs never: {prompts_never:.2f}")
    print(
        "\n  -> The 'bad answers cause churn' story is NOT supported: users who hit a\n"
        "     0-cite answer were actually MORE active (a selection effect — heavier\n"
        "     users ask more, so they hit more uncited answers). So I make no\n"
        "     retention claim; the defensible claim is trust/quality per interaction."
    )


def main() -> None:
    rows = load_rows()
    print(f"Loaded {len(rows)} events from {CSV_PATH.name}")
    print(
        f"({len({r['user_id'] for r in rows})} users, "
        f"{len({r['conversation_id'] for r in rows if r['conversation_id']})} conversations)"
    )
    citations_vs_feedback(rows)
    reupload_pain(rows)
    retention_myth_check(rows)


if __name__ == "__main__":
    main()
