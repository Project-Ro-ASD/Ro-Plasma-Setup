# Ro-Plasma-Setup

Ro-ASD-specific first-boot presentation and extensions for KDE Plasma Setup.
Upstream owns account creation, authentication, session handling and completion.

PR-01 is an architecture gate; this repository does not implement a wizard yet.

- [Architecture decision and implementation gates](docs/ARCHITECTURE-PR-01.md)
- [Source findings and reproduction](docs/RESEARCH-PR-01.md)
- [Pinned research baseline](docs/research/baseline-2026-10-09.json)

The proposal targets Fedora 44's `plasma-setup-6.7.5-1.fc44` and recommends a
separate customization package using documented KPackage pages first. Further
branding requires small upstream presentation hooks. The installer seed remains
`/var/lib/ro-asd/firstboot/installer-seed-v1.json`.
