<!-- SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved. -->
<!-- SPDX-License-Identifier: Apache-2.0 -->

# Skills Generation Prompt

Generate or update skill files for users of this SDK/repository based on the current branch. The skills target Physical AI developers writing data converters that emit OpenUSD via the OpenUSD Exchange SDK.

## Context

- Source Docs: @docs/
- Source Headers: @include/
- Reference Samples: [OpenUSD Exchange Samples](https://github.com/NVIDIA-Omniverse/usd-exchange-samples). Generated skills must align with the concepts demonstrated there.

## Skill Set

Generate **exactly two skills**:

1. **`getting-started`** -- environment setup, installation, project layout, and a smoke test. Base it on [getting-started.md](../../docs/getting-started.md) and [native-application.md](../../docs/native-application.md). It must specifically prevent these recurring failures:
   - Agents trying to build `usd-exchange` themselves when the PyPI wheel is available.
   - Agents placing a new project inside the `usd-exchange` repository directory instead of in its own directory with its own venv.
2. **`usd-authoring`** -- authoring USD content with the OpenUSD Exchange SDK. This is **one** skill with one `SKILL.md` (overview + non-negotiables + reference index) plus topical reference files inside the same folder.

Do NOT split `usd-authoring` into multiple sibling skills. The trigger ("user is authoring USD via the OpenUSD Exchange SDK"), audience, and non-negotiables are shared across every domain, so it is one skill with topical references.

## Layout

```text
.agents/skills/
  getting-started/
    SKILL.md
  usd-authoring/
    SKILL.md
    references/
      <topic>.md ...
AGENTS.md                  (root; links to each skill with a one-line description)
```

Skills live at `<repo>/.agents/skills/<skill-name>/SKILL.md`. The `SKILL.md` filename and the `.agents/skills/` directory together form the auto-discovery convention used by Cursor and Anthropic Claude Skills. Other agents reach the content via the root `AGENTS.md`, which must link to every skill.

This layout intentionally differs from the [agentskills.io](https://agentskills.io) packaging convention, which places skills at `<repo>/skills/` or `<repo>/team-skills/`.

If it is absolutely necessary for Claude agents, add a root `CLAUDE.md` containing only `@AGENTS.md`. Otherwise omit it.

## Skill frontmatter (YAML)

Every `SKILL.md` begins with a YAML frontmatter block delimited by `---` lines on its own first line and the line immediately before the SPDX header (see **License headers**). The block must populate the following fields exactly:

```yaml
---
name: <skill-name>
description: <50-150 char description>
version: "<sdk-version>"
license: Apache-2.0
metadata:
  author: "NVIDIA Corporation"
  tags: [<tag1>, <tag2>, ...]
---
```

Field contract:

- **`name`** — required. Kebab-case identifier, 1-64 chars, must match the parent directory name exactly. Lowercase letters, digits, and hyphens only; must start with a letter; no consecutive or trailing hyphens; must not contain reserved words (`anthropic`, `claude`) or XML tags.
- **`description`** — required, **50-150 characters** total. Written in the third person (no "I", "you", "we", "your"). Must include both:
  - A WHEN-to-use phrase (`Use for…`, `Use when…`, `For…`, `Helps…`, `Allows…`).
  - At least one boundary phrase (`Do NOT use for…`, `Not for…`, `Except when…`) so the description carries a negative trigger and does not over-trigger on broad terms.
- **`version`** — required. Semantic version string in double quotes. **The skill version must match the target SDK release version**, derived from the first line of [`../../CHANGELOG.md`](../../CHANGELOG.md) (the top-most `# <semver>` header) **with any pre-release (`-…`) or build (`+…`) suffix stripped — keep only the `MAJOR.MINOR.PATCH` numeric core**. Examples: a heading of `# 2.3.0-rc1` → `version: "2.3.0"`; `# 2.4.0-alpha.2+build.7` → `version: "2.4.0"`; `# 2.3.0` → `version: "2.3.0"`. The skills version lock-steps with the SDK release line by *target* version, not by current pre-release tag, so a development checkout already shows the version the release will ship under and no regeneration is required at tag-cut time. Do not bump skills independently and do not invent a separate cadence. On every generation / update run, re-read the CHANGELOG header, strip the suffix, and overwrite the field if it has drifted.
- **`license`** — required; always the literal string `Apache-2.0` for this repo. Mirrors the SDK's own license and the SPDX license-identifier header that every generated file already carries in HTML-comment form. The body-level SPDX header is kept (it's what source-tree license-scanners read); the frontmatter `license:` slot is what skill-aware clients display.
- **`metadata.author`** — required (presence-only). The canonical value is the bare organization string `NVIDIA Corporation`. **The prompt must never hard-code an individual user's name or email here, and must not invent a project mailbox or alias.** A `Name <email@host>` shape is *recommended* but not enforced under the public validation profile (a non-email value such as `NVIDIA Corporation` produces a silent advisory-level finding only and does not block validation); the simpler organization name avoids planting a fictional mailbox in the published artifact.
- **`metadata.tags`** — required. A YAML list of 1-5 lowercase kebab-case categorization tags (for example `[openusd, usdex, physical-ai, converter]` for `usd-authoring`; `[openusd, usdex, getting-started, install]` for `getting-started`).

Forbidden frontmatter keys, which must never appear in any generated `SKILL.md`: `alwaysApply`, `globs`. These are rules-engine fields belonging to a different file type and break skill schema validation.

The frontmatter block itself must be the first content in the file (line 1 = `---`). The SPDX license header follows the closing `---` per the placement rules under **License headers**.

## License headers

Every file you create or update — `AGENTS.md`, `CLAUDE.md`, every `SKILL.md`, every `references/<topic>.md` — must carry an Apache-2.0 SPDX header that matches the rest of the repository. Markdown files use HTML comments so the header does not render. The two lines are exactly:

```
<!-- SPDX-FileCopyrightText: Copyright (c) <year> NVIDIA CORPORATION & AFFILIATES. All rights reserved. -->
<!-- SPDX-License-Identifier: Apache-2.0 -->
```

Placement:

- Files without YAML frontmatter (`AGENTS.md`, `CLAUDE.md`, every `references/<topic>.md`): the two SPDX lines are the first two lines of the file, followed by a blank line, followed by the first heading.
- Files with YAML frontmatter (`getting-started/SKILL.md`, `usd-authoring/SKILL.md`): the file **must** begin with `---` so the frontmatter parses. Place the two SPDX lines immediately after the closing `---` of the frontmatter, followed by a blank line, followed by the first heading.

Year handling: use the current year for newly-created files. When updating an existing file whose header has an older year, extend it to a range (e.g. `2025-2026`). Do not invent multi-year ranges for files you are creating from scratch.

## External documentation links

When a generated file links to NVIDIA Omniverse documentation under `https://docs.omniverse.nvidia.com/...`, **prefer the agent-friendly Markdown twin by appending `.md` to the `.html` path component.** Every HTML page on the Omniverse docs site is served as Markdown at the same path with `.md` appended; the Markdown form is cheaper for an agent to consume than the rendered HTML.

- HTML: `https://docs.omniverse.nvidia.com/usd/latest/learn-openusd/independent/asset-structure-principles.html`
- Markdown twin (preferred): `https://docs.omniverse.nvidia.com/usd/latest/learn-openusd/independent/asset-structure-principles.html.md`

For URLs with an anchor, append `.md` to the path *before* the `#`:

- `https://docs.omniverse.nvidia.com/materials-and-rendering/latest/materials.html#omnipbr` → `https://docs.omniverse.nvidia.com/materials-and-rendering/latest/materials.html.md#omnipbr`

This applies to every `docs.omniverse.nvidia.com` link in `AGENTS.md`, every `SKILL.md`, every `references/<topic>.md`, and any code-block comment that names such a URL. Non-Omniverse documentation hosts (e.g. `openusd.org`, `github.com`, `agentskills.io`) do not have this convention and must be linked as-is. The link-text portion of a markdown link should still read naturally — replace only the URL, not the human-facing label.

## Reference Decoupling Inside `usd-authoring`

Each domain becomes its own `<domain>.md` inside `.agents/skills/usd-authoring/references/` (note: the topical docs live in a `references/` subdirectory, not as `reference-*.md` siblings to `SKILL.md` — the validator's schema check expects siblings of `SKILL.md` to be one of `SKILL.md`, `README.md`, `references/`, `scripts/`, `assets/`, or `evals/` and flags anything else as an unexpected file). Use the C++ `@defgroup` sections in the headers as a loose guide for which domains to split. **Physics, lights, and cameras must each have their own reference file** -- never group them together (e.g. no "scene elements" reference).

`SKILL.md` itself is short: it states when to apply the skill, the non-negotiables below, and an index of the reference files. Agents should load only the reference files they need for the current task.

## Code-Sample Non-Negotiables

These rules apply to **every** code block in **every** generated file -- SKILL.md, every `references/<topic>.md`, every anti-pattern table that uses code (avoid that, see Brevity), examples in prose, etc. There is no "teaching" exception, no "illustrative" exception, and no "the example is about something else" exception. If the rule cannot be honored cleanly in a snippet, replace the snippet with a prose / table description of the API.

- Use `usdex.core.NameCache` or `usdex.core.getValidPrimName(s)` / `getValidChildName(s)` / `getValidPropertyName(s)` for **every** prim or property name shown -- including names the converter "owns" (asset names, scope names, default-prim names) and including throwaway example names. Do not use literal strings such as `"Foo"`, `"MyMesh"`, `"Clay"`, `"FlowerPlanter"`, `"main"`, `"World"`, etc. as `name=` arguments. Show `name=cache.getPrimName(parent, source.name)` or `defaultPrimName=usdex.core.getValidPrimName(asset.name)` instead.
- Use `usdex.core.createStage` rather than `Usd.Stage.CreateNew` / `Usd.Stage.CreateInMemory` + manual metadata.
- After `createStage`, promote the default prim from `Scope` to `Xform` via `usdex.core.defineXform(stage.GetDefaultPrim())` (or `defineXform(stage, stage.GetDefaultPrim().GetPath())`) whenever the resulting stage is intended to be referenced or placed.
- Use `usdex.core.saveStage` rather than `stage.Save()`. For single-layer work, use `saveLayer` / `exportLayer`.
- Use `usdex.core.setLocalTransform` (or pass a transform to `defineXform` / `defineCamera`) rather than raw `UsdGeomXformOp` writes or `UsdGeomXformCommonAPI`.
- Wrap every primvar (normals, UVs, widths, displayColor, displayOpacity, ids, custom) in the matching typed `*PrimvarData` alias (`Vec3fPrimvarData`, `Vec2fPrimvarData`, `FloatPrimvarData`, `Int64PrimvarData`, `IntPrimvarData`, `TokenPrimvarData`, `StringPrimvarData`) rather than authoring primvar attributes directly. **Do not write `usdex.core.PrimvarData` in Python prose or code** — `PrimvarData` is a C++ template (`usdex::core::PrimvarData<T>`) and is not a Python public symbol; Python only exposes the typed aliases. C++-targeted prose may name the bare template, but only when the C++ audience is explicit.
- Recommend supplying normals when using `definePolyMesh` calls, either source-provided (wrapped in `Vec3fPrimvarData`) or computed via `usdex.core.computeMeshNormals(faceVertexCounts, faceVertexIndices, points)` when the source data lacks them. Caveat that higher fidelity mesh operation libraries should be used over `computeMeshNormals` if they are available. Asset Validator's `NormalsExistChecker` rejects non-subdiv meshes without `primvars:normals`, so any canonical-flow demonstration, code block, or anti-pattern alternative that omits `normals=` produces an artifact that fails default validation.
- Use `usdex.core.defineReference` / `usdex.core.definePayload` rather than raw `prim.GetReferences().AddReference(...)` / `prim.GetPayloads().AddPayload(...)`.
- Use the matching `usdex.core.define...` / `usdex.rtx.define...` helper whenever one exists for the prim type being authored, rather than `Usd<Schema>.Define` plus attribute writes. Raw schema is allowed (and required) only for APIs with no helper -- for example `UsdPhysicsRigidBodyAPI.Apply`, `UsdPhysicsCollisionAPI.Apply`, `UsdPhysics.Scene.Define` -- and only **after** the prim was defined via the helper.
- Pass an `authoringMetadata` value (a variable, not a literal -- e.g. `AUTHORING_METADATA`) to `createStage` / `configureStage` / `saveStage` / `saveLayer` / `exportLayer` in every example that calls them.

### Self-audit before declaring done

After all files are written, search the generated files for the strings below. **Every** hit inside a code block must either be the right side of an anti-pattern comparison (which should be prose, not code -- see Brevity) or be fixed:

- `Usd.Stage.CreateNew`, `Usd.Stage.CreateInMemory`, `stage.Save()`
- `UsdGeomXformCommonAPI`, `AddTranslateOp`, `AddRotateOp`, `AddScaleOp`, `AddTransformOp`
- `GetReferences().AddReference`, `GetPayloads().AddPayload`
- `Tf.MakeValidIdentifier`, `TfMakeValidIdentifier`
- Literal `name="..."` / `name='...'` arguments to any `usdex.core.define*`, `usdex.rtx.define*`, `defineScope`, `createMaterial`, `getValidChildName`, `NameCache.getPrimName`, etc. Replace with `name=cache.getPrimName(parent, source_name)` (or similar) using a variable.
- Literal `defaultPrimName="..."` arguments to `createStage` / `configureStage`. Use `usdex.core.getValidPrimName(asset_name)`.
- Calls to `definePolyMesh` / `defineLinearBasisCurves` / `defineCubicBasisCurves` / `definePointCloud` whose `normals=` / `uvs=` / `widths=` / `displayColor=` / `displayOpacity=` / `ids=` arguments are not wrapped in `*PrimvarData`.
- `definePolyMesh(...)` calls without any `normals=` argument at all. Replace with a call that supplies `normals=` from source data (wrapped in `Vec3fPrimvarData`) or from `usdex.core.computeMeshNormals(...)`. Asset Validator's `NormalsExistChecker` will reject the generated stage otherwise.
- Code blocks (including the `getting-started/SKILL.md` smoke test) that call `createStage(...)` followed by `stage.GetDefaultPrim()` and then operate on the result without first running it through `defineXform(...)`. The default prim coming out of `createStage` is a `Scope`; the rule above mandates an explicit `Xform` promotion before any child Xforms are authored or before the stage is saved as a placeable artifact.
- Any `docs.omniverse.nvidia.com/...html` link in a generated file that is not followed by `.md` (or `.md#anchor`). Replace the `.html` portion with `.html.md` (preserving any trailing `#anchor`). The Markdown twin is the agent-friendly variant; the raw `.html` URL is a rendering of the same content for human browsers.

If any hit remains in code, fix or delete that snippet before reporting completion.

Also confirm every generated file begins with the two-line SPDX header described under **License headers** (after the YAML frontmatter for the two `SKILL.md` files, at line 1 for every other file). A missing or malformed header is a generation failure.

Frontmatter checks (apply to every `SKILL.md`):

- Every `SKILL.md` frontmatter has `name`, `description` (50-150 chars, third person, with a WHEN-to-use phrase and a `Do NOT use for…` / `Not for…` boundary phrase), `version` (semver string in quotes; must equal the *target* SDK version derived from the top `# <semver>` heading of `CHANGELOG.md` with any pre-release / build suffix stripped — i.e. only the `MAJOR.MINOR.PATCH` core; confirm by re-reading the changelog before declaring done), `license: Apache-2.0`, `metadata.author` (defaulting to `NVIDIA Corporation`), and `metadata.tags` (1-5 entries). A missing or empty field, or a `version` value whose `MAJOR.MINOR.PATCH` core does not match the changelog header, is a generation failure.
- `metadata.author` must not contain any individual user's name or email, and must not invent a project mailbox / alias. The canonical value is the bare organization string `NVIDIA Corporation`.
- No `alwaysApply` or `globs` keys appear in any `SKILL.md` frontmatter.

## Brevity

Skills are loaded into the agent's context every time the trigger fires. The cost we want to minimize is **consumption**, not generation. Therefore:

- The generation phase may use unlimited tokens. Read every relevant header in `@include/`, every doc in `@docs/`, and the [OpenUSD Exchange Samples](https://github.com/NVIDIA-Omniverse/usd-exchange-samples) thoroughly before authoring any skill.
- The generated skill files must be terse: dense factual content, short sentences, no preamble or recap, no marketing language, no "what is USD" tutorial content (assume the agent already knows OpenUSD and is consulting the skill for `usdex` specifics). Prefer tables and bullet lists over prose, and prose over code.
- `SKILL.md` is a thin index plus the non-negotiables. Detail belongs in `references/<topic>.md` files that load on demand.
- Each reference file covers one topic and assumes `SKILL.md` is already in context; do not restate the non-negotiables in every reference.

### Reference file length budget

Each `references/<topic>.md` targets **30-50 lines total** (including blank lines, table rows, and any code blocks). 60 is the absolute a ceiling; do not exceed it. If a reference is creeping past 50, the fix is almost always one of:

- Collapse multi-line prose paragraphs into a single sentence or fold them into the signature table's "Notes" column.
- Drop overload variants from the signature table (one row per function, list overload args inline as `(stage, path, ...)` / `(parent, name, ...)` / `(prim, ...)`).
- Move pattern code blocks to the topic where the pattern is most central and link from siblings.
- Trim anti-pattern tables to the 3-5 traps that actually bite; do not enumerate every possible misuse.
- Cut "background" sections (history, motivation, USD-version trivia) — they belong in `@docs/`, not in a reference loaded on every trigger fire.

`SKILL.md` files have no separate line budget but are governed by the existing rules: thin index, non-negotiables, no code (except the one smoke-test exception in `getting-started/SKILL.md`).

### Code-block budget

Code blocks are the most expensive content per byte and the easiest to over-produce. Treat them as scarce.

- **`SKILL.md` files (both skills): 0 code blocks** in the body. The trigger, non-negotiables, and reference index are prose / tables only. No "minimal end-to-end example", no canonical-flow code listing (a prose flow is fine), no quick-start snippet (the smoke test belongs in `getting-started/SKILL.md`, which is the one allowed exception -- one short script).
- **Each `references/<topic>.md`: at most 2 short code blocks, each ≤ ~15 lines.** Prefer a signatures-and-behavior table (function name, args, return, one-line note) over a code block. Reach for a code block only when calling pattern is genuinely non-obvious (e.g. multi-step composition with required ordering, like `definePreviewMaterial` -> `add*Texture` -> `addPreviewMaterialInterface`). If two reference files would otherwise show the same pattern, write it in one and link from the other.
- **Anti-pattern tables: prose comparisons only.** Format: `| Don't | Do |` with short text on each side (e.g. `Hard-coded "Foo" name` -> `cache.getPrimName(parent, source.name)`). Do not put fenced code blocks inside table cells.
- **No full-converter examples anywhere.** The samples repo (linked from `getting-started/SKILL.md`) is the place for end-to-end scripts. Skill samples should isolate one API.
- **No imports / boilerplate** in snippets unless the import itself is the point. Assume `import usdex.core`, `import usdex.rtx`, `from pxr import Gf, Sdf, Usd, UsdGeom, ...` are already in scope.

## Root `AGENTS.md`

The root `AGENTS.md` must contain:

- A one-paragraph "When this applies" trigger description: tasks that import `usdex.core` / `usdex.rtx` / `usdex.test` in Python, or include `<usdex/core/...>` / `<usdex/rtx/...>` / `<usdex/test/...>` in C++, or that author `Usd.Stage` / `Sdf.Layer` / `UsdPrim` / `UsdGeomMesh` / `UsdShadeMaterial` / `UsdLuxLight` / `UsdGeomCamera` / `UsdPhysics...` data.
- A bulleted list linking to each `<skill-name>/SKILL.md` with a one-line description.
- A "load only the references you need for the current task" instruction.

## Process

- If the skills files already exist, ask the user whether to update with complete verification or obliterate and recreate before doing anything else.
- If you are asked to obliterate it is literal. Delete the skills files, the AGENT.md, & start over from scratch. Do not intentionally follow patterns from previous runs.
- Do not add skills or notes for contributors -- `CONTRIBUTING.md` is sufficient.
