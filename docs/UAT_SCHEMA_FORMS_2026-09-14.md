# Schema-driven record forms

## Problem statement
An administrator must be able to create or edit a governed record without guessing internal codes. Definitions and permitted choices must appear in the form.

## Issue identified
Hosted feedback creation rejected free-text authority and system-area values. The form did not expose the server's allowed choices.

## Root cause
The generic form inferred controls from example records instead of consuming the JSON Schema already returned by `/v1/schema`. Example values also obscured missing values and defaults.

## Key steps to fix
Use canonical schemas for enum selectors, defaults, required fields, nullable values, numeric limits and field descriptions. Preserve existing values and reuse idempotency keys for unchanged retries while preventing concurrent duplicate submissions.

## Acceptance and regression coverage
Regression tests exercise canonical schema choices, unknown versus false/zero, JSON parsing, constants, timestamps and duplicate-submit handling. A Python contract test keeps the browser fixture synchronized with registered server schemas.

## Release boundary
This is a frontend repair; it does not grant permissions, change server validation or approve publication. Hosted acceptance and the broader production readiness decision remain separate from passing unit tests.
