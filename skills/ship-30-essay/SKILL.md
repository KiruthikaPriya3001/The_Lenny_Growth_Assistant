---
name: ship-30-essay
description: >
  Generates approximately 1,250-word evidence-backed essays in the Ship 30 for 30 style.
  Inputs a user thesis/question plus retrieved transcript evidence and produces a
  publishable essay with hook, clear thesis, grounded body, and actionable takeaway.
---

# Ship 30 for 30 Essay Skill

## What This Skill Does

This skill transforms a user request and retrieved Lenny's Podcast/Newsletter evidence into
a ~1,250-word essay following Ship 30 for 30 principles.

## Source Reference

Ship 30 for 30 is a writing cohort created by Nicolas Cole and Dickie Bush.
The principles below are sourced from their publicly available guides:
- https://ship30for30.com (public homepage with methodology overview)
- Public posts and videos by Nicolas Cole and Dickie Bush on X/Twitter
- The "Atomic Essays" format: 250 words → full "digital essays" of 1,000-1,500 words

The implementation interprets these principles for growth/product content.

## Core Principles Applied

1. **Write for ONE specific reader** — not "practitioners" in general, but a specific PM with a specific problem
2. **Hook first** — the opening sentence must earn the reader's attention; never start with "In today's world..."
3. **One thesis, stated clearly** — by paragraph 2 the reader must know what they'll learn
4. **Evidence, not assertion** — every claim should trace to a retrieved source
5. **Skimmable structure** — headings, short paragraphs, selective bolding
6. **Actionable ending** — one concrete thing the reader can do *this week*

## Input Requirements

```
audience:       str   # who the essay is for (e.g., "early-stage founders")
user_request:   str   # what to write about (becomes the retrieval query)
tone:           str   # e.g., "conversational, evidence-backed"
thesis_hint:    str   # optional — override retrieval query
```

## Writing Workflow

1. **Retrieve evidence** — search knowledge base for relevant chunks (top 8)
2. **Assess sufficiency** — if <2 relevant sources, narrow thesis or disclose limitation
3. **Write hook** — open with a specific, relatable observation or bold claim
4. **State thesis** — one precise claim by paragraph 2
5. **Develop body** — section headings (##), grounded claims with [CHUNK:id] citations
6. **Avoid padding** — every paragraph earns its place
7. **Write takeaway** — one action the reader can take immediately
8. **Count words** — target 1,100–1,400 words; flag if <900 or >1,600
9. **Review citations** — remove any [CHUNK:id] not in retrieved set
10. **Label hypotheses** — anything beyond the transcript evidence: *(Hypothesis)*

## Output Requirements

- Title: specific and compelling (not generic)
- ~1,250 words (range: 1,100-1,400)
- Grounded factual claims only
- Valid [CHUNK:id] citations inline
- No fabricated anecdotes, quotes, or episode names
- Clear labeling of anything inferred: *(Hypothesis)*
- Sources section at the end with title, author, URL

## Failure Modes

| Situation | Response |
|-----------|----------|
| Insufficient evidence (<2 relevant chunks) | Narrow thesis, disclose limitation, write smaller essay |
| All evidence tangentially related | Write partial essay, note qualification |
| User asks to fabricate | Decline and explain why |
| LLM refuses topic | Return error with explanation |

## Tests

Run via `pytest backend/tests/test_backend.py -k "essay"`:
- Word count validation (target ± 20%)
- Title extraction from heading
- Citation validation (no unverified chunk IDs)
- Skill routing (intent classification correctly routes to essay)
