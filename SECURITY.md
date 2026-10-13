# Security scope

ForgeSight is a local research application, not an authenticated shared service. Keep the default loopback listener. See [architecture](docs/ARCHITECTURE.md) for the implemented protections and remaining boundaries.

Before reporting an issue publicly, remove private images, local paths, and any credentials from reproduction steps. For a sensitive vulnerability, use the repository owner's private reporting channel if one is configured; do not include exploit payloads or private data in a public issue.

The application does not send inspection images to external AI services. Initial dataset and pretrained-weight downloads are network operations. Local SQLite records are not cryptographically tamper-proof.
