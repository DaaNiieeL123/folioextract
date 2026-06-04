# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

We take the security of FolioExtract seriously. If you discover a security vulnerability, please follow the steps below.

### How to Report

1. **Do NOT open a public GitHub issue** for security vulnerabilities.
2. Send an email to [INSERT SECURITY EMAIL] with the subject line: `[SECURITY] FolioExtract - Brief Description`
3. Include the following in your report:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

### What to Expect

- **Acknowledgment**: You will receive an acknowledgment within 48 hours.
- **Updates**: We will provide status updates as we investigate and work on a fix.
- **Resolution**: Once the vulnerability is confirmed and fixed, we will:
  1. Release a patched version
  2. Publish a security advisory on GitHub
  3. Credit you (if you wish) in the advisory

### Responsible Disclosure

Please allow us reasonable time to address the vulnerability before disclosing it publicly. We aim to resolve confirmed vulnerabilities within 30 days.

## Security Considerations

FolioExtract is designed as a **local desktop application**. Keep in mind:

- The backend API binds to `127.0.0.1` (loopback) only by default. **Do not expose it to the network.**
- CORS is restricted to localhost origins. If you modify `FOLIOEXTRACT_CORS_ORIGINS`, ensure you understand the implications.
- Uploaded files are processed in a temporary directory (`temp_jobs/`) and cleaned up after conversion.
- The `/api/system/open` endpoint restricts path access to the output directory, app data directory, and user home directory.
- PowerShell automation (Windows DOCX conversion) validates file paths against injection characters.

## Scope

The following are in scope for security reports:

- Code execution vulnerabilities
- Path traversal or unauthorized file access
- Injection attacks (command injection, XSS, etc.)
- Denial of service via resource exhaustion
- Information disclosure

The following are **not** considered vulnerabilities:

- Issues in third-party dependencies (report to the upstream project)
- Attacks that require physical access to the user's machine
- Issues that only affect outdated/unsupported browser versions
