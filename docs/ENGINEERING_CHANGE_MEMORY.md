# Concise change summaries and engineering memory

Version 1.0.0. Canonical interpretation of GitHub issue 17.

## Review card

Every human-identified issue and every pull request begins with four sections. Each section contains at most two non-empty lines.

```markdown
## Problem statement
What outcome or user problem requires attention.

## Issue/change identified
What defect, gap or enhancement was observed.

## Root cause or opportunity rationale
The observable cause, or the current limitation and expected value for an enhancement.

## Key steps
The smallest implementation and validation path.
```

Do not fill the root-cause section with speculation. If diagnosis is incomplete, state the confirmed boundary and evidence still needed. For an enhancement, do not invent a bug; explain the present limitation or opportunity.

## Patch scope

A pull request may include one change or multiple closely related changes. A coherent patch has one outcome, compatible risk, shared acceptance criteria and one understandable rollback.

Split unrelated outcomes, independent migrations or changes with different approval boundaries. PR size alone does not determine coherence.

Detailed design, logs and migration steps belong in linked documents, tests or artifacts. The four-section card remains a fast review index.

## Learning from mistakes

When a technical failure is confirmed, store a compact lesson containing:

- observed symptom and affected boundary;
- root-cause category supported by evidence;
- corrective change and why it addresses the cause;
- prevention and applicable scope;
- regression test, validator or other evidence;
- first/last occurrence, recurrence count and relevant versions.

At a new task boundary, retrieve lessons matching the technology, workflow, contract and risk. Do not load the entire historical backlog into every prompt.

When a failure recurs, prefer converting the lesson into a deterministic control: a regression test, schema validation, linter, template constraint, admission check or architectural invariant. Improvement is fewer repeated errors and faster recovery, not a larger memory file.

## Security and privacy

Learning memory contains safe technical summaries, not hidden model reasoning, credentials, personal data, customer records or private exploit instructions. Security root causes use private vulnerability reporting; public PRs contain the minimum safe remediation summary.
