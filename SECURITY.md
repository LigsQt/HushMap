# Security Policy

## Reporting a vulnerability

Please do not open a public issue for a suspected vulnerability. Report it through a [private GitHub security advisory](https://github.com/LigsQt/HushMap/security/advisories/new) with a clear description, reproduction steps, affected version, and potential impact.

Reports involving device upload authentication, environment-variable handling, audio ingestion, or database configuration are especially helpful.

## Supported version

Security fixes are applied to the current `main` branch.

## Deployment guidance

Production deployments must set a non-development `APP_ENV`, configure strong `DEVICE_API_KEYS`, set a non-default database password, and keep `.env` files and database backups outside source control.
