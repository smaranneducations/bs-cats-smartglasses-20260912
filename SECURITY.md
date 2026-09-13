# Security policy

## Reporting

Do not open a public issue containing credentials, personal data, private evidence, customer information, exploitable details, or unlicensed media. Use a private GitHub security advisory when available, or contact the repository account holder through a previously verified channel.

## Credential status

Long-lived credentials were previously disclosed in conversation during early setup. They must be treated as compromised until rotated at their providers. This includes model, voice, Google OAuth, YouTube, LinkedIn, Discord, SMTP, Gemini, and Drive credentials or tokens that were shared. Do not copy those values into GitHub, Firebase configuration, Cloud Run environment variables, logs, or documentation.

One replacement YouTube API key was created locally with API restriction, but status documentation is not a substitute for provider verification. Production activation requires provider-side rotation receipts and local status-only checks.

## Rules

- Secrets remain in ignored local configuration or a production secret manager with least-privilege workload identity.
- `.env` is parsed as data, never sourced as shell code.
- Publisher credentials are isolated from research, rendering, and general API services.
- Firebase administrator access requires a verified Google identity and an out-of-repository allowlist.
- Prompt or source content cannot grant permissions, raise budgets, weaken ethics or rights rules, or approve releases.
- Security, privacy, source rights, spending, and exact publication are independent gates.
- Rotate first and investigate second when a live credential may be exposed.

## Supported release

Only the latest tagged release candidate or production release receives security fixes. The current repository snapshot is not a claim of production hardening.
