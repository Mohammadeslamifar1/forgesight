# Security scope

ForgeSight is a local research application, not an authenticated shared service. Keep the default loopback listener. See [architecture](docs/ARCHITECTURE.md) for the implemented protections and remaining boundaries.

For a sensitive vulnerability, use [GitHub private vulnerability reporting](https://github.com/Mohammadeslamifar1/forgesight/security/advisories/new). Remove private images, local paths, and credentials from reproduction steps. Do not publish sensitive exploit details or private data in a public issue.

The application does not send inspection images to external AI services. Initial dataset and pretrained-weight downloads are network operations. Local SQLite records are not cryptographically tamper-proof.
