# Security Policy

## Reporting a vulnerability

Please do not open a public issue for a suspected vulnerability. Report it through a [private GitHub security advisory](https://github.com/LigsQt/HushMap/security/advisories/new) with a clear description, reproduction steps, affected version, and potential impact.

Reports involving device upload authentication, environment-variable handling, audio ingestion, or database configuration are especially helpful.

## Supported version

Security fixes are applied to the current `main` branch.

## Deployment guidance

Production deployments must set a non-development `APP_ENV`, configure strong `DEVICE_API_KEYS`, set a non-default database password, and keep `.env` files and database backups outside source control.

The unauthenticated device-upload bypass is local-development behavior only. It
requires both `APP_ENV=development` and
`ALLOW_UNAUTHENTICATED_DEVICE_UPLOADS=true`; non-development environments fail
closed when no device keys are configured.

AI summary generation is intentionally available to frontend users and is
bounded by a per-client frontend limit plus backend request and Gemini-call
limits. These in-memory limits apply per application process; multi-instance
deployments must enforce a shared quota at the gateway or another centralized
service. Trusted reverse-proxy deployments must configure adapter-node's
`ADDRESS_HEADER` and `XFF_DEPTH`, and the proxy must replace rather than append
untrusted forwarding headers. Deployments requiring private map or session data
must add application-level user authentication in front of the frontend and API
rather than treating these quotas as authorization.
