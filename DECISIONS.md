# Decisions & Rationale

## Part 1 — Multi-document conversations

A conversation can now hold any number of documents. The data model already had a
one-to-many `Conversation → documents` relationship, so the "one document per
conversation" rule was an artificial limit enforced in three places (the upload
guard, the LLM call, and the routers that only read `documents[0]`). I removed
the guard, made the LLM prompt assemble **all** documents — each wrapped in a
`<document name="…">` tag so answers can span and attribute across files — and
rebuilt the viewer around a **document switcher** (one tab per file). The attach
button now always adds another document, and newly uploaded files are focused
automatically. Previously uploaded documents persist when new ones are added.

## Part 2 — Verifiable citations + an uncertainty signal

**The insight from the data.** I split the prioritisation between what users
*say* and what they *do*, and only one theme showed up strongly in both. In
`usage_events.csv`, when an AI response cited **0 sources, 80% of the feedback on
it was negative**; when it cited **≥1 source, only 18% was negative** (thumbs-down
answers averaged 2.28 citations vs 3.31 for thumbs-up). The full analysis —
including method and caveats — is reproducible in
[`analysis/`](./analysis/ANALYSIS.md) (`python analysis/usage_analysis.py`). That behavioural signal
lines up exactly with the loudest, most senior qualitative feedback — four of the
nine interview quotes are about trust/citations, and they're the ones from
**partners**, framed in money and liability terms ("£40M acquisition", *"I'd pay
double if it would just tell me when it's not sure"*, *"confidently wrong is
worse than being slow"*). Every other theme (export, annotation, ctrl-F) is a
single anecdote about convenience with no behavioural signal behind it.

**Why this over the alternatives.** The 0-citation → negative correlation is best
read as a *proxy for groundedness*: when the answer genuinely is in the document
the model has something concrete to cite and is right; when it isn't, the model
fills the gap and fabricates — which is precisely what lawyers punish. So the fix
isn't "cite more," it's **make groundedness visible**: show *where* a claim comes
from when it's grounded, and *say so* when it isn't. Those are two halves of one
feature, which is why I built them together. Crucially, the citations are
**verified, not just displayed** — the model returns each claim with a verbatim
quote, and the backend checks that quote actually exists in the source text
before trusting it, deriving the real page number from the document's page
markers. A quote it can't find is shown as **"unverified"** rather than as a
confident link. That directly attacks the scariest complaint in the feedback
("cited a clause that doesn't exist"): the product now catches that case instead
of presenting it as fact. Clicking a verified citation jumps the reader straight
to the page — the "magic" moment one associate described — which also removes the
"I have to go find it myself anyway" objection.

**One caveat I want to be honest about.** I tested whether bad answers *drive
people away* and the data does **not** support it — users who received a
0-citation answer actually had *more* sessions (2.21 vs 1.71), a selection effect
because heavier users ask more questions and so hit more uncited answers. So I
make no retention claim; the defensible claim is about *trust and answer quality
per interaction*, which is what partners said determines whether they adopt the
tool at all.

## What I'd do next with more time

- **Highlight the cited passage in the viewer**, not just jump to the page —
  anchor the quote's character range and scroll/flash it. This also sets up the
  "annotation/highlighting" request from the feedback.
- **Retrieval for large/long documents.** Today the full text of every document
  is sent in the prompt; on a real due-diligence deal (dozens of long PDFs) that
  won't fit. I'd chunk + embed and retrieve the relevant passages, which also
  makes citations more precise.
- **Cross-document comparison view** (the Firm F request) — now cheap to build on
  top of multi-doc + structured citations: ask one question, render each
  document's answer + citation side by side.
- **Report export** with the verified citations attached, turning the trust
  feature into the client deliverable users are currently copy-pasting by hand.
- **Tighten the citation contract** with a typed/structured-output API call and a
  small eval set scoring grounded-accuracy and citation-verification rate, so the
  trust feature can be regression-tested rather than eyeballed.
