# Beta Usage Analysis

The evidence behind the roadmap decisions. Everything here is reproduced by:

```bash
python analysis/usage_analysis.py
```

**Dataset:** `data/usage_events.csv` — 1,088 events, 50 users, 115 conversations
from the 3-week beta. It's an *event log*: one row per event (`session_start`,
`conversation_created`, `document_uploaded`, `prompt_submitted`,
`response_received`, `feedback_given`, `session_end`), not one row per answer.

---

## Finding 1 — Citations are the trust lever (drove Part 2)

**Question:** do answers that cite the document get better feedback?

**Method:** citation counts (`sources_cited`) and ratings (`feedback`) live on
*separate* event rows, so I link each `feedback_given` to the most recent
`response_received` in the same `conversation_id` (one sorted pass, carrying the
last citation count forward), then split the rated answers by 0 vs 1+ citations.

| Answer cited… | Thumbs-down rate |
| --- | --- |
| **0 sources** | **80%** (8 / 10) |
| **1+ sources** | **18%** (17 / 92) |

Same model, same users — whether the answer pointed to the document is the single
biggest swing in satisfaction. This lines up with the loudest qualitative
feedback, which came from **partners** (the budget holders / liability owners):
*"I'd pay double if it would just tell me when it's not sure"*, *"confidently
wrong is worse than being slow"*.

**Caveats:** the link is a heuristic (no explicit feedback→message id; inferred
from timing). The 0-citation bucket is small (n=10), so 80% is *directional* — but
the effect size is large enough to act on.

---

## Finding 2 — The same document is re-uploaded across chats (validates Part 1)

**Method:** group `document_uploaded` events by `document_hash` and count how many
distinct conversations each document appears in.

| Document | Separate conversations it was uploaded into |
| --- | --- |
| Headlease – 100 Bishopsgate.pdf | **12** |
| Title Report – Lot 7 Victoria Park.pdf | 8 |
| Property Certificate – Leeds Civic Quarter.pdf | 6 |
| Environmental Phase I – Manchester Arndale.pdf | 5 |
| Rent Review Memorandum – Unit 4B.pdf | 5 |

Only 15 unique documents exist, but the top one was re-uploaded into **12
separate conversations**. Users re-upload the same file chat after chat because a
conversation only held one document — exactly the *"the tool should just remember
my documents"* complaint. Validates multi-document conversations (Part 1).

---

## Finding 3 — Myth-bust: uncited answers do NOT visibly drive churn

**Tempting claim:** bad (uncited) answers drive users away. I tested it before
asserting it.

**Method:** split users by whether they ever received a 0-citation answer, and
compare engagement.

| Users | Avg sessions | Avg prompts |
| --- | --- | --- |
| Ever got a 0-citation answer (33) | **2.21** | **6.91** |
| Never did (17) | 1.71 | 4.35 |

The story is **not** supported — users who hit a 0-citation answer were *more*
active, not less. That's a selection effect: heavier users ask more questions, so
they encounter more uncited answers. So I make **no retention claim**; the
defensible claim is about **trust and answer quality per interaction**, which is
what partners said determines adoption at all.

*(Checking this — and dropping the claim — matters: it's the difference between a
data-driven decision and a just-so story dressed up with a number.)*
