# Security Policy

## Supported Versions

Ferricov is pre-alpha and has not published replacement binaries. Security
fixes currently target the latest revision of `main`; no stable release line is
supported yet.

## Reporting A Vulnerability

Do not open a public issue for a suspected vulnerability. Use GitHub's
**Report a vulnerability** action in the repository Security tab to start a
private security advisory.

Include the affected revision, environment, reproduction steps, expected
impact, and any suggested mitigation. Reports should avoid real credentials,
private source code, or coverage artifacts that contain sensitive paths.

The project will acknowledge a complete report within seven days and will
coordinate validation, remediation, disclosure, and credit through the private
advisory. Response times may change before the first stable release.

## Scope

Relevant issues include unsafe parsing or resource use of untrusted coverage
data, path traversal in generated reports, command injection through callbacks
or external tools, unintended source disclosure, and release artifact or build
provenance compromise.

Compatibility differences without a security impact should use the public
compatibility issue template instead.
