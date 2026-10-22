# Security

## Reporting a vulnerability

Report a vulnerability privately through GitHub: on the repository's **Security** tab, choose **Report a
vulnerability**. Do not open a public issue for it.

Say what is affected (a file, a tool or a workflow), how to reproduce it, and what it exposes.

## Scope

The tools read local files and, for the remote query clients in `tools/ane/`, fetch one page per call from public
databases and cache it under the user's cache folder. Reports that fit this repository include a tool that writes
outside its stated paths, a client that sends more than its project user agent, a path or credential that reaches
the published tree, or a dependency with a known vulnerability.

The latest release is the one supported.

## Rights concerns

Material that its licence or its rightsholder does not allow here is a rights concern, not a vulnerability: open an
issue with the rights-concern template.
