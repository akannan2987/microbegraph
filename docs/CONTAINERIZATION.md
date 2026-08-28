# Containerization: shipping the whole application in a box

**Prerequisites:** [`CONTAINERS.md`](CONTAINERS.md) (what a container is, and
choosing a runtime) and [`01-setup.md`](01-setup.md). You do not need to have
built any phase yet — this document explains the destination.

**Learning goal:** understand what it means to containerize an entire
application, why it's worth doing, and exactly how MicrobeGraph does it — with
**one set of files that works identically under Docker and Podman**, on Windows,
macOS, and RHEL 8. By the end you will be able to explain images, layers,
volumes, networks, health checks, and compose files to someone else.

**Time:** 40–50 minutes reading. The build work happens in Phases 9b and 18.

> Every term here is also in [`GLOSSARY.md`](GLOSSARY.md).

---

## Contents

1. [The problem, at three sizes](#1-the-problem-at-three-sizes)
2. [What "containerizing the application" actually means](#2-what-containerizing-the-application-actually-means)
3. [The three-step plan](#3-the-three-step-plan)
4. [Step one: one service in one container (Phase 9b)](#4-step-one-one-service-in-one-container-phase-9b)
5. [The Containerfile, line by line](#5-the-containerfile-line-by-line)
6. [Layers and caching: why the order matters](#6-layers-and-caching-why-the-order-matters)
7. [Multi-stage builds: don't ship the mixing bowls](#7-multi-stage-builds-dont-ship-the-mixing-bowls)
8. [Volumes: data must outlive the container](#8-volumes-data-must-outlive-the-container)
9. [Networks and ports: how services find each other](#9-networks-and-ports-how-services-find-each-other)
10. [Secrets in containers](#10-secrets-in-containers)
11. [Health checks and start order](#11-health-checks-and-start-order)
12. [Step two: the whole stack with compose (Phase 18)](#12-step-two-the-whole-stack-with-compose-phase-18)
13. [Docker vs Podman: the differences that actually bite](#13-docker-vs-podman-the-differences-that-actually-bite)
14. [RHEL 8 specifics](#14-rhel-8-specifics-selinux-rootless-ports-and-autostart)
15. [Step three: publishing images (Phase 19)](#15-step-three-publishing-images-phase-19)
16. [Security and size: doing it properly](#16-security-and-size-doing-it-properly)
17. [Troubleshooting](#17-troubleshooting)
18. [Checkpoint](#18-checkpoint)
19. [Committing this phase](#19-committing-this-phase)

---

## 1. The problem, at three sizes

Containerization solves the same problem three times over, at growing scale. It's
worth seeing all three, because each one motivates a different piece of the
tooling.

### Size 1 — "it works on my machine"

You finish the project. A colleague clones it. It fails: their Python is 3.9,
they're missing a system library, their operating system puts files somewhere
else.

*Everyday parallel:* you write a recipe that works in your kitchen. A friend tries
it and it fails — their oven runs hot, their flour is different, they don't own a
stand mixer. The recipe was never the whole story. **The kitchen was part of it.**

`.venv` fixes part of this — it seals your Python packages. But it doesn't seal
the Python itself, the operating system libraries underneath, or the system tools
your code shells out to.

### Size 2 — "five things have to start in the right order"

By Release 3.0, MicrobeGraph isn't one program. It's a **PostgreSQL database**, a
**FastAPI service**, a **Streamlit app**, a **React frontend**, and (optionally)
**Airflow**. Each needs its own setup. The database must be ready before the API
starts. The API must be reachable before the frontend loads. Each needs to know
where the others live.

Doing that by hand means five terminal windows, a written start-up order, and a
page of notes that goes stale.

*Everyday parallel:* a restaurant isn't one machine. It's an oven, a fridge, a
dishwasher, a till, and a coffee machine — each installed separately, each
depending on plumbing and power that must already be working. Opening a new branch
by shipping the *fully-fitted kitchen as one unit* is a very different proposition
from buying five appliances and hoping.

### Size 3 — "the same thing must run in three places"

Your laptop. A RHEL 8 server. A cloud host. Same application, three very different
environments.

*Everyday parallel:* this is the actual, literal shipping container. Before them,
loading a ship meant hand-stacking barrels, crates and sacks — every cargo
different, every port needing its own handling. The standard steel box changed
that: **the crane doesn't care what's inside.** One agreed shape, and any ship,
truck, or train can carry it.

Software containers are named after that, and it's the most useful analogy in the
whole topic. The container is a standard box. The host doesn't need to know or
care what's inside it.

---

## 2. What "containerizing the application" actually means

Concretely, it means producing:

1. **A recipe file per service** — called a `Containerfile` (or `Dockerfile`;
   identical format, two names). It says: start from this base, install these
   things, copy in this code, run this command.
2. **An image per service** — the built, packaged result of that recipe. Static,
   shareable, versioned.
3. **A compose file** — one file describing all the services, how they connect,
   what storage they keep, and in what order they start.
4. **One command that runs everything.**

That last point is the whole payoff. The end state for MicrobeGraph is:

```bash
git clone https://github.com/akannan2987/microbegraph.git
cd microbegraph
docker compose up          # or: podman compose up
```

Two commands and the entire system is running — database, API, app, frontend — on
a machine with **no Python installed, no R, no PostgreSQL, no configuration**.

That is the difference between "here is my code" and "here is my application."

---

## 3. The three-step plan

Containers are introduced gradually, and each step is motivated by a problem the
previous step exposed. Nothing arrives before it's needed.

| Step | Phase | What it covers | Why here |
|---|---|---|---|
| **One container** | **9b** *(optional)* | The Streamlit app alone, in a single image | Learn images, layers, ports and volumes on a **one-service** system, where there's only one thing to get wrong |
| **The whole stack** | **18** | Postgres + API + Streamlit + React + Airflow, via compose | Now that several services exist, learn how they find each other, share storage, and start in order |
| **Automated builds** | **19** | CI builds and publishes images on every push | Now that images exist, stop building them by hand |

**Phase 12 (Airflow) also uses containers**, but differently: there you *consume*
images somebody else built. Here you *build your own*. Consuming first, building
second, is the gentler order.

**Release 1.0 never requires containers.** `.venv` remains a fully supported path
forever. Containerization is an *additional* way to run the project, never a
replacement — which keeps a fresh clone runnable by someone who doesn't want to
install a container engine at all.

---

## 4. Step one: one service in one container (Phase 9b)

The goal: package the Streamlit app so anyone can run it with one command and no
Python.

```bash
# Docker
docker build -t microbegraph-app .
docker run -p 8501:8501 microbegraph-app

# Podman — identical, one word changed
podman build -t microbegraph-app .
podman run -p 8501:8501 microbegraph-app
```

Then open `http://localhost:8501`. The app runs. The machine needs no Python, no
pandas, no NetworkX.

**Notice how similar the two engines are.** Podman deliberately mirrors Docker's
command line, so nearly every Docker tutorial you find works by substituting one
word. This is not a coincidence — it's Podman's explicit design goal.

---

## 5. The Containerfile, line by line

Here is the real one, with every line explained. **Read the comments — they're the
lesson.**

```dockerfile
# ==============================================================================
# MicrobeGraph — the Streamlit app, in a box
#
# BUILD:  docker build -t microbegraph-app .      (or: podman build ...)
# RUN:    docker run -p 8501:8501 microbegraph-app
#
# This file is called "Containerfile". Docker also accepts "Dockerfile" —
# same format, two names. Podman prefers Containerfile; both engines read
# both. We use Containerfile because it's the vendor-neutral name.
# ==============================================================================

# ---- 1. The starting point --------------------------------------------------
# Every image is built ON TOP of another image. This one starts from an
# official Python 3.12 image built on Debian "slim" — a minimal Linux with
# Python already installed.
#
# EVERYDAY PARALLEL: you don't build a kitchen from raw ore. You start with a
# room that already has plumbing and power, and fit it out from there.
#
# WHY "slim": the full Python image is ~1 GB of tools we'd never use. Slim is
# ~150 MB. Smaller images build faster, transfer faster, and have fewer
# components that could contain a vulnerability.
#
# WHY the digest is pinned in production: "python:3.12-slim" can quietly change
# when the maintainers rebuild it. Pinning by digest makes the build
# reproducible. We use the readable tag here and pin in CI (Phase 19).
FROM python:3.12-slim

# ---- 2. Labels: who made this and why ---------------------------------------
# Metadata attached to the image. Not required, but it means anyone who finds
# a stray image on a server can trace it back.
LABEL org.opencontainers.image.title="MicrobeGraph"
LABEL org.opencontainers.image.description="A knowledge graph of microbes, metabolites, and crop diseases"
LABEL org.opencontainers.image.source="https://github.com/akannan2987/microbegraph"
LABEL org.opencontainers.image.licenses="MIT"

# ---- 3. Where we work inside the container ----------------------------------
# Creates /app inside the image and makes it the current directory for
# everything that follows. Like "cd /app", but permanent.
#
# WHY a fixed path: so every later instruction and every run has one known
# location. Guessing where files live is a classic source of confusion.
WORKDIR /app

# ---- 4. System packages (only what's genuinely needed) ----------------------
# The slim base omits things like compilers. Some Python packages need them.
#
# WHY all on one line joined by &&: each instruction creates a LAYER (see the
# next section). Splitting this into three instructions would store three
# layers instead of one, making the image bigger for no benefit.
#
# WHY "rm -rf /var/lib/apt/lists/*": the package index is ~40 MB and useless
# after installing. Deleting it IN THE SAME instruction keeps it out of the
# layer entirely. Deleting it in a later instruction would NOT shrink the
# image — the data would still be sitting in the earlier layer.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
    && rm -rf /var/lib/apt/lists/*

# ---- 5. Python dependencies — copied BEFORE the code ------------------------
# This ordering looks odd and is the single most important optimisation in
# this file. Full explanation in section 6 below.
COPY requirements.txt .

# --no-cache-dir: don't keep pip's download cache in the image (~100 MB saved)
RUN pip install --no-cache-dir -r requirements.txt

# ---- 6. Now the application code --------------------------------------------
# Code changes constantly; dependencies rarely. Copying code LAST means a code
# edit only invalidates this layer, so rebuilds take seconds instead of
# minutes.
#
# .dockerignore controls what is excluded here — see section 6.
COPY src/ ./src/
COPY app/ ./app/
COPY artifacts/ ./artifacts/

# ---- 7. Run as a non-root user ----------------------------------------------
# By default a container's processes run as root. If something is ever
# compromised, root inside a container is a far better starting point for an
# attacker than an ordinary user.
#
# EVERYDAY PARALLEL: a contractor working in your house doesn't need the keys
# to every room and the safe combination. Give the minimum access the job
# needs.
#
# This is good practice under Docker and largely redundant under rootless
# Podman (where "root" inside the container is already an unprivileged ID
# outside it) — but we do it anyway, because the image must be safe under
# either engine.
RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app
USER appuser

# ---- 8. Which door is open --------------------------------------------------
# EXPOSE is DOCUMENTATION, not an action. It records that this image listens
# on 8501. Actually opening it happens with -p at run time (section 9).
#
# EVERYDAY PARALLEL: the floor plan marks where the door is. It doesn't
# unlock it.
EXPOSE 8501

# ---- 9. Is it actually alive? -----------------------------------------------
# Runs periodically inside the container. If the command fails repeatedly the
# container is marked unhealthy, and compose can act on that.
#
# WHY it matters: a process can be "running" while being completely stuck.
# "Is the process alive?" and "is the service working?" are different
# questions, and only the second one matters.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# ---- 10. What runs when the container starts --------------------------------
# "Exec form" (a JSON list, not a plain string) so the app becomes the main
# process and receives stop signals properly. With the string form, a shell
# sits in between and swallows them, so the container takes 10 seconds to
# stop instead of stopping immediately.
#
# --server.address=0.0.0.0 is ESSENTIAL and catches everyone once: by default
# Streamlit listens only on "localhost", which inside a container means "only
# reachable from inside this container." 0.0.0.0 means "listen on all network
# interfaces," so traffic from outside can arrive.
CMD ["streamlit", "run", "app/streamlit_app.py", \
     "--server.address=0.0.0.0", \
     "--server.port=8501", \
     "--server.headless=true"]
```

---

## 6. Layers and caching: why the order matters

Every instruction in a Containerfile creates a **layer** — a saved snapshot of the
filesystem after that step. The image is those layers stacked.

*Everyday parallel:* **packing a suitcase.** Shoes at the bottom, then folded
clothes, then the things you'll want first on top. If you need to swap the item on
top, you lift one thing. If you need to swap the shoes, you unpack everything above
them.

Containers work the same way, and the engine caches every layer. **When you
rebuild, it reuses layers up to the first thing that changed, and rebuilds
everything after it.**

This is why the Containerfile copies `requirements.txt` and installs packages
*before* copying the application code:

| Order | You edit one line of Python… | Rebuild time |
|---|---|---|
| ✅ requirements first, code last | Only the code layer is invalid | **~2 seconds** |
| ❌ code first, requirements last | The install layer is invalid; every package reinstalls | **~3 minutes** |

Same image either way. Ninety times the wait. Over a project's life that's hours of
your time, decided by two lines being in the right order.

**The general rule:** put the things that change *least often* earliest.

### `.dockerignore` — what not to send

When you run a build, the engine first sends the whole folder to the build
process. Without filtering, that includes `.venv/` (hundreds of MB), `data/`
(potentially gigabytes), and `.git/`.

`.dockerignore` excludes them. Both Docker and Podman read it.

```gitignore
# ---------------------------------------------------------------
# What the container build must NOT receive
#
# WHY: everything here is either huge, secret, rebuildable, or
# irrelevant inside the container. Excluding it makes builds much
# faster and images much smaller — and prevents secrets ending up
# baked into a published image.
# ---------------------------------------------------------------

# Rebuilt inside the container from requirements.txt — and it would be
# the WRONG platform's binaries anyway (macOS packages in a Linux image).
.venv/
venv/

# Secrets — must NEVER be baked into an image. An image is shareable;
# treat anything inside it as public.
.env
.env.*
!.env.example
.streamlit/secrets.toml
*.pem
*.key

# Rebuilt by the pipeline; often gigabytes
data/
*.duckdb
*.db

# Version history — not needed at runtime, often the biggest folder
.git/
.github/

# Python working files
__pycache__/
*.py[cod]
.pytest_cache/
.ruff_cache/

# Docs and notebooks aren't needed to RUN the app
docs/
notebooks/
figures/

# Editor and OS clutter
.vscode/
.idea/
.DS_Store
```

> ⚠️ **The most important line in that file is `.env`.** An image is a shareable
> artifact. If you publish one with a secret baked in, that secret is public —
> and deleting the file in a later layer does **not** remove it, because it's
> still in the earlier layer. Anyone can extract it. This is one of the most
> common real-world container security failures.

---

## 7. Multi-stage builds: don't ship the mixing bowls

Some services need tools to *build* that they don't need to *run*. The React
frontend is the clearest case: building it needs Node.js, npm, and hundreds of
megabytes of packages. Running it needs only the handful of finished files a web
server hands out.

*Everyday parallel:* baking a cake needs mixing bowls, scales, a stand mixer and a
messy worktop. **Serving it needs a plate.** You don't deliver the kitchen with the
cake.

A **multi-stage build** uses one image to build and a second, minimal image to run,
copying only the finished result across:

```dockerfile
# ==============================================================================
# MicrobeGraph — the React frontend, multi-stage
# ==============================================================================

# ---- STAGE 1: the messy kitchen ---------------------------------------------
# "AS builder" names this stage so stage 2 can reach into it.
FROM node:20-slim AS builder
WORKDIR /build

# Dependencies first (same caching logic as before)
COPY frontend/package*.json ./
RUN npm ci                      # "ci" = exact versions from the lockfile

COPY frontend/ ./
RUN npm run build               # produces a /build/dist folder of static files

# ---- STAGE 2: the plate -----------------------------------------------------
# A fresh, tiny image. Nothing from stage 1 comes along except what we copy.
FROM nginx:alpine

# Reach back into the builder stage and take ONLY the finished files.
# Node.js, npm, node_modules — all left behind.
COPY --from=builder /build/dist /usr/share/nginx/html
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
```

**The result:** a build image of roughly 1.2 GB produces a final image of roughly
25 MB. Fifty times smaller, with fifty times less surface area for a security
problem.

*What is nginx?* A small, very fast web server. Its job here is to hand finished
HTML, CSS and JavaScript files to browsers. *Everyday parallel:* the person at the
counter passing over pre-made sandwiches — no cooking, just fast, reliable
handover.

---

## 8. Volumes: data must outlive the container

**Containers are disposable.** Stop one and everything written inside it vanishes.

That's a feature, not a bug — it's what makes them reproducible. But a database
that forgets everything on restart is useless.

*Everyday parallel:* a container is a **hotel room**. You use it, you leave, it's
cleaned to a standard state for the next guest. Anything you want to keep goes in
your **suitcase**, which leaves with you.

A **volume** is the suitcase: storage that lives on the host and is mounted into
the container.

```bash
# Docker
docker run -v microbegraph-data:/var/lib/postgresql/data postgres:16

# Podman on RHEL — note the :Z, explained in section 14
podman run -v microbegraph-data:/var/lib/postgresql/data:Z postgres:16
```

Two kinds, and the distinction matters:

| Kind | Looks like | Use it for | Everyday parallel |
|---|---|---|---|
| **Named volume** | `microbegraph-data:/path` | Databases, anything the app owns | A storage locker the engine manages for you |
| **Bind mount** | `./local/path:/path` | Live-editing code during development | A window onto a folder on your own desk |

**In development**, bind-mounting your source code means edits appear inside the
running container instantly — no rebuild. **In production**, you never bind-mount
code: the whole point is that the image contains a fixed, known version.

---

## 9. Networks and ports: how services find each other

### Inside: services call each other by name

When compose starts several containers it puts them on a private network where
**each service is reachable by its service name**.

So the API connects to the database at `postgres:5432` — not an IP address, not
`localhost`. The name `postgres` is the service's name in the compose file.

*Everyday parallel:* an office internal phone system. You dial "Accounts", not a
full external number. The system knows where Accounts sits, and it still works
after they move desks.

**Why this is genuinely better than IP addresses:** container IPs change on every
restart. Names don't. This is why the compose file has a service literally named
`postgres` — that name *is* the address.

### Outside: publishing a port

Nothing inside the private network is reachable from your browser until you
**publish** a port:

```bash
docker run -p 8501:8501 microbegraph-app
#             ^^^^ ^^^^
#             │    └── the port INSIDE the container
#             └── the port on YOUR machine
```

*Everyday parallel:* the hotel again. Every room has a phone (the internal port).
Only rooms the front desk will connect a call to are reachable from outside (the
published port). `-p 9000:8501` means "outside callers dial 9000, connect them to
the app's 8501" — useful when 8501 is already taken.

**The security point:** only publish what genuinely needs to be reachable. In
MicrobeGraph's stack, the frontend and API are published; **the database is not**.
It's reachable by the API over the internal network and invisible from outside.
That's a deliberate decision, and it's the default posture you should adopt.

---

## 10. Secrets in containers

Three rules, in order of importance:

**1. Never bake a secret into an image.** Covered above — layers keep everything,
and images are shareable.

**2. Pass secrets at run time, from a file the container reads.** Compose does
this from `.env`, which is gitignored:

```yaml
services:
  api:
    environment:
      DATABASE_URL: postgresql://microbegraph:${POSTGRES_PASSWORD}@postgres:5432/microbegraph
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:-}   # ":-" = empty if unset, don't fail
```

The `${...}` values come from `.env` on the host. The image contains only the
*shape*, never a value.

**3. Provide a `.env.example` with empty placeholders.** Committed, so anyone
knows what's needed; harmless, because it holds nothing.

The `:-` fallback on the API key is what makes the AI layer **degrade
gracefully**: no key means that one feature hides itself and the stack still
starts. A container that refuses to boot because an optional feature has no key is
badly designed.

---

## 11. Health checks and start order

Here's a trap that catches everyone the first time.

You tell compose the API depends on the database. Compose starts the database
first, then the API. The API immediately crashes: *connection refused*.

**Why:** the database *container* started in a second. The database *program*
inside it takes fifteen seconds to be ready for connections. "Started" and "ready"
are different things.

*Everyday parallel:* you switch the kettle on and immediately pour. Switching on
isn't boiling. You have to **wait for the click.**

A **health check** is the click:

```yaml
services:
  postgres:
    image: postgres:16
    healthcheck:
      # pg_isready is Postgres's own "are you ready for connections?" command
      test: ["CMD-SHELL", "pg_isready -U microbegraph"]
      interval: 5s
      timeout: 5s
      retries: 10
      start_period: 10s        # grace period before failures start counting

  api:
    depends_on:
      postgres:
        condition: service_healthy    # ← wait for the CLICK, not the switch
```

`condition: service_healthy` is the line that matters. Without it, `depends_on`
only waits for *started*, which is almost never what you want.

**Belt and braces:** the API should *also* retry its first connections. Health
checks handle the normal case; retries handle the abnormal one. Real systems do
both, because the database can also restart later, long after startup.

---

## 12. Step two: the whole stack with compose (Phase 18)

**Compose** describes every service in one file and runs them together.

*Everyday parallel:* a Containerfile is a recipe for one dish. A compose file is
the **menu plus the kitchen rota** — what gets made, which station makes it, what
each needs, and in what order.

```yaml
# ==============================================================================
# MicrobeGraph — the whole application, one file
#
# RUN:   docker compose up          (or: podman compose up)
# STOP:  docker compose down
# WIPE:  docker compose down -v     ⚠️ -v also deletes the volumes (your data)
#
# Reads secrets from .env (gitignored). Copy .env.example to .env first.
# ==============================================================================

services:

  # ---- The database ---------------------------------------------------------
  postgres:
    # Apache AGE ships a Postgres image with the graph extension preinstalled,
    # so we don't compile anything. Pinned to a version, never "latest" —
    # "latest" means "whatever it happens to be today", which is the opposite
    # of reproducible.
    image: apache/age:PG16_latest
    environment:
      POSTGRES_USER: microbegraph
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?set POSTGRES_PASSWORD in .env}
      POSTGRES_DB: microbegraph
    volumes:
      # The suitcase: survives container removal. :Z is for SELinux (RHEL).
      - microbegraph-db:/var/lib/postgresql/data:Z
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U microbegraph"]
      interval: 5s
      timeout: 5s
      retries: 10
      start_period: 10s
    # DELIBERATELY NO "ports:" — the database is reachable by the other
    # services on the internal network and INVISIBLE from outside. Publish it
    # only if you need to connect a desktop SQL client, and only temporarily.
    restart: unless-stopped

  # ---- The API: the shared service layer ------------------------------------
  api:
    build:
      context: .
      dockerfile: api/Containerfile
    environment:
      # "postgres" is the SERVICE NAME above — the internal phone directory
      DATABASE_URL: postgresql://microbegraph:${POSTGRES_PASSWORD}@postgres:5432/microbegraph
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:-}      # optional; empty is fine
    ports:
      - "8000:8000"        # published: the frontend and you both call it
    depends_on:
      postgres:
        condition: service_healthy    # wait for the click
    healthcheck:
      test: ["CMD", "curl", "--fail", "http://localhost:8000/health"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 15s
    restart: unless-stopped

  # ---- The Streamlit app: the analyst's workbench ---------------------------
  app:
    build:
      context: .
      dockerfile: Containerfile
    environment:
      MICROBEGRAPH_API_URL: http://api:8000      # by name again
    ports:
      - "8501:8501"
    depends_on:
      api:
        condition: service_healthy
    restart: unless-stopped

  # ---- The React frontend: the public product ------------------------------
  frontend:
    build:
      context: .
      dockerfile: frontend/Containerfile
    ports:
      - "3000:80"          # nginx listens on 80 inside; we publish it as 3000
    depends_on:
      api:
        condition: service_healthy
    restart: unless-stopped

# ---- Named volumes ----------------------------------------------------------
# Declared here, managed by the engine, and NOT deleted when containers are
# removed — only by an explicit "down -v".
volumes:
  microbegraph-db:
```

### Running it

```bash
# 1. One-time: create your .env from the template and set a password
cp .env.example .env          # Windows: copy .env.example .env

# 2. Start everything (add -d to run in the background)
docker compose up             # or: podman compose up

# 3. Watch it come up
#    postgres  ... healthy
#    api       ... healthy
#    app       ... started
#    frontend  ... started

# 4. Open:
#    http://localhost:3000   the React product
#    http://localhost:8501   the Streamlit workbench
#    http://localhost:8000/docs   the API's own interactive documentation

# 5. Stop (data survives)
docker compose down

# 6. Stop AND delete the data  ⚠️
docker compose down -v
```

### Everyday commands

```bash
docker compose ps                  # what's running, and is it healthy?
docker compose logs -f api         # follow one service's log output
docker compose restart api         # restart one service
docker compose up -d --build api   # rebuild and restart one service
docker compose exec api bash       # open a shell INSIDE a running container
```

That last one is the debugging workhorse. *Everyday parallel:* instead of guessing
why the dishwasher isn't working, you open the door and look inside.

---

## 13. Docker vs Podman: the differences that actually bite

Podman mirrors Docker's interface closely, so most things are one word apart. Here
is every difference that will actually affect you, honestly listed.

| Topic | Docker | Podman | Does it matter? |
|---|---|---|---|
| Build | `docker build` | `podman build` | No — identical |
| Run | `docker run` | `podman run` | No — identical |
| Recipe file | `Dockerfile` | `Containerfile` | No — both engines read both names |
| Compose | `docker compose up` (built in) | `podman compose up` (needs `podman-compose` or `podman-docker`) | **Slightly** — one extra install |
| Background service | A root daemon, always running | **No daemon** | Podman is simpler and safer |
| Privileges | Effectively root | **Rootless by default** | Podman wins on shared machines |
| Ports below 1024 | Fine | Blocked when rootless | **Yes** — see section 14 |
| SELinux volumes | N/A | Needs `:Z` on RHEL | **Yes** — see section 14 |
| Auto-start on boot | `restart: unless-stopped` | Same, plus systemd/Quadlet | Podman integrates better with Linux servers |
| Licence | Free personally; **paid in larger companies** | **Always free, open source** | Often the deciding factor |

### Making one set of files work with both

Three small decisions, applied throughout this project:

1. **Name the recipe `Containerfile`.** Both engines read it; the name is
   vendor-neutral.
2. **Publish only ports above 1024** (8000, 8501, 3000). Never 80 or 443
   directly. Rootless Podman can't bind low ports without extra configuration,
   and there's no reason to need them in development.
3. **Add `:Z` to volume mounts.** Docker ignores it entirely; Podman on RHEL needs
   it. One flag, both engines happy.

With those three, `docker compose up` and `podman compose up` do the same thing
from the same files. **No separate Podman version of anything.**

### Installing podman-compose

```bash
# RHEL 8 / Rocky
sudo dnf install -y podman-compose

# macOS
brew install podman-compose

# Any platform, via pip (works everywhere)
pip install podman-compose
```

Alternatively `sudo dnf install podman-docker` provides a `docker` command that
calls Podman, so literal `docker compose` commands work unchanged. Slightly
magical, very convenient.

---

## 14. RHEL 8 specifics: SELinux, rootless ports, and autostart

RHEL 8 is where the container gotchas live, so they get their own section.

### SELinux and the `:Z` flag

**What SELinux is:** an extra security layer in Red Hat Linux that labels every
file and enforces which processes may touch which labels. It's on by default and
it's a genuinely good thing.

*Everyday parallel:* a building where every room has a colour-coded badge reader.
Your badge opens rooms of your colour. Very effective — and confusing the first
time you're handed a badge and told a door "should" work.

**The symptom:** you mount a folder into a container and the container gets
`Permission denied` — even though the file permissions look completely fine. The
*permissions* are fine; the *SELinux label* is wrong.

**The fix:** append `:Z` to the mount.

```bash
podman run -v ./data:/app/data:Z microbegraph-app
```

`:Z` tells Podman to relabel that content so this container can access it. Docker
ignores the flag harmlessly, so **you can leave it in every mount and both engines
work**. That's why every volume in this project's compose file carries it.

*(Capital `:Z` = private to this container. Lowercase `:z` = shared between
containers. Use capital unless two containers genuinely need the same folder.)*

### Ports below 1024

Rootless Podman cannot bind ports under 1024 — a Linux rule that reserves them for
privileged processes.

**Our answer:** don't need them. Every published port in this project is above
1024. If you eventually want port 80 on a server, put a reverse proxy in front
rather than weakening the rule.

### Starting automatically on boot

On a RHEL server you'll want the stack to come back after a reboot. Podman
integrates with **systemd**, Linux's service manager:

```bash
# Generate a systemd unit from a running container
podman generate systemd --new --name microbegraph-app \
    > ~/.config/systemd/user/microbegraph-app.service

systemctl --user daemon-reload
systemctl --user enable --now microbegraph-app.service

# Let your user's services run without you being logged in
sudo loginctl enable-linger $USER
```

*(Newer Podman versions prefer **Quadlet**, a tidier file-based approach. The
Phase 18 guide will show whichever is current when we get there — this is exactly
the kind of detail worth re-checking rather than trusting a year-old memory.)*

That last `loginctl` line is easily missed: without it, your user's services stop
when you log out. *Everyday parallel:* leaving the office and having the lights
you switched on turn themselves off — fine for lights, not for a server.

---

## 15. Step three: publishing images (Phase 19)

Building by hand gets old. **A registry** is a place images live so others can pull
them without building anything.

*Everyday parallel:* a registry is an app store for images. `docker pull` is
"install".

MicrobeGraph publishes to **GitHub Container Registry (GHCR)** — free for public
repositories and already tied to your GitHub account.

Phase 19 adds a GitHub Actions workflow that, on every push to `master`:

1. Runs the test suite (so a broken image is never published)
2. Builds each image
3. Tags them with the version and the commit
4. Pushes them to `ghcr.io/akannan2987/microbegraph`

After which anyone can run the app with **no clone, no build, no Python**:

```bash
docker run -p 8501:8501 ghcr.io/akannan2987/microbegraph-app:latest
```

**Multi-platform builds** are worth knowing about: Apple Silicon Macs are ARM,
most servers are x86. `docker buildx` builds both from one command, so the same
tag works on either. Without it, a Mac-built image fails on a server with a
confusing `exec format error`.

---

## 16. Security and size: doing it properly

Applied throughout, each with its reason:

| Practice | Why | Where |
|---|---|---|
| Non-root user | Limits the damage if something is compromised | `USER appuser` |
| `slim` / `alpine` bases | ~150 MB instead of ~1 GB; fewer components, fewer vulnerabilities | `FROM python:3.12-slim` |
| Multi-stage builds | Build tools never reach the final image | Frontend, ~50× smaller |
| Pinned versions | `latest` changes silently; reproducibility requires exact | `postgres:16`, not `postgres` |
| No secrets in images | Layers keep everything, forever, publicly | `.dockerignore` + runtime env |
| Database not published | Reachable internally, invisible externally | No `ports:` on `postgres` |
| Health checks | "Running" and "working" are different questions | Every service |
| `.dockerignore` | Faster builds, smaller images, no accidental secrets | Repository root |
| Image scanning | Finds known vulnerabilities in your base image | `docker scout` / `trivy`, Phase 19 |

**Rough sizes to expect:** the app image ~450 MB (Python plus scientific libraries
are simply large), the frontend ~25 MB (multi-stage), the database ~400 MB
(official image). Total around 900 MB — normal for a stack like this, and a useful
number to sanity-check your own build against.

---

## 17. Troubleshooting

### "Cannot connect to the Docker daemon"

Docker Desktop isn't running. Start it, wait for the whale to settle. Linux with
Docker Engine: `sudo systemctl start docker`.

### Podman: "short-name resolution enforced but cannot prompt without a TTY"

Podman wants fully-qualified image names. Use `docker.io/library/postgres:16`
instead of `postgres:16`, or add `docker.io` to `unqualified-search-registries` in
`/etc/containers/registries.conf`.

### "port is already allocated"

Something else is using that port. Find it, or publish a different one:

```bash
docker compose down                 # often it's your own previous run
# or change the LEFT number only:  "9501:8501"
```

### The app starts but the browser shows nothing

Almost always the `0.0.0.0` mistake. A server bound to `localhost` inside a
container is reachable only from inside that container. Check your start command
includes `--server.address=0.0.0.0` (Streamlit) or `--host 0.0.0.0` (uvicorn).

### `Permission denied` on a mounted folder (RHEL)

SELinux. Add `:Z` to the mount — see [section 14](#14-rhel-8-specifics-selinux-rootless-ports-and-autostart).

### API can't reach the database

Three usual causes, in order of likelihood:

1. Using `localhost` in the connection string. Inside a container `localhost` is
   *that container*. Use the service name: `postgres`.
2. Missing `condition: service_healthy`, so the API started before the database
   was ready.
3. Password mismatch between `.env` and what Postgres was first initialised with.
   **Note:** Postgres only reads `POSTGRES_PASSWORD` when creating a *brand-new*
   data directory. Changing it later has no effect unless you also remove the
   volume — a genuinely confusing behaviour worth knowing about.

### Build is slow every single time

Your `COPY` order is wrong, or `.dockerignore` is missing. See
[section 6](#6-layers-and-caching-why-the-order-matters).

### "no space left on device"

Images accumulate:

```bash
docker system prune -a        # or: podman system prune -a
docker volume ls              # check volumes separately — prune -a doesn't touch them
```

⚠️ Removes unused images and stopped containers. Safe here (everything rebuilds),
but read the prompt.

### `exec format error`

Architecture mismatch — an ARM image on an x86 machine or vice versa. Rebuild on
the target, or use `docker buildx` for multi-platform images.

---

## 18. Checkpoint

You've understood this document when you can answer these without scrolling up:

1. What problem does containerizing solve that `.venv` does not?
2. Why does the Containerfile copy `requirements.txt` before the application code?
3. What is a multi-stage build, and what does it save?
4. Why does a database need a volume?
5. Inside compose, how does the API address the database — and why not by IP?
6. What does `condition: service_healthy` do that plain `depends_on` doesn't?
7. Name three things that make one set of files work under both Docker and Podman.
8. Why must a secret never be baked into an image, even if deleted in a later
   layer?

<details>
<summary>Answers (open after you've tried)</summary>

1. `.venv` seals Python *packages*. A container seals the Python itself, the
   operating-system libraries beneath it, and the system tools — the whole
   kitchen, not just the ingredients.
2. Layer caching. Dependencies change rarely, code changes constantly. This order
   means a code edit rebuilds in ~2 seconds instead of ~3 minutes.
3. Using one image to build and a second, minimal one to run, copying only the
   finished output across. The frontend goes from ~1.2 GB to ~25 MB — and the
   build tools never reach production.
4. Containers are disposable; anything written inside vanishes on removal. A
   volume is the suitcase that leaves the hotel room with you.
5. By service name (`postgres:5432`), like dialling "Accounts" on an office phone
   system. Container IP addresses change on every restart; names don't.
6. Plain `depends_on` waits for *started*. `service_healthy` waits for *ready* —
   the kettle's click, not the switch. Postgres takes seconds to accept
   connections after its container starts.
7. Name the file `Containerfile`; publish only ports above 1024; add `:Z` to
   volume mounts (Docker ignores it, Podman on RHEL needs it).
8. Images are layered and shareable. A file deleted in a later layer is still
   present in the earlier one and can be extracted. Anything in a published image
   is effectively public.

</details>

**What you learned:** the three sizes of the "works on my machine" problem; images
versus containers versus registries; layers and why instruction order changes
build times by 90×; multi-stage builds; volumes and the disposability of
containers; how services find each other by name; publishing ports and why the
database isn't; secrets at run time rather than build time; health checks and the
difference between started and ready; compose as the whole-stack description; and
the specific Docker/Podman differences that actually matter, including SELinux on
RHEL.

That's a genuinely substantial foundation, and it transfers to every containerized
system you'll ever meet.

---

## 19. Committing this phase

```bash
# safety first, before staging anything
pytest -q                     # once tests exist
./check-public-safe.sh        # must print "SAFE TO PUSH"

git switch develop
git add -A
git commit -m "feat: containerize the application (Docker + Podman)"
git push origin develop develop:beta develop:master

## --tags is optional, and only when cutting a new version
## then switch back to local master and pull in the changes from the remote

git switch master
git pull --ff-only origin master
git switch develop
```

> **Extra care for this phase:** run `./check-public-safe.sh` *before* building
> any image, not just before pushing. A `.env` that slipped past `.dockerignore`
> ends up inside a shareable artifact, which is a worse leak than a Git commit —
> a commit can be rewritten, but a pulled image is already on someone else's disk.

---

**Related:** [`CONTAINERS.md`](CONTAINERS.md) (choosing a runtime) ·
[`ROADMAP.md`](ROADMAP.md) (where this sits in the plan) ·
[`01-setup.md`](01-setup.md) (the non-container path, always supported)
