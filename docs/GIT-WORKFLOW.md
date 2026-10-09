# Git Workflow: commit messages and the flow, every time

**Prerequisites:** [`01-setup.md`](01-setup.md), the repository cloned, three
branches on the remote, the safety gate working.

**Learning goal:** you will know exactly what to type after *any* change to this
project, which commit message to write, in what order to run the commands, and
what to do when something goes wrong. You will also understand *why* each step is
there, so you can adapt it rather than copy it blindly.

**How to use this document:** keep it open in a tab. Find the row for what you
just did, take the message, run the flow. That's it.

> Every term here is also in [`GLOSSARY.md`](GLOSSARY.md).

---

## Contents

1. [The flow, in one block](#1-the-flow-in-one-block)
2. [What each line actually does](#2-what-each-line-actually-does)
3. [Why the order matters](#3-why-the-order-matters)
4. [How to write a commit message](#4-how-to-write-a-commit-message)
5. [The message for every phase](#5-the-message-for-every-phase)
6. [Messages for the changes in between](#6-messages-for-the-changes-in-between)
7. [One change, one commit](#7-one-change-one-commit)
8. [Tags: marking a release](#8-tags-marking-a-release)
9. [When something goes wrong](#9-when-something-goes-wrong)
10. [The quick reference card](#10-the-quick-reference-card)
11. [Checkpoint](#11-checkpoint)

---

## 1. The flow, in one block

**This is the whole thing.** Every change to this project ends with exactly these
commands.

```bash
# 1. Make sure you're on the working branch
git switch develop

# 2. Stage everything that changed
git add -A

# 3. Check nothing secret or huge is about to be published
./check-public-safe.sh        # must print "SAFE TO PUSH"
                              # Windows: bash check-public-safe.sh

# 4. (From Phase 1 onward) run the tests
pytest -q

# 5. Save the snapshot with a message describing WHY
git commit -m "type: what changed and why"

# 6. Publish to all three branches at once
git push origin develop develop:beta develop:master

## --tags is optional, and only when cutting a new version

# 7. Bring your local master back in step with the remote
git switch master
git pull --ff-only origin master
git switch develop
```

Seven steps. You will have them memorised by about the third phase.

*Everyday parallel:* the routine for leaving the house, keys, wallet, phone,
lock the door. You don't think about it after a while, and the one time you skip
a step is the one time it matters.

---

## 2. What each line actually does

Understanding this means you can adapt the flow instead of being stuck when
something differs.

### `git switch develop`

Moves you to the `develop` branch. **All work happens here**, `master` is the
published version and you never edit it directly.

*Everyday parallel:* opening your working draft rather than the printed copy on
the shelf.

If you were already on `develop`, Git says "Already on 'develop'" and does
nothing. Running it anyway costs nothing and prevents the classic mistake of
committing to the wrong branch.

### `git add -A`

**Staging**: choosing what goes into the next snapshot. `-A` means "everything
that changed, including new and deleted files."

*Everyday parallel:* putting items in a shopping basket. Nothing is bought yet;
you're deciding what's included in this trip.

### `./check-public-safe.sh`

The safety gate. Checks that no secret, no database, no huge folder is about to
be published. **Must print `SAFE TO PUSH`.**

If it doesn't, it names the problem. Take the offending file back out of the
basket and fix it:

```bash
git restore --staged path/to/file      # unstage, file stays on disk
```

### `pytest -q`

Runs the automated tests. `-q` means "quiet", just the summary line. Nothing to
run before Phase 1, so skip it until then.

*Everyday parallel:* tasting the sauce before serving.

### `git commit -m "..."`

Takes everything in the basket and saves it permanently as one snapshot, with your
message attached. This is a **local** action, nothing has left your machine yet.

### `git push origin develop develop:beta develop:master`

Sends the commit to GitHub, updating **three branches from one command**:

| Piece | Meaning |
|---|---|
| `origin` | Send to GitHub |
| `develop` | Update remote `develop` from local `develop` |
| `develop:beta` | Also update remote `beta` from local `develop` |
| `develop:master` | Also update remote `master` from local `develop` |

The colon reads "from local **X**, into remote **Y**".

Success looks like three lines at the end:

```
   b9c3295..d9f81cd  develop -> beta
   b9c3295..d9f81cd  develop -> develop
   b9c3295..d9f81cd  develop -> master
```

Same commit hash on all three. They are in lock-step.

### The `master` sync-back

```bash
git switch master
git pull --ff-only origin master
git switch develop
```

The push updated **GitHub's** `master`. Your **laptop's** `master` doesn't know
yet. Without this, local `master` drifts further behind every phase until one day
it confuses you badly.

`--ff-only` means *"update only if it's a clean fast-forward, otherwise stop and
tell me."* Since you never commit to local `master`, it is always clean, and Git
just moves the pointer forward.

*Everyday parallel:* you posted the updated document to two colleagues. This is
you updating your own filing cabinet so your copy matches what you sent.

---

## 3. Why the order matters

Two orderings in that block are deliberate, and both were mistakes I made and
corrected. Worth knowing so you don't reintroduce them.

### Stage *before* the safety gate

The gate inspects what Git is **tracking** (`git ls-files`). A brand-new file that
has never been staged is invisible to Git, and therefore invisible to the gate.

Run the check before staging and you are inspecting the *previous* state of the
repository, not the one you're about to publish.

*Everyday parallel:* checking your bag before you've finished packing it.

### Commit *after* the gate and the tests

If the gate fails or a test breaks, you want to fix it **before** it becomes part
of the permanent history. A commit is not easily undone once pushed, and a secret
committed once stays in the history forever, even if the next commit deletes it.

*Everyday parallel:* proofread before you send, not after.

---

## 4. How to write a commit message

A commit message is a note to your future self, who will not remember what you
did or why.

*Everyday parallel:* labelling a box when you move house. "Kitchen, pans and
baking trays" versus "Stuff". Both take three seconds to write. Only one saves you
an hour later.

### The format

```
type: short description in the present tense
```

**The types**, and when each applies:

| Type | Use it when you | Example |
|---|---|---|
| `feat` | Add a new capability | `feat: add MIBiG source adapter with probe and fetch` |
| `fix` | Correct something broken | `fix: reject edges pointing at non-existent nodes` |
| `docs` | Change documentation only | `docs: add architecture overview` |
| `test` | Add or change tests | `test: cover the entity resolution ledger` |
| `refactor` | Restructure code without changing behaviour | `refactor: move validation rules into ontology.py` |
| `chore` | Housekeeping, config, dependencies | `chore: pin dependency upper bounds` |
| `perf` | Make something faster | `perf: index node_id before the join` |
| `style` | Formatting only, no logic change | `style: apply ruff formatting` |

This convention is widely used and not invented here. Its real value is that
*scanning* the history becomes fast, you can see at a glance whether a stretch of
work was features, fixes, or documentation.

### The rules

1. **Present tense, imperative.** "add", not "added" or "adds". The message
   completes the sentence *"If applied, this commit will…"*.
2. **Under about 70 characters.** Git tools truncate longer ones.
3. **Say what and why, not how.** The *how* is visible in the diff; the *why*
   exists nowhere else.
4. **No full stop at the end.** Convention, and it looks tidier in a list.

### Good and bad

| ❌ Bad | ✅ Good | Why |
|---|---|---|
| `update` | `docs: clarify why raw responses are never edited` | Says what and why |
| `fixed stuff` | `fix: stage before running the safety gate` | Specific and searchable |
| `WIP` | `feat: add MIBiG probe (fetch to follow)` | Honest and still informative |
| `asdf` | anything | Your future self will not thank you |
| `changes to the file that handles the ingestion of MIBiG records including the parser and the tests` | `feat: add MIBiG adapter with parser and tests` | Fits, scans, says the same thing |

### When one line isn't enough

Occasionally a change deserves a paragraph. Use `git commit` with no `-m`. Git
opens an editor. Write the summary line, a blank line, then the detail:

```
fix: reject uncited curated edges at load time

An edge with evidence_level = curated_literature and no citation was
being warned about and then loaded. Warnings get ignored, and an
uncited hand-added fact is exactly what erodes trust in the graph.
The loader now refuses the whole build.
```

The blank line matters: Git treats the first line as the summary and everything
after as the body.

*(If the editor opens and you don't know how to leave it: it's usually `vim`.
Press <kbd>Esc</kbd>, type `:wq`, press Enter to save and quit. To avoid vim
entirely: `git config --global core.editor "code --wait"` uses VS Code instead.)*

---

## 5. The message for every phase

Each phase in the roadmap has one natural commit at the end. Use these, they're
already written to tell a coherent story when read top to bottom.

### Phase 0, design

| What you did | Commit message |
|---|---|
| Initial scaffolding, docs, safety gate | `chore: project scaffolding, documentation, and safety gate` |
| Setup verification script | `chore: add setup verification script` |
| Architecture document | `docs: add architecture overview` |
| Ontology and data model | `feat: add the ontology and data model (nodes, edges, evidence)` |
| Roadmap | `docs: add the phase roadmap with tool justifications` |
| R environment | `feat: add R environment (renv, RStudio project) alongside Python` |
| Container runtime guide | `docs: compare container runtimes (Docker, Podman, Prefect)` |

### Release 1.0, the science

| # | Phase | Commit message |
|---|---|---|
| 1 | Ingestion: MIBiG | `feat: add MIBiG source adapter with evidence locker and provenance log` |
| 2 | PubChem · NCBI · KEGG | `feat: add PubChem, NCBI Taxonomy and KEGG adapters` |
| 3 | UniProt proteins | `feat: add UniProt adapter and the protein layer` |
| 4 | Entity resolution & build | `feat: add entity resolution, resolution ledger, and graph build` |
| 5 | Graph analytics | `feat: add path finding, centrality, and community detection` |
| 6 | Statistical validation (R) | `feat: add R null-model validation and igraph cross-check` |
| 7 | Graph machine learning | `feat: add node embeddings and link prediction with honest evaluation` |
| 8 | Streamlit app | `feat: add the Streamlit app with a read-only SQL console` |
| 8b | Shiny app *(optional)* | `feat: add the Shiny frontend over the same database` |
| 9 | Deployment + GraphRAG | `feat: add the GraphRAG answer layer and deploy the app` |
| 9b | One container *(optional)* | `feat: containerize the Streamlit app (Docker and Podman)` |
|  | Release | `chore: release v1.0.0` |

### Release 2.0, the platform

| # | Phase | Commit message |
|---|---|---|
| 10 | dbt | `feat: move transformations into dbt with the ontology as tests` |
| 11 | PostgreSQL + AGE + pgvector | `feat: add PostgreSQL backend with Apache AGE and pgvector` |
| 12 | Airflow | `feat: orchestrate the pipeline with Airflow` |
| 13 | Snowflake | `feat: add Snowflake as an alternative dbt target` |

### Release 3.0, the product

| # | Phase | Commit message |
|---|---|---|
| 14 | FastAPI | `feat: add the FastAPI service layer` |
| 15 | React frontend | `feat: add the React and TypeScript frontend` |
| 16 | MCP server | `feat: add an MCP server over the graph` |
| 17 | Databricks | `feat: add literature mining with human review` |
| 18 | Containerize the stack | `feat: containerize the full stack with compose` |
| 19 | CI/CD | `ci: build, test, and publish images on every push` |
|  | Release | `chore: release v2.0.0` |

*(`ci` is a type used specifically for continuous-integration configuration.)*

---

## 6. Messages for the changes in between

Most commits are not "I finished a phase." Here is the pattern for everything
else.

| What you did | Commit message |
|---|---|
| Fixed a typo in a document | `docs: fix typo in the ontology guide` |
| Rewrote an explanation more clearly | `docs: clarify why entity resolution refuses to guess` |
| Added a glossary term | `docs: define permutation test and null model in the glossary` |
| Added a package | `chore: add ggplot2 for publication figures` |
| Updated version bounds | `chore: pin dependency upper bounds` |
| Regenerated the lockfile | `chore: refresh requirements.lock.txt` |
| Added tests for existing code | `test: cover the MIBiG parser with offline fixtures` |
| Fixed a bug you found | `fix: handle MIBiG records with no linked compound` |
| Renamed files, no behaviour change | `refactor: rename fetch.py to ingest.py for clarity` |
| Improved the safety gate | `chore: add renv library check to the safety gate` |
| Updated a diagram | `docs: update the architecture diagram for the protein layer` |
| Added a figure | `docs: add the centrality distribution figure` |
| Changed the gitignore | `chore: ignore R workspace files` |
| Deleted something unused | `refactor: remove the unused notebooks folder` |
| Corrected your own earlier mistake | `fix: correct stale phase numbers in the README` |

**Notice the last one.** Committing a correction to your own work is completely
normal and reads as care, not carelessness. A history with visible fixes is more
credible than one that pretends nothing was ever wrong.

---

## 7. One change, one commit

**The principle:** each commit should be one logical change that could be
described in one sentence.

*Everyday parallel:* saving a document after finishing a section, rather than
once at the end of the week. If something goes wrong you lose one section, not a
week, and you can see when each section was written.

### Why it matters practically

- **Undoing.** If commit 5 broke something, you can undo commit 5 alone. If
  commits 1-5 were one giant commit, you undo everything.
- **Finding.** `git log --oneline` becomes a readable table of contents.
- **Understanding.** Six months later, `git blame` tells you *why* a line exists,
  because the message explains it.

### A worked example

Suppose you just did three things: added R support, added a Shiny phase to the
roadmap, and fixed some stale phase numbers.

**Acceptable**: one commit:

```bash
git commit -m "feat: add R support, the Shiny phase, and documentation fixes"
```

**Better**: three commits, because these are three separate ideas:

```bash
git add docs/R-SETUP.md .gitignore .dockerignore check-public-safe.sh
git commit -m "feat: add R environment setup and protect R artefacts"

git add docs/ROADMAP.md docs/00-architecture.md
git commit -m "feat: add optional Shiny phase as a second frontend"

git add -A
git commit -m "docs: fix stale phase numbers and add missing glossary terms"
```

Note that you **push once at the end**, not after each commit. Commits are local;
the push sends all of them together.

### When one file belongs in two commits

Occasionally a single file contains changes for two different ideas. Git can stage
*parts* of a file:

```bash
git add -p README.md
```

Git shows each chunk of changes and asks: stage it? `y` for yes, `n` for no, `?`
for the full list of options.

This is a genuinely useful tool, and also a fiddly one. **When in doubt, just make
one commit.** A slightly coarse history is far better than no commit because you
got tangled in staging.

---

## 8. Tags: marking a release

A **tag** is a permanent label on a specific commit, marking a version.

*Everyday parallel:* a bookmark in a long book. The pages keep turning; the
bookmark stays where you put it.

Only used when you finish a release:

```bash
git tag -a v1.0.0 -m "Release 1.0, knowledge graph, validation, ML, and app"
git push origin develop develop:beta develop:master --tags
```

- `-a` makes an *annotated* tag, which stores who made it and when. Always use
  `-a` for releases.
- `--tags` sends tags too, they are **not** pushed by default, which surprises
  everyone once.

**Version numbers** follow semantic versioning, the same scheme your
`requirements.txt` bounds rely on:

| Change | Example | When |
|---|---|---|
| **Major** | `1.0.0 → 2.0.0` | Something deliberately breaks or the project changes shape |
| **Minor** | `1.0.0 → 1.1.0` | New capability, nothing broken |
| **Patch** | `1.0.0 → 1.0.1` | Bug fix only |

On GitHub, tags become **Releases**, a page per version with notes. That's where
release notes live.

---

## 9. When something goes wrong

Every one of these has happened to everyone. None is a disaster.

### I committed to `master` by mistake

The commit is on the wrong branch. Move it:

```bash
git log --oneline -1                  # note the hash, e.g. a1b2c3d
git switch develop
git cherry-pick a1b2c3d               # copy the commit here

git switch master
git reset --hard origin/master        # discard it from master
git switch develop
```

⚠️ `--hard` discards changes permanently. It's safe here because you just copied
the commit to `develop`, check `git log` on `develop` first if unsure.

### My commit message is wrong (not pushed yet)

```bash
git commit --amend -m "the correct message"
```

`--amend` replaces the last commit rather than adding another.

⚠️ **Only before pushing.** Amending a pushed commit rewrites history that others
may already have.

### My commit message is wrong (already pushed)

Leave it. A slightly wrong message is a small thing; rewriting published history
is a large one. Write a clearer message next time.

### I forgot to include a file

If not pushed yet:

```bash
git add the/forgotten/file
git commit --amend --no-edit          # add it to the last commit, keep the message
```

If already pushed, just make a new commit:

```bash
git commit -m "fix: add the file missed in the previous commit"
```

### The safety gate says NOT SAFE

It names the file. Unstage it, then fix the cause:

```bash
git restore --staged path/to/file     # take it out of the basket
```

Then add the right pattern to `.gitignore` and re-run the gate. **Never commit
past a failing gate**, that check exists precisely for the mistake that cannot be
undone.

### `git push` was rejected

The remote has commits you don't have, usually because you edited a file directly
on github.com, or pushed from another machine.

```bash
git switch develop
git pull --ff-only origin develop
```

If that fails because both sides moved, look at what happened before doing
anything:

```bash
git log --oneline --graph --all -10
```

Then `git pull --rebase origin develop` replays your commits on top of theirs.
**Never** `git push --force` on a shared branch to make an error go away, it
deletes other people's work.

### I want to see what I'm about to commit

```bash
git status                # which files
git diff                  # changes not yet staged
git diff --staged         # changes that ARE staged, what the commit will contain
```

`git diff --staged` before committing is a habit worth building. It's the last
chance to notice a stray debug line.

### I want to undo everything since my last commit

```bash
git restore .             # discard all unstaged changes
```

⚠️ Permanent. Only when you're sure.

---

## 10. The quick reference card

Copy this into a note. It's everything you need day to day.

```bash
# ---- STARTING A SESSION ----
cd ~/projects/microbegraph
source .venv/bin/activate            # Windows:.\.venv\Scripts\Activate.ps1
git switch develop

# ---- WHILE WORKING ----
git status                           # what changed
git diff                             # what exactly changed

# ---- ENDING A SESSION ----
git switch develop
git add -A
./check-public-safe.sh               # must say SAFE TO PUSH
pytest -q                            # from Phase 1 onward
git commit -m "type: what changed and why"
git push origin develop develop:beta develop:master

git switch master
git pull --ff-only origin master
git switch develop

# ---- RELEASE ONLY ----
git tag -a v1.0.0 -m "Release 1.0, description"
git push origin develop develop:beta develop:master --tags
```

**Types:** `feat` `fix` `docs` `test` `refactor` `chore` `perf` `style` `ci`

---

## 11. Checkpoint

You've understood this document when you can answer without scrolling up:

1. Why does staging come *before* the safety gate?
2. What do the three parts of `develop develop:beta develop:master` do?
3. Why sync local `master` after pushing, when the push already updated GitHub?
4. Which type would you use for adding a package to `requirements.txt`?
5. What is the difference between `git diff` and `git diff --staged`?
6. You committed to `master` by mistake and haven't pushed. What now?
7. Why should a commit be one logical change?

<details>
<summary>Answers (open after you've tried)</summary>

1. The gate inspects what Git is *tracking*. An unstaged new file is invisible to
   Git and therefore to the gate, so checking first inspects the previous state.
2. `develop` updates remote develop; `develop:beta` pushes local develop into
   remote beta; `develop:master` pushes local develop into remote master. Three
   branches, one command.
3. The push updated GitHub's master, not your laptop's. Without the sync, local
   master drifts further behind every phase.
4. `chore`, housekeeping and dependencies.
5. `git diff` shows changes you haven't staged; `git diff --staged` shows what the
   commit will actually contain. The second is the one to check before committing.
6. `git cherry-pick` the commit onto develop, then `git reset --hard
   origin/master` on master to remove it.
7. So you can undo one thing without undoing five, find when something changed,
   and understand *why* a line exists six months later.

</details>

---

## Committing this document

```bash
git switch develop
git add -A                    # stage first, so the gate can see the new files

./check-public-safe.sh        # must print "SAFE TO PUSH"

git commit -m "docs: add the git workflow and commit message reference"
git push origin develop develop:beta develop:master

## --tags is optional, and only when cutting a new version
## then switch back to local master and pull in the changes from the remote

git switch master
git pull --ff-only origin master
git switch develop
```

---

**Related:** [`01-setup.md`](01-setup.md) (how the branches were created) ·
[`ROADMAP.md`](ROADMAP.md) (what each phase does) ·
[`GLOSSARY.md`](GLOSSARY.md)
