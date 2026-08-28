# R Setup: R, RStudio, and working alongside Python

**Prerequisites:** [`01-setup.md`](01-setup.md) complete — you have the repository
cloned, Git configured, and a Python environment working. No R experience is
assumed.

**Learning goal:** you will have R and RStudio installed, a sealed R package
environment (`renv`) for this project, and a clear understanding of how R and
Python coexist in one repository without either getting in the other's way. You
will also read the project's DuckDB database from R and see the same facts your
Python code produced.

**Time:** 40–60 minutes, once per machine.

**When you need this:** before **Phase 6** (statistical validation). Everything
before that is Python-only, so you can safely defer this document — but reading
it early is useful, because the "one database, two languages" idea shapes how the
project is designed.

> Every term here is also in [`GLOSSARY.md`](GLOSSARY.md).

---

## Contents

1. [Why R at all, when the project is already in Python?](#1-why-r-at-all-when-the-project-is-already-in-python)
2. [R and RStudio are two different things](#2-r-and-rstudio-are-two-different-things)
3. [Step 1 — Install R](#3-step-1--install-r)
4. [Step 2 — Install RStudio](#4-step-2--install-rstudio)
5. [Step 3 — The project file (`.Rproj`)](#5-step-3--the-project-file-rproj)
6. [Step 4 — `renv`: R's sealed toolbox](#6-step-4--renv-rs-sealed-toolbox)
7. [Step 5 — Install the project's R packages](#7-step-5--install-the-projects-r-packages)
8. [Step 6 — Keep R's clutter out of Git](#8-step-6--keep-rs-clutter-out-of-git)
9. [Step 7 — Read the project database from R](#9-step-7--read-the-project-database-from-r)
10. [Using RStudio and VS Code together](#10-using-rstudio-and-vs-code-together)
11. [Running R from the terminal](#11-running-r-from-the-terminal)
12. [The R/Python dictionary](#12-the-rpython-dictionary)
13. [Troubleshooting](#13-troubleshooting)
14. [Checkpoint](#14-checkpoint)
15. [Committing this phase](#15-committing-this-phase)

---

## 1. Why R at all, when the project is already in Python?

A fair question, and "because I know R" isn't a good enough answer for a public
repository. Here is the honest case.

### Reason 1 — R is the language statisticians built

Python is a general-purpose language that grew excellent statistics libraries. R
was designed *by statisticians, for statistics*, from the beginning. For the one
thing Phase 6 does — asking **"could this pattern have arisen by chance?"** — R's
tooling is more direct, better documented, and closer to how the question is
posed in the literature.

*Everyday parallel:* a Swiss Army knife has a screwdriver, and it works. A
screwdriver is still better at screws. Neither observation is an insult to the
other tool.

### Reason 2 — Two implementations agreeing is evidence

Phase 6 computes centrality in R with `igraph` and compares it against the Python
`networkx` result. If two independently written libraries, in two languages, by
two different teams, produce the same numbers, that is **real evidence your
pipeline is correct**.

If they disagree, you've found a bug you would otherwise have shipped.

*Everyday parallel:* checking a bill by adding the column twice — once top to
bottom, once bottom to top. Same numbers, different route.

This is not busywork. Cross-implementation validation is a genuine technique, and
most portfolio projects skip it entirely.

### Reason 3 — One database, two languages

DuckDB has clients for both languages. `microbegraph.duckdb` — built by your
Python pipeline — is queryable directly from R:

```r
con <- DBI::dbConnect(duckdb::duckdb(), "data/processed/microbegraph.duckdb")
edges <- DBI::dbGetQuery(con, "SELECT * FROM edges")
```

No export step. No CSV shuffling. No format conversion. The same file, read by a
different language.

**This is worth pausing on**, because it's a real architectural idea: when your
data lives in a shared, open format, the choice of language stops being a lock-in
decision and becomes a per-task decision. Use Python for the pipeline, R for the
statistics, SQL for the aggregation — over one set of facts.

*Everyday parallel:* a shared kitchen where everyone reads from the same recipe
book, regardless of which knife they prefer.

### Reason 4 — `ggplot2`

For static, publication-quality figures, `ggplot2` is unusually good. The
teaching figures in `docs/img/` come from it.

### And the honest counterpoint

R adds a second language, a second package manager, and a second thing that can
break. That is a real cost. It's justified here because the reasons above are
specific — a statistical technique, a validation strategy, and a plotting library
— rather than "more languages is better." **If you removed R, the project would
be measurably weaker in one identifiable way: it would have no null-model
validation.** That's the test any second language should have to pass.

---

## 2. R and RStudio are two different things

This confuses nearly everyone once, so let's be explicit.

| | What it is | Analogy |
|---|---|---|
| **R** | The language and the engine that runs the code | The car's engine |
| **RStudio** | An application for writing and running R comfortably | The dashboard, seats, and steering wheel |

**Install R first, then RStudio.** RStudio has no engine of its own — without R
it will start and immediately complain that it can't find one.

Compare with what you already know: **Python** is the engine, **VS Code** is the
dashboard. Exactly the same relationship.

### A third option worth knowing about

**Positron** is a newer IDE from the same company that makes RStudio. It's built
on the same foundation as VS Code and supports **R and Python side by side in one
window**. For a project like this one — genuinely bilingual — it's an appealing
option.

This guide uses **RStudio**, because it's the most widely used, best documented,
and what you'll find in every R tutorial. If you'd rather try Positron later,
nothing in this project depends on the choice: they all edit the same files.

---

## 3. Step 1 — Install R

R comes from **CRAN** (the Comprehensive R Archive Network) — the official
repository, run by the R Foundation. It is also where R packages come from, so
you'll see the name often.

<details open>
<summary><b>🪟 Windows</b></summary>

1. Go to <https://cran.r-project.org/bin/windows/base/>
2. Click the **Download R for Windows** link at the top.
3. Run the installer, accepting the defaults.
4. Optionally also install **Rtools** from
   <https://cran.r-project.org/bin/windows/Rtools/> — needed only if a package
   has to be compiled from source. Skip it for now; install it if you later hit
   an error asking for it.

</details>

<details open>
<summary><b>🍎 macOS</b></summary>

1. Go to <https://cran.r-project.org/bin/macosx/>
2. Download the right build for your machine:
   - **Apple Silicon** (M1/M2/M3/M4) → the `arm64` package
   - **Intel Mac** → the `x86_64` package
   *(Unsure? Apple menu →  About This Mac. "Chip" means Apple Silicon;
   "Processor" means Intel.)*
3. Run the `.pkg` installer and accept the defaults.

</details>

<details open>
<summary><b>🐧 Linux — RHEL 8 / Rocky / AlmaLinux</b></summary>

R lives in the EPEL repository (Extra Packages for Enterprise Linux — a
community-maintained collection of software Red Hat doesn't ship itself):

```bash
sudo dnf install -y epel-release
sudo dnf install -y R
```

If `dnf` reports that R isn't found, enable the CodeReady Builder repository
first — some of R's dependencies live there:

```bash
sudo subscription-manager repos --enable codeready-builder-for-rhel-8-x86_64-rpms
# On Rocky/AlmaLinux instead:
# sudo dnf config-manager --set-enabled powertools     # Rocky 8
```

</details>

### Verify

```bash
R --version
```

```
R version 4.4.2 (2024-10-31) -- "Pile of Leaves"
Copyright (C) 2024 The R Foundation for Statistical Computing
```

✅ **Checkpoint.** A version number appears. **4.0 or newer** is fine; 4.3+ is
ideal.

*(Yes, R releases have names. That one's from a Peanuts strip. All of them are.)*

---

## 4. Step 2 — Install RStudio

RStudio Desktop is **free and open source** (AGPL licence). There is a paid
commercial edition with support, which you do not need.

1. Go to <https://posit.co/download/rstudio-desktop/>
2. The page detects your system and offers the right download. Take it.
3. Install as normal for your platform:
   - **Windows** — run the `.exe`, accept defaults
   - **macOS** — drag to Applications
   - **RHEL 8** — download the `.rpm`, then:
     ```bash
     sudo dnf install -y ./rstudio-*.rpm
     ```
4. Launch RStudio.

> ⚠️ **macOS version note.** Current RStudio requires **macOS 14 or newer**. On an
> older macOS, the download page offers earlier RStudio versions that still work —
> scroll to the older-versions section rather than forcing the newest.

> **On a headless Linux VM** with no desktop, install **RStudio Server** instead
> (`rstudio-server-rhel-*.rpm` from posit.co/download/rstudio-server/). It runs in
> your browser at port 8787. Also free and open source.

### What you're looking at

RStudio opens with four panes. Learn these four names and you can follow any R
tutorial:

| Pane | What it is |
|---|---|
| **Console** (bottom-left) | Type R here and it runs immediately. Like a conversation. |
| **Source** (top-left) | Where you write and save scripts. Like a document. |
| **Environment** (top-right) | Every object currently in memory — genuinely useful, and something VS Code shows less readily |
| **Files / Plots / Packages / Help** (bottom-right) | Your folder, your charts, installed packages, documentation |

Try it — type this into the **Console** and press Enter:

```r
1 + 1
```
```
[1] 2
```

✅ **Checkpoint.** You see `[1] 2`. R is running.

*(The `[1]` is R telling you this is the first element of the result. R thinks in
vectors — lists of values — so even a single number is a list of one. It looks odd
at first and stops being noticeable within a day.)*

---

## 5. Step 3 — The project file (`.Rproj`)

An **RStudio project** is a small file that tells RStudio "this folder is a
project." Opening it sets the working directory correctly, keeps your open tabs
between sessions, and — most importantly — stops the single most common R
beginner error: *scripts that only work if you happen to be in the right folder.*

*Everyday parallel:* a labelled folder on your desk versus loose papers. The
label doesn't change the contents; it stops you looking in the wrong place.

**Create it:**

1. In RStudio: **File → New Project → Existing Directory**
2. Browse to your `microbegraph` folder
3. **Create Project**

RStudio creates `microbegraph.Rproj` and reopens in that project. From now on,
open the project — not individual files — and paths like
`data/processed/microbegraph.duckdb` will always resolve from the repository
root, on every machine.

**Commit this file.** It's tiny, it's plain text, and it means anyone cloning your
repository gets the same behaviour.

---

## 6. Step 4 — `renv`: R's sealed toolbox

You already know this idea. In Python it's `.venv`; in R it's **`renv`**. Same
problem, same solution, different name.

**The problem:** R packages install system-wide by default. Project A needs
`igraph` 1.5, project B needs 2.0, and installing one breaks the other.

**The solution:** a per-project library, plus a lockfile recording exact versions.

| Python | R | Job |
|---|---|---|
| `.venv/` | `renv/library/` | Where this project's packages live |
| `requirements.txt` | `DESCRIPTION` *(or the script itself)* | What the project needs |
| `requirements.lock.txt` | `renv.lock` | Exactly what was working |
| `source .venv/bin/activate` | *(automatic on project open)* | Use this project's packages |
| `pip install` | `renv::install()` | Add a package |
| `pip freeze >` | `renv::snapshot()` | Record exact versions |

Notice the fourth row: **R does not need an explicit activation step.** Opening
the `.Rproj` file activates `renv` automatically. One fewer thing to forget than
Python's `.venv` — a genuine small win.

**Set it up.** In the RStudio **Console**:

```r
install.packages("renv")
```

You may be asked to choose a CRAN mirror — pick any; they're copies of the same
thing. Then:

```r
renv::init()
```

```
* Initializing project ...
* Discovering package dependencies ... Done!
* Copying packages into the cache ... Done!
* Project '~/projects/microbegraph' loaded. [renv 1.0.7]
```

This creates `renv/`, `renv.lock`, and an `.Rprofile` that activates it
automatically whenever the project opens.

✅ **Checkpoint.** `renv.lock` exists in your project folder.

---

## 7. Step 5 — Install the project's R packages

In the RStudio **Console**:

```r
renv::install(c(
  "igraph",      # graphs and network algorithms — R's equivalent of networkx
  "DBI",         # the standard way R talks to any database
  "duckdb",      # the DuckDB driver, so R can read the project's database file
  "dplyr",       # data manipulation — R's closest equivalent to pandas
  "ggplot2",     # the plotting library, for publication-quality figures
  "readr",       # fast, reliable CSV reading
  "tidyr"        # reshaping tables between wide and long layouts
))
```

This takes a few minutes the first time. Some packages compile from source, which
is normal in R and shows a lot of scrolling output.

**Then record exactly what you got:**

```r
renv::snapshot()
```

```
The following package(s) will be updated in the lockfile:
# CRAN -----------------------------------------------------------
- DBI          [* -> 1.2.3]
- dplyr        [* -> 1.1.4]
- duckdb       [* -> 1.1.3]
- ggplot2      [* -> 3.5.1]
- igraph       [* -> 2.1.1]
...
Do you want to proceed? [Y/n]:
```

Type `y` and Enter. `renv.lock` now holds exact versions — the R equivalent of
your `requirements.lock.txt`. **Commit it.**

### Verify

```r
library(igraph)
library(DBI)
library(duckdb)
cat("R packages loaded OK\n")
```

```
R packages loaded OK
```

*(`library()` messages about objects being "masked" are normal, not errors. They
mean two packages define a function with the same name and R is telling you which
one wins.)*

✅ **Checkpoint.** The message prints with no error above it.

---

## 8. Step 6 — Keep R's clutter out of Git

R generates working files that must not be published — most importantly
`renv/library/`, which is hundreds of megabytes of installed packages, and
`.RData`, which silently saves your entire workspace including any data you had
loaded.

Add this block to your `.gitignore`:

```gitignore
# --- R -----------------------------------------------------------
# The installed package library: large, machine-specific, and fully
# rebuildable from renv.lock. Exactly like .venv/ for Python.
renv/library/
renv/staging/
renv/python/
renv/sandbox/

# A saved snapshot of your entire R workspace. Never commit this: it can
# silently contain data, credentials, or half-finished objects, and it makes
# your scripts appear to work when they only work on YOUR machine.
.RData
.Rhistory
.Rapp.history

# RStudio's per-user state (open tabs, pane sizes)
.Rproj.user/

# Output from R CMD check
*.Rcheck/

# NOT ignored, and committed on purpose:
#   microbegraph.Rproj  — so everyone gets the same project settings
#   renv.lock           — so everyone can rebuild the same package versions
#   .Rprofile           — so renv activates automatically on open
```

> **The `.RData` trap is worth understanding.** By default R offers to save your
> workspace when you quit, and to reload it when you start. That sounds helpful
> and is actively harmful: your script starts working because an object is
> already in memory from last time, and then fails for everyone else. Turn it off
> in RStudio: **Tools → Global Options → General → uncheck "Restore .RData into
> workspace at startup"**, and set "Save workspace to .RData on exit" to
> **Never**.
>
> *Everyday parallel:* a recipe that works only because there's already a pot of
> stock in your fridge that isn't in the ingredients list.

---

## 9. Step 7 — Read the project database from R

This is the moment the two languages meet. *(It needs the database to exist, so
it works from Phase 4 onward — come back then if you're reading ahead.)*

Create `R/explore.R`:

```r
# ---------------------------------------------------------------
# MicrobeGraph — reading the project database from R
#
# WHY THIS FILE EXISTS:
#   The pipeline is written in Python, but DuckDB has clients for both
#   languages. That means R can read the SAME database file directly —
#   no export, no CSV shuffling, no format conversion.
#
#   The wider idea: when data lives in a shared, open format, the choice
#   of language stops being a lock-in decision and becomes a per-task one.
# ---------------------------------------------------------------

library(DBI)        # the standard interface R uses to talk to any database
library(duckdb)     # the specific driver for DuckDB
library(dplyr)      # data manipulation, for the summarising below

# Connect. The path is relative to the project root, which is why opening
# the .Rproj file matters — it guarantees we start in the right place.
con <- dbConnect(duckdb::duckdb(), "data/processed/microbegraph.duckdb")

# What tables exist?
cat("Tables in the database:\n")
print(dbListTables(con))

# Run SQL directly. This is the SAME SQL the Python code runs — SQL is
# neutral ground between the two languages.
edge_summary <- dbGetQuery(con, "
  SELECT edge_type,
         evidence_level,
         COUNT(*) AS n
  FROM edges
  GROUP BY edge_type, evidence_level
  ORDER BY n DESC
")

cat("\nEdges by type and evidence level:\n")
print(edge_summary)

# Pull a whole table into R for analysis
edges <- dbGetQuery(con, "SELECT * FROM edges")
nodes <- dbGetQuery(con, "SELECT * FROM nodes")

cat("\nLoaded", nrow(nodes), "nodes and", nrow(edges), "edges into R.\n")

# ALWAYS close the connection. An open connection holds a lock on the file,
# which can block the Python side from writing to it.
dbDisconnect(con, shutdown = TRUE)
```

Run it from the RStudio Console:

```r
source("R/explore.R")
```

Expected shape of the output:

```
Tables in the database:
[1] "edges" "nodes"

Edges by type and evidence level:
        edge_type       evidence_level   n
1        PRODUCES curated_experimental 412
2         HARBORS curated_experimental 389
...

Loaded 1247 nodes and 3891 edges into R.
```

✅ **Checkpoint.** R prints tables that your Python pipeline created. **The two
languages are now working on the same data.**

---

## 10. Using RStudio and VS Code together

The key realisation: **neither program owns your project.** Both are editors
pointed at the same folder on disk. Git doesn't know or care which one saved a
file.

*Everyday parallel:* opening a spreadsheet in Excel and a document in Word from
the same folder. Different tools, different files, one filing cabinet.

**A practical division of labour:**

| Tool | Best for |
|---|---|
| **RStudio** | R scripts, the Environment pane, plots, `renv`, R help |
| **VS Code** | Python, Markdown docs, YAML, the terminal, Git operations |

**Both open at once is completely fine.** The only rule worth following: **don't
have the same file open and unsaved in both.** Whichever saves last wins, and you
lose the other's changes silently.

*Everyday parallel:* two people editing the same paper document. Fine if you're
on different pages, messy on the same one.

### If you'd rather use R inside VS Code

You can, and for a bilingual project it's tempting:

1. VS Code → **Extensions** → search **R** → install the one by **REditorSupport**
2. In R, install the language server:
   ```r
   renv::install("languageserver")
   ```
3. Restart VS Code. You now get R syntax highlighting, completion, and a console.

**Honest comparison:** VS Code's R support is good and improving, but RStudio's
Environment pane, plot history, and integrated help are still better for
*interactive statistical work* — the exploratory back-and-forth where you run a
line, look at the result, and adjust. That's exactly what Phase 6 involves.

**My suggestion:** use VS Code for Python and documentation, RStudio for the R
work. Try Positron if you'd like one window for both. There is no wrong answer
here, and switching later costs nothing.

### Git works identically from either

RStudio has a **Git** pane (top-right, once the project is in a repository) with
buttons for stage, commit, push. It's the same Git, doing the same thing.

**However — this project's push command has three targets:**

```bash
git push origin develop develop:beta develop:master
```

RStudio's push button can't express that. **Use the terminal for pushes**, and
the buttons for staging and reviewing changes if you prefer clicking. RStudio has
a built-in terminal (**Tools → Terminal → New Terminal**) so you don't have to
leave the window.

---

## 11. Running R from the terminal

You don't need RStudio open to run R. This matters for automation — Phase 12's
orchestrator runs R scripts with no human present.

```bash
# Run a script start to finish
Rscript R/validate_graph.R

# One-off command
Rscript -e 'cat(R.version.string, "\n")'

# Interactive R in the terminal (quit with q() )
R
```

`Rscript` is R's equivalent of running `python script.py`. Every R script in this
project is written to work this way — no RStudio required — which is what makes
them automatable.

---

## 12. The R/Python dictionary

Coming from Python, this table is the fastest way in. Keep it open beside you.

| Task | Python | R |
|---|---|---|
| Install a package | `pip install x` | `install.packages("x")` |
| Load a package | `import x` | `library(x)` |
| Assign a value | `x = 5` | `x <- 5` *(also `=`, but `<-` is idiomatic)* |
| Read a CSV | `pd.read_csv("f.csv")` | `readr::read_csv("f.csv")` |
| First rows | `df.head()` | `head(df)` |
| Dimensions | `df.shape` | `dim(df)` |
| Column names | `df.columns` | `names(df)` |
| Filter rows | `df[df.x > 5]` | `filter(df, x > 5)` |
| Select columns | `df[["a","b"]]` | `select(df, a, b)` |
| New column | `df["z"] = ...` | `mutate(df, z = ...)` |
| Group and count | `df.groupby("x").size()` | `count(df, x)` |
| Chain operations | `df.pipe(...)` | `df \|> ...` *(the pipe)* |
| Print | `print(x)` | `print(x)` or just `x` |
| Comment | `#` | `#` |
| Index of first element | `0` | **`1`** ⚠️ |

**Two differences that will catch you out:**

1. **R counts from 1, not 0.** `x[1]` is the first element. Every off-by-one bug
   you've ever had, in mirror image. There's no trick — you just adjust.
2. **`<-` for assignment.** `=` works too, but R code in the wild uses `<-`, so
   reading other people's code is easier if you use it. RStudio has a shortcut:
   <kbd>Alt</kbd>/<kbd>Option</kbd> + <kbd>-</kbd>.

**The pipe (`|>`)** is worth knowing early — it passes a result into the next
function, so you read left to right instead of inside out:

```r
edges |> filter(evidence_level == "inferred") |> count(edge_type)
```

Read as: *take edges, then keep the inferred ones, then count by edge type.*
Python's method chaining (`df.query(...).groupby(...)`) is the same idea.

---

## 13. Troubleshooting

### "RStudio can't find R"

R isn't installed, or was installed after RStudio. Install R (Step 1), then
restart RStudio. If it still can't find it: **Tools → Global Options → General →
R version → Change** and point it at your installation.

### `renv::init()` fails or hangs

Usually a CRAN mirror problem. Set one explicitly:

```r
options(repos = c(CRAN = "https://cloud.r-project.org"))
renv::init()
```

### A package fails to compile

R compiles more packages from source than Python does, so it needs build tools:

- **Windows** — install **Rtools** from <https://cran.r-project.org/bin/windows/Rtools/>
- **macOS** — run `xcode-select --install` in Terminal
- **RHEL 8** — `sudo dnf install -y gcc gcc-c++ gcc-gfortran make`

### `duckdb` fails to install

It's a large package that compiles a database engine. Ensure build tools are
present (above), then retry. If it still fails, the CSV route works as a fallback
— every table can be exported by Python and read with `readr::read_csv()`. Slower
and less elegant, but nothing is blocked.

### Scripts work in RStudio but fail with `Rscript`

Almost always a path problem. RStudio sets the working directory to the project
root; a plain terminal uses wherever you happen to be. Run `Rscript` from the
repository root, and always use paths relative to it.

### R feels slow to start

Normal — R loads more at startup than Python. If it's *very* slow, you probably
have `.RData` restoration enabled and it's reloading a large workspace. Turn it
off (Step 6).

### `renv` says packages are out of sync

```r
renv::status()      # what differs
renv::restore()     # make the library match renv.lock  (the usual fix)
renv::snapshot()    # make renv.lock match the library  (only if you added packages deliberately)
```

Choosing between the last two is the whole skill: **restore** when you want the
recorded state; **snapshot** when your current state is the new truth.

---

## 14. Checkpoint

- [ ] `R --version` prints 4.0 or newer
- [ ] RStudio opens and `1 + 1` returns `[1] 2` in the Console
- [ ] `microbegraph.Rproj` exists and RStudio opens the project from it
- [ ] `renv.lock` exists
- [ ] `library(igraph)`, `library(DBI)`, `library(duckdb)` all load without error
- [ ] `.gitignore` contains the R block, and `renv/library/` is **not** tracked
- [ ] `.RData` restoration is disabled in RStudio's options
- [ ] `./check-public-safe.sh` still prints `SAFE TO PUSH`
- [ ] *(From Phase 4 onward)* `source("R/explore.R")` prints tables from the
      project database

**What you learned:** the difference between a language and an IDE; that R and
Python coexist in one repository because both are just files on disk; `renv` as
R's answer to the same problem `.venv` solves; why `.RData` is a trap;
that DuckDB lets both languages read one file with no export step; and enough
R/Python vocabulary to read either.

---

## 15. Committing this phase

```bash
git switch develop
git add -A                    # stage first, so the gate can see the new files

./check-public-safe.sh        # must print "SAFE TO PUSH"

git commit -m "feat: add R environment (renv, RStudio project) alongside Python"
git push origin develop develop:beta develop:master

## --tags is optional, and only when cutting a new version
## then switch back to local master and pull in the changes from the remote

git switch master
git pull --ff-only origin master
git switch develop
```

> **Check carefully before this particular commit.** `renv/library/` is large —
> if it were accidentally tracked, the repository would balloon by hundreds of
> megabytes. Confirm with:
> ```bash
> git ls-files | grep -c "^renv/library/"      # must print 0
> ```

---

**Related:** [`01-setup.md`](01-setup.md) (the Python side) ·
[`ROADMAP.md`](ROADMAP.md) (where R is used) ·
[`GLOSSARY.md`](GLOSSARY.md)
