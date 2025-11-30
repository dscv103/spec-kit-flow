# Installation Reference - Monorepo Setup

This document explains how to install packages from the SpecKitFlow monorepo.

## Why the `#subdirectory` Syntax?

SpecKitFlow is a **monorepo** containing multiple packages:
- `src/specify_cli/` - The `specify` command for Spec-Driven Development
- `src/speckit_core/` - Shared library (installed as dependency)
- `src/speckit_flow/` - The `skf` command for parallel orchestration

When installing from a git repository with multiple packages, we use the `#subdirectory=` fragment to tell `uv` which package to install.

## Installation Commands

### Specify CLI

```bash
# Install
uv tool install specify-cli --from "git+https://github.com/dscv103/spec-kit-flow.git#subdirectory=src/specify_cli"

# Upgrade
uv tool install specify-cli --force --from "git+https://github.com/dscv103/spec-kit-flow.git#subdirectory=src/specify_cli"

# One-time use (no installation)
uvx --from "git+https://github.com/dscv103/spec-kit-flow.git#subdirectory=src/specify_cli" specify init my-project
```

### SpecKitFlow

```bash
# Install
uv tool install speckit-flow --from "git+https://github.com/dscv103/spec-kit-flow.git#subdirectory=src/speckit_flow"

# Upgrade
uv tool install speckit-flow --force --from "git+https://github.com/dscv103/spec-kit-flow.git#subdirectory=src/speckit_flow"

# One-time use (no installation)
uvx --from "git+https://github.com/dscv103/spec-kit-flow.git#subdirectory=src/speckit_flow" skf dag --visualize
```

## Local Development

For contributors working on the codebase:

```bash
# Clone the repository
git clone https://github.com/dscv103/spec-kit-flow.git
cd spec-kit-flow

# Install in editable mode
pip install -e src/specify_cli
pip install -e src/speckit_core
pip install -e src/speckit_flow

# Or use Hatch environment
hatch shell
```

## Troubleshooting

### Error: "Package name does not match install request"

This happens when you forget the `#subdirectory=` part:

```bash
# ❌ Wrong - tries to install root package
uv tool install specify-cli --from git+https://github.com/dscv103/spec-kit-flow.git

# ✅ Correct - specifies the subdirectory
uv tool install specify-cli --from "git+https://github.com/dscv103/spec-kit-flow.git#subdirectory=src/specify_cli"
```

### Installing from a Specific Branch

```bash
# Install from a feature branch
uv tool install specify-cli --from "git+https://github.com/dscv103/spec-kit-flow.git@feature-branch#subdirectory=src/specify_cli"
```

### Installing from a Specific Tag/Release

```bash
# Install from version tag
uv tool install specify-cli --from "git+https://github.com/dscv103/spec-kit-flow.git@v0.0.22#subdirectory=src/specify_cli"
```

## Template Downloads

When you run `specify init`, the CLI:
1. Contacts GitHub API: `https://api.github.com/repos/dscv103/spec-kit-flow/releases/latest`
2. Downloads template ZIPs from **your releases** (e.g., `spec-kit-template-copilot-sh-v0.0.22.zip`)
3. Extracts them to create the project structure

**Important**: Templates must be packaged and attached to GitHub releases for this to work!

## Next Steps

- See [local-development.md](local-development.md) for development workflow
- See [upgrade.md](upgrade.md) for upgrade instructions
- See [installation.md](installation.md) for full installation guide
