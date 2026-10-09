# Ro-Plasma-Setup

Ro-ASD-specific first-boot presentation and extensions for KDE Plasma Setup.
Upstream owns account creation, authentication, session handling and completion.

PR-01 defines the architecture. PR-02 adds an isolated development test harness;
there are no production Ro pages or replacement wizard.

- [Architecture decision and implementation gates](docs/ARCHITECTURE-PR-01.md)
- [Source findings and reproduction](docs/RESEARCH-PR-01.md)
- [Pinned research baseline](docs/research/baseline-2026-10-09.json)
- [Development harness, environment and test commands](docs/DEVELOPMENT-HARNESS.md)
- [PR-02 validation report](docs/validation/PR-02.md)

The proposal targets Fedora 44's `plasma-setup-6.7.5-1.fc44` and recommends a
separate customization package using documented KPackage pages first. Further
branding requires small upstream presentation hooks. The installer seed remains
`/var/lib/ro-asd/firstboot/installer-seed-v1.json`.
