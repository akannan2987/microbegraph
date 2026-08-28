# 01 — Setup: from a blank laptop to a working workshop

**Prerequisites:** a computer running **Windows 10/11**, **macOS**, or
**Linux (RHEL 8 / Rocky / AlmaLinux)**, an internet connection, and permission
to install software. **No prior programming experience is assumed.** If you have
never opened a terminal in your life, you are the reader this document was
written for.

**Learning goal:** by the end you will have a terminal you're comfortable in,
Python installed and verified, a code editor, Git configured, a GitHub account,
an empty MicrobeGraph repository with three branches (`master`, `beta`,
`develop`), a sealed Python toolbox for this project, and a safety gate that
stops you from ever publishing a secret. You will also understand *why* each of
those exists.

**Time:** 60–90 minutes the first time. **You do this once per machine.** After
that, day-to-day work is three or four short commands.

**Checkpoint at the end:** a `check-setup` command that verifies every piece.

> Every term here is also in [`GLOSSARY.md`](GLOSSARY.md).

---

## Contents

1. [How to read this document](#1-how-to-read-this-document)
2. [Step 0 — The terminal, explained](#2-step-0--the-terminal-explained)
3. [Step 1 — Install Python](#3-step-1--install-python)
4. [Step 2 — Install a code editor (VS Code)](#4-step-2--install-a-code-editor-vs-code)
5. [Step 3 — Install and configure Git](#5-step-3--install-and-configure-git)
6. [Step 4 — Create your GitHub account](#6-step-4--create-your-github-account)
7. [Step 5 — Connect your computer to GitHub](#7-step-5--connect-your-computer-to-github)
8. [Step 6 — Create the project folder](#8-step-6--create-the-project-folder)
9. [Step 7 — The virtual environment](#9-step-7--the-virtual-environment-what-and-why)
10. [Step 8 — Install the project's packages](#10-step-8--install-the-projects-packages)
11. [Step 9 — Protect your secrets before you have any](#11-step-9--protect-your-secrets-before-you-have-any)
12. [Step 10 — The three-branch model](#12-step-10--the-three-branch-model)
13. [Step 11 — Your first push](#13-step-11--your-first-push)
14. [Step 12 — Verify everything](#14-step-12--verify-everything)
15. [Your daily rhythm from now on](#15-your-daily-rhythm-from-now-on)
16. [Troubleshooting](#16-troubleshooting)
17. [Checkpoint](#17-checkpoint)

---

## 1. How to read this document

**Rules of engagement:**

1. **One step at a time, in order.** Later steps assume earlier ones worked.
2. **Type commands rather than pasting them,** at least at first. Typing is
   slower and teaches your fingers what the words are. Paste once you're bored.
3. **Always check the expected output.** Every command below shows what success
   looks like. If yours differs, stop and check
   [Troubleshooting](#16-troubleshooting) before continuing. Pushing on past a
   failed step is the single most common way beginners get stuck for hours.
4. **Errors are information, not failure.** Every practitioner reads error
   messages all day. The skill is not "avoid errors"; it's "read the error,
   identify which step it belongs to, fix that step."

**Notation used throughout:**

- Lines starting with `$` are commands you type (don't type the `$` itself).
- <kbd>Enter</kbd> means press the Enter/Return key.
- Where operating systems differ, you'll see three clearly labelled blocks. **Do
  only the one for your machine.**

---

## 2. Step 0 — The terminal, explained

### What it is

A **terminal** (also "command line", "shell", "console") is a window where you
type instructions to your computer as text instead of clicking.

*Everyday example:* clicking through folders is like wandering a supermarket
looking for pasta. The terminal is handing the assistant a written list. Slower
to learn, far faster once you know it — and, crucially, **a written list can be
handed to someone else and produce the same result.** That reproducibility is
why every serious data project lives here.

You will not need many commands. Realistically, five do 90% of the work.

### Open it

**Windows** — press <kbd>Win</kbd>, type `PowerShell`, press <kbd>Enter</kbd>.
Use **PowerShell**, not the older "Command Prompt"; every Windows command in
this tutorial assumes PowerShell.

**macOS** — press <kbd>Cmd</kbd>+<kbd>Space</kbd>, type `Terminal`, press
<kbd>Enter</kbd>.

**Linux (RHEL 8)** — <kbd>Ctrl</kbd>+<kbd>Alt</kbd>+<kbd>T</kbd>, or find
"Terminal" in the applications menu. On a headless VM you're already there when
you SSH in.

### The five commands you actually need

Try each one now. They're all harmless.

```bash
pwd
```
*"Print working directory" — where am I right now?* Expected output is a path:

```
/Users/yourname          # macOS
/home/yourname           # Linux
C:\Users\yourname        # Windows PowerShell
```

```bash
ls
```
*List what's in this folder.* Expected: names like `Documents`, `Downloads`.
(On Windows PowerShell, `ls` works and so does `dir`.)

```bash
cd Documents
```
*"Change directory" — go into the Documents folder.* No output means success.
**Silence is success** is a general rule in terminals: tools print when
something's wrong, not when things are fine.

```bash
cd ..
```
*Go up one level.* Two dots always mean "the folder above this one".

```bash
mkdir practice
```
*Make a folder called `practice`.* Run `ls` to see it appeared. You can delete
it in your normal file browser afterwards.

**Three habits that will save you real time:**

- Press <kbd>Tab</kbd> to autocomplete names. Type `cd Doc` then <kbd>Tab</kbd>.
  It completes to `Documents`. This prevents typos, which are the #1 cause of
  "command not found".
- Press <kbd>↑</kbd> to bring back the previous command. Endlessly useful.
- Press <kbd>Ctrl</kbd>+<kbd>C</kbd> to cancel a command that's hanging.

**You now know enough terminal for this entire project.** Everything else is
copy, check the output, continue.

---

## 3. Step 1 — Install Python

### What Python is, and why this project uses it

**Python** is a programming language — a way of writing instructions a computer
can follow. It's used here because it's unusually readable (its code looks close
to English), it's free, it runs identically on Windows, macOS and Linux, and
every library MicrobeGraph needs — graphs, databases, web apps, AI — already
exists in it.

*Everyday example:* choosing a language for a project is like choosing a
language to write a manual in. You pick the one your readers and your reference
material already speak. In data work, that's Python.

We target **Python 3.12**. Version numbers matter: 3.12 and 3.9 differ in ways
that break libraries.

**Use Python 3.11 or 3.12.** (3.10 and 3.13 also work for the core project, but
3.11 and 3.12 have pre-built versions of every package this project uses,
including the Phase 7 extras — so they are the choices that never bite you
later.)

**Check what you already have before installing anything** — see below. Machines
often have several versions, and using one you already own is faster and tidier
than adding another.

> ⚠️ **Do not use Python 3.14 (or whatever the newest release is).** This is a
> real trap and it catches almost everyone once. Many scientific packages
> contain compiled C code, and someone has to rebuild and test each of them for
> every new Python release. That takes **6–12 months**. Until then, `pip` finds
> no ready-made version, tries to compile from source, and fails with a wall of
> C compiler errors that look alarming and have nothing to do with you.
>
> *Everyday parallel:* buying a brand-new phone model on launch day. The phone
> is fine — half your favourite apps just haven't been updated for it yet.
>
> **The professional habit:** for data work, always run one or two versions
> behind the newest. Newest is for people testing the language itself. If you
> hit this, see [Troubleshooting T11](#t11-pip-fails-to-build-a-package-with-c-compiler-errors).

Python **2** is a different, long-dead language; never use it.

### First: check what you already have

**Do not install anything yet.** Many machines already have several Python
versions, and installing another when you don't need one just adds clutter.

Type `python` and press the <kbd>Tab</kbd> key twice (don't press Enter):

```bash
python⇥⇥
```

Your shell lists every matching command it can find:

```
python              python3.11          python3.13          python3.14
python3             python3.11-config   python3.13-config   python3.14-config
```

*What just happened:* pressing Tab twice asks the shell to show every installed
command starting with what you typed. **This is the fastest way to see which
Python versions a machine actually has**, and it's worth remembering for any
command, not just this one.

Read the list for a version in the **3.10–3.13** range:

- **See `python3.11` or `python3.12`?** You're done — skip the installation
  below entirely and use that name in Step 7. Note it down.
- **Only `python3.13`?** Usable, but see the note below before choosing it.
- **Only `python3.14` or nothing in range?** Install 3.12 using the instructions
  below.

> **On 3.13 specifically:** everything in `requirements.txt` works on it. But
> `gensim`, one of the two Phase 7 extras in `requirements-ml.txt`, was last
> released before 3.13 existed and has no pre-built version for it. If you have
> **3.11 or 3.12 available, prefer those** — otherwise you'll meet the same
> problem months from now, at Phase 7, instead of today.

**Windows note:** Tab-completion works differently in PowerShell. List your
versions with `py --list` instead.

### Install it (only if the check above found nothing suitable)

<details open>
<summary><b>🪟 Windows</b></summary>

1. Go to <https://www.python.org/downloads/windows/>
2. Scroll down to **Python 3.12.x** and download its "Windows installer
   (64-bit)". **Do not** click the big green button at the top of the page —
   that gives you the newest release, which is exactly what you don't want (see
   the warning above).
3. Run the installer. **Before clicking Install, tick the box at the bottom that
   says "Add python.exe to PATH".** This is the step everyone misses and the
   cause of most "python is not recognised" errors later.

   *What is PATH?* A list of folders your computer searches when you type a
   command name. If Python isn't on the list, typing `python` gets you "not
   recognised" even though Python is installed — like a phone book that doesn't
   list a number you own.
4. Click **Install Now**, wait, then **Close**.
5. **Close your PowerShell window and open a new one.** PATH changes only apply
   to terminals opened afterwards.

</details>

<details open>
<summary><b>🍎 macOS</b></summary>

macOS ships with an old Python that must not be used for projects. Install your
own.

**Option A — the installer (simplest):**
1. Go to <https://www.python.org/downloads/macos/>
2. Scroll down to **Python 3.12.x** and download its macOS 64-bit universal2
   installer. **Do not** click the big green button at the top — that gives you
   the newest release, which is exactly what you don't want (see the warning
   above).
3. Run it and accept the defaults.
4. It installs as `python3.12`, alongside any other version you have. Use that
   exact name when creating the virtual environment in Step 7.

**Option B — Homebrew** (if you already have it, or want a package manager):
```bash
brew install python@3.12
```

</details>

<details open>
<summary><b>🐧 Linux — RHEL 8 / Rocky / AlmaLinux</b></summary>

RHEL 8 ships with Python 3.6, which is too old. Install 3.12 alongside it —
**do not remove or replace the system Python**, because system tools depend on
it. (This is a real and common RHEL trap: replacing the system Python breaks
`yum`/`dnf` itself.)

```bash
sudo dnf install -y python3.12 python3.12-pip
```

If your RHEL 8 minor version doesn't offer `python3.12`, use `python3.11` or
`python3.9` — both work — and substitute that name everywhere `python3.12`
appears below:

```bash
sudo dnf install -y python3.11 python3.11-pip
```

*What is `dnf`?* RHEL's package manager — an app store for command-line
software. `sudo` means "run this as administrator". You'll be asked for your
password; the cursor won't move as you type it, which is normal.

</details>

### Verify it

**This is the pattern for the whole tutorial: install, then verify.** Never
assume.

```bash
python --version          # Windows, macOS
python3 --version         # macOS, Linux
python3.12 --version      # RHEL 8, if you installed 3.12 alongside
```

Expected output (your patch number may differ):

```
Python 3.12.7
```

✅ **Checkpoint.** You want a version between **3.10 and 3.13**, ideally
**3.12**. Note down which command produced it (`python`, `python3`, or
`python3.12`) — **you'll use that same word throughout this tutorial.** For the
rest of this document it is written as `python`; substitute yours.

⚠️ **If it says 3.14 or higher, stop and install 3.12** using the instructions
above. Continuing will work fine for several steps and then fail confusingly at
`pip install`. Installing 3.12 does **not** remove your other version — they
live side by side, and you simply use `python3.12` when creating the virtual
environment.

❌ If you see "command not found" or "not recognised", go to
[Troubleshooting T1](#t1-python-command-not-found).

---

## 4. Step 2 — Install a code editor (VS Code)

### Why not just use Notepad?

A **code editor** is a text editor that understands code. It colours the parts
of your program differently (so a typo often becomes visible before you run
anything), warns about mistakes as you type, and has a terminal built in so you
don't switch windows constantly.

*Everyday example:* writing a letter in Notepad versus in Word. Both produce
text. Only one tells you "you've misspelled this" while you write.

We use **VS Code**: free, made by Microsoft, identical on all three operating
systems, and by a wide margin the most common editor in this field.

### Install it

1. Go to <https://code.visualstudio.com/>
2. The site detects your system — click the big download button.
3. Install with defaults.
   - **Windows:** tick "Add to PATH" and "Open with Code" if offered.
   - **macOS:** drag it to Applications.
   - **RHEL 8:** the `.rpm` download, then
     `sudo dnf install -y ./code-*.rpm`
4. Open VS Code.
5. Click the **Extensions** icon in the left bar (four squares), search for
   **Python**, and install the one published by **Microsoft**.

   *What's an extension?* An add-on that teaches the editor about a specific
   language — like installing a dictionary for a language your word processor
   didn't know.

✅ **Checkpoint.** VS Code opens and the Python extension appears in your
installed list.

---

## 5. Step 3 — Install and configure Git

### What Git is, properly

**Git** is a system that records snapshots of your project over time.

*Everyday example:* saving in a video game. You save before the hard bit. If it
goes badly, you reload. Git is that, for your work — except every save is
permanent, labelled with a message explaining what changed, and you can compare
any two saves to see exactly what's different.

*Second everyday example:* the "Version history" in Google Docs, but you choose
when a version is created and you write a note saying why.

Three words you'll use constantly:

| Word | Plain meaning | Everyday parallel |
|---|---|---|
| **repository** ("repo") | The project folder Git is watching, plus its whole history | A document with its full version history |
| **commit** | One saved snapshot, with a message | Clicking "save a named version" |
| **branch** | A parallel line of work | A photocopy of the draft you can scribble on without touching the original |

**Git ≠ GitHub.** Git is the program on your computer. **GitHub** is a website
that stores copies of Git repositories online, so your work is backed up,
shareable, and readable by others. You can use Git with no GitHub at all — but
we want the backup and the public home.

### Install it

<details open>
<summary><b>🪟 Windows</b></summary>

1. Go to <https://git-scm.com/download/win> — the download starts automatically.
2. Run the installer. **Accept every default** — there are many screens and the
   defaults are correct for our purposes. The one worth noticing: it installs
   "Git Bash", an extra terminal. You can ignore it; PowerShell is enough.
3. Close and reopen PowerShell.

</details>

<details open>
<summary><b>🍎 macOS</b></summary>

```bash
git --version
```
If Git isn't installed, macOS offers to install the Developer Tools — accept,
and wait a few minutes. Otherwise: `brew install git`.

</details>

<details open>
<summary><b>🐧 Linux — RHEL 8</b></summary>

```bash
sudo dnf install -y git
```

</details>

### Verify

```bash
git --version
```

```
git version 2.43.0
```

Any 2.x version is fine.

### Configure your identity

Every commit is stamped with a name and email. Set them once per machine.

```bash
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

> **Privacy note:** this email is embedded in every public commit. If you'd
> rather not publish your real address, GitHub gives you a free no-reply one:
> after creating your account (next step), go to
> **Settings → Emails → Keep my email addresses private**, and it shows an
> address like `12345678+username@users.noreply.github.com`. Use that here
> instead. You can change this later at any time.

One more setting worth having:

```bash
# Make "master" the default branch name for new repositories.
# (Git's historical default; some newer installs default to "main".
#  This project uses master, so set it explicitly.)
git config --global init.defaultBranch master
```

### Optional: the fast-forward-only preference

There's one more setting some people like, and it's genuinely **optional** —
decide for yourself:

```bash
git config pull.ff only
```

**What it does.** "Fast-forward" means Git can update your branch by simply
moving its pointer along an existing line, with nothing to reconcile — the clean
case. `pull.ff only` says: *if a pull isn't that clean, stop and tell me rather
than inventing a merge commit I didn't ask for.*

*Everyday parallel:* the difference between a colleague adding paragraphs to the
end of your draft (just accept it) and a colleague rewriting your middle section
while you rewrote it too (someone has to decide what the document says). The
setting says "in the second case, ask me."

**Why it's optional here:** every `pull` in this project's documented workflow
already passes the flag explicitly —

```bash
git pull --ff-only origin master
```

— so the config adds nothing to *this* project. It only helps in repositories
where you might forget the flag.

**Choosing a scope.** Git config has three levels, and the most specific wins:

| Command | Applies to | When you'd want it |
|---|---|---|
| `git config pull.ff only` | **This repository only** (`.git/config`) | You like the safety net here but don't want to change how Git behaves elsewhere |
| `git config --global pull.ff only` | Your whole user account | You want it everywhere, always |
| *(don't set it)* | — | Perfectly fine; the workflow's explicit `--ff-only` covers you |

*Everyday parallel:* a house rule versus a rule for one room. "No shoes in the
flat" versus "no shoes in the bedroom."

**A recommendation, not a requirement:** the repository-scoped version is the
comfortable middle ground — protection where you're working, no side effects on
your other projects. But skipping it entirely is a legitimate choice, and this
tutorial works either way.

<details>
<summary><b>🪟 Windows only — one extra setting</b></summary>

Windows and Unix mark line endings differently, which can make Git report that
every line of a file changed when nothing did. This setting handles the
translation:

```powershell
git config --global core.autocrlf true
```

On macOS/Linux the equivalent (`input`) is already the sensible default.

</details>

Verify all of it:

```bash
git config --global --list
```

```
user.name=Your Name
user.email=your.email@example.com
init.defaultbranch=master
```

(You may see other lines too — Git installations and tools add their own
settings. That's normal. If you set `pull.ff` globally above, it appears here;
if you set it per-repository, it won't — check with `git config --list --local`
from inside the project instead.)

✅ **Checkpoint.** Your name and email appear.

---

## 6. Step 4 — Create your GitHub account

**GitHub** is where your repositories live online. Free, and the standard place
this kind of work is published and read.

1. Go to <https://github.com/> and click **Sign up**.
2. Choose a username you're happy for people to see — it becomes part of every
   URL (`github.com/yourname/microbegraph`). Something close to your real name
   is the norm.
3. Verify your email address.
4. The free plan is entirely sufficient. Public repositories are free and
   unlimited.

✅ **Checkpoint.** You can log in and see your (empty) profile page.

---

## 7. Step 5 — Connect your computer to GitHub

Your computer needs to prove it's you when it uploads. There are two ways.

### Option A — Personal Access Token (simplest; recommended to start)

A **Personal Access Token** (PAT) is a long password generated for programs
rather than humans. Your normal GitHub password won't work for Git operations —
this is deliberate, because a token can be limited in scope and revoked
individually without changing your account password.

1. Log in to GitHub.
2. Click your avatar (top right) → **Settings**.
3. Scroll to the bottom of the left sidebar → **Developer settings**.
4. **Personal access tokens** → **Tokens (classic)** → **Generate new token
   (classic)**.
5. **Note:** `microbegraph laptop`. **Expiration:** 90 days is a sensible
   balance. **Scopes:** tick **`repo`** only. Nothing else.
6. **Generate token**, then **copy it immediately** — GitHub shows it once and
   never again. Paste it somewhere safe (a password manager is ideal).

When Git asks for a password later, paste the token. To avoid re-pasting every
time, turn on the credential helper:

```bash
# Windows
git config --global credential.helper manager

# macOS
git config --global credential.helper osxkeychain

# Linux (RHEL 8) — caches in memory for 1 hour; nothing written to disk
git config --global credential.helper 'cache --timeout=3600'
```

> ⚠️ **Never** paste a token into a file inside your project, into code, or into
> a commit message. If you ever do by accident: go straight to GitHub → Settings
> → Developer settings → revoke the token, and generate a new one. Revoked
> tokens are dead instantly. This is exactly the accident
> `check-public-safe.sh` (Step 9) exists to prevent.

### Option B — SSH keys (nicer long-term)

An **SSH key** is a matched pair of files: a *private* key that never leaves
your machine and a *public* key you give GitHub. They prove your identity
without any password being sent.

*Everyday example:* a physical key and the lock it fits. You keep the key; the
lock is fitted to the door and is useless to a thief on its own.

```bash
# 1. Generate the pair (press Enter three times to accept defaults)
ssh-keygen -t ed25519 -C "your.email@example.com"

# 2. Show the PUBLIC key (safe to share — never show the one without .pub)
cat ~/.ssh/id_ed25519.pub          # macOS / Linux
type $env:USERPROFILE\.ssh\id_ed25519.pub    # Windows PowerShell
```

Copy the whole line (starts `ssh-ed25519`), then GitHub → Settings → **SSH and
GPG keys** → **New SSH key** → paste → **Add SSH key**.

Test it:

```bash
ssh -T git@github.com
```
```
Hi yourname! You've successfully authenticated, but GitHub does not provide shell access.
```
That message is success, despite how it reads.

✅ **Checkpoint.** You have either a token saved safely, or a working SSH key.

---

## 8. Step 6 — Create the project folder

### Create the repository on GitHub first

Creating it online first, then cloning it down, avoids a whole category of
"these two repositories don't know about each other" confusion.

1. GitHub → **+** (top right) → **New repository**.
2. **Repository name:** `microbegraph`
3. **Description:** `A knowledge graph of microbes, the molecules they make, and the crop diseases those molecules act on.`
4. **Public.**
5. ✅ **Add a README file** — this creates the first commit, so the repository
   isn't empty (an empty repo has no branches, which makes the next steps
   awkward).
6. **Add .gitignore:** choose **Python** from the dropdown. (We'll replace it
   with a fuller version in Step 9.)
7. **Choose a license:** **MIT**. It's the standard permissive licence — anyone
   may use your work provided they keep your copyright notice.
8. **Create repository.**

### Clone it to your computer

**Clone** = download a copy including its whole history, wired up to talk to the
original.

First decide where projects live on your machine, and be consistent:

```bash
# macOS / Linux
mkdir -p ~/projects
cd ~/projects

# Windows PowerShell
mkdir $HOME\projects
cd $HOME\projects
```

*What's `~` / `$HOME`?* Shorthand for your home folder. `~/projects` is
`/Users/you/projects` on macOS, `/home/you/projects` on Linux.

Now clone (replace `yourname`):

```bash
# If you chose a token (Option A)
git clone https://github.com/yourname/microbegraph.git

# If you chose SSH (Option B)
git clone git@github.com:yourname/microbegraph.git
```

```
Cloning into 'microbegraph'...
remote: Enumerating objects: 4, done.
remote: Counting objects: 100% (4/4), done.
remote: Total 4 (delta 0), reused 0 (delta 0), pack-reused 0
Receiving objects: 100% (4/4), done.
```

Go in and look:

```bash
cd microbegraph
ls -a
```

```
.  ..  .git  .gitignore  LICENSE  README.md
```

`.git` is the hidden folder holding the entire history. **Never edit or delete
it** — it *is* the repository. (The `-a` flag means "show hidden files"; on
Windows PowerShell use `ls -Force`.)

### Create the folder structure

These are empty scaffolding folders that later phases fill. Creating them now
means every future instruction has somewhere to go.

<details open>
<summary><b>🍎🐧 macOS / Linux</b></summary>

```bash
mkdir -p docs src/microbegraph sources curation artifacts app mcp tests notebooks data/raw data/processed figures
```
*(one command; `-p` creates parent folders as needed)*

</details>

<details open>
<summary><b>🪟 Windows PowerShell</b></summary>

```powershell
"docs","src/microbegraph","sources","curation","artifacts","app","mcp","tests","notebooks","data/raw","data/processed","figures" | ForEach-Object { New-Item -ItemType Directory -Force -Path $_ }
```

</details>

Git doesn't track empty folders, so drop a placeholder in the ones that must
exist in a fresh clone:

```bash
# macOS / Linux
touch artifacts/.gitkeep curation/.gitkeep tests/.gitkeep

# Windows PowerShell
New-Item -ItemType File -Force artifacts/.gitkeep, curation/.gitkeep, tests/.gitkeep
```

*Why?* `.gitkeep` isn't a Git feature — it's a convention. Git tracks files, not
folders, so a folder with one dummy file inside is how you make an "empty"
folder survive a clone.

✅ **Checkpoint.** `ls` shows the new folders.

---

## 9. Step 7 — The virtual environment: what and why

**This is the concept beginners skip and later regret. Read the why.**

### The problem it solves

Python libraries are installed on your machine and shared by everything. Project
A needs version 1.0 of a library; project B needs version 2.0. Install 2.0 and
project A breaks — with an error that has nothing obviously to do with the
install you just did. This is known, affectionately, as *dependency hell*.

*Everyday example:* one shared kitchen for a whole apartment block. Someone
replaces the flour with gluten-free. Your bread recipe now fails and you have no
idea why. A **virtual environment** is your own private kitchen cupboard: your
ingredients, your versions, nobody else's changes.

*Second everyday example:* a project toolbox instead of one giant shared garage.
Each project's toolbox holds exactly the tools that project needs, at the
versions it needs.

Concretely, a virtual environment (`venv`) is just a **folder** containing its
own copy of Python and its own libraries. It has two enormous benefits:

1. **Isolation** — projects can't break each other.
2. **Reproducibility** — you can write down exactly what's in the toolbox
   (`requirements.txt`) so anyone, anywhere, on any operating system, can build
   an identical one. That's what makes "clone this repo and run it" actually
   work.

### Create it

Run this **inside** the `microbegraph` folder:

```bash
# Use the exact version name you identified in Step 1.
python3.11 -m venv .venv        # macOS / Linux — if 3.11 is what you have
python3.12 -m venv .venv        # ...or 3.12
python -m venv .venv            # only if `python --version` already shows 3.11-3.12
# py -3.12 -m venv .venv        # Windows, choosing a specific version
```

⚠️ **Name the version explicitly rather than using bare `python`.** On a machine
with several versions installed, plain `python` may point at whichever one was
installed last — often the newest, which is exactly the one you don't want. Being
explicit here takes two extra characters and prevents the most common setup
failure in this whole document.

If you get `command not found`, that version isn't installed. Go back to Step 1
and use a name the Tab-completion check actually listed.

*Reading the command:* `-m venv` means "run the built-in module called venv";
`.venv` is the folder to create. The leading dot makes it hidden — by
convention, because it's machinery, not content.

No output means success.

### Activate it

**Activating** tells your terminal "for this session, use this project's
toolbox".

<details open>
<summary><b>🪟 Windows PowerShell</b></summary>

```powershell
.\.venv\Scripts\Activate.ps1
```

If you get a red error about "running scripts is disabled on this system", run
this once and try again:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

*What that does:* Windows blocks scripts by default as a safety measure.
`RemoteSigned` means "allow scripts I wrote locally; require a signature for
scripts downloaded from the internet." `-Scope CurrentUser` limits the change to
your account. It's a normal, safe setting for development.

</details>

<details open>
<summary><b>🍎🐧 macOS / Linux</b></summary>

```bash
source .venv/bin/activate
```

</details>

Your prompt now starts with `(.venv)`:

```
(.venv) yourname@laptop microbegraph %
```

**That prefix is your signal.** No `(.venv)` = you're outside the toolbox, and
`pip install` would put packages in the wrong place. Get in the habit of
glancing at it.

**You must activate once per terminal session** — every time you open a new
window to work on this project. It is not permanent, and that's by design.

To leave: `deactivate`.

### Verify

```bash
python -c "import sys; print(sys.prefix)"
```

The path printed should end with your project's `.venv`:

```
/home/yourname/projects/microbegraph/.venv
```

Also confirm the version inside the environment is the one you meant:

```bash
python --version
```
```
Python 3.11.9
```

✅ **Checkpoint.** Two things must be true: the path points inside your project's
`.venv`, and the version is in the 3.11–3.12 range. If the path points somewhere
else (like `/usr` or `C:\Python312`), the environment isn't active — re-run the
activate command. If the *version* is wrong, delete `.venv` and recreate it
naming the right Python: `rm -rf .venv` then `python3.11 -m venv .venv`.

---

## 10. Step 8 — Install the project's packages

### What a package is

A **package** (or library) is code someone else wrote and published so you don't
have to write it yourself.

*Everyday example:* buying flour instead of growing wheat. You *could* implement
graph algorithms from scratch. It would take months, and yours would be slower
and buggier than NetworkX, which hundreds of people have improved over twenty
years.

**pip** is Python's package installer — the thing that fetches and installs
them.

### The requirements file

Rather than installing packages one at a time and forgetting which, we list them
in `requirements.txt`. That file is the project's **receipt**: it lets anyone
rebuild an identical toolbox.

Create it in the project root (VS Code: **File → New File**, save as
`requirements.txt`):

```
# MicrobeGraph — core Python dependencies
#
# Install with:  pip install -r requirements.txt
#
# PYTHON VERSION: 3.11 or 3.12.
#   3.10 and 3.13 also run everything here, but the Phase 7 extras in
#   requirements-ml.txt have no build for 3.13 yet.
#   Python 3.14 is NOT supported: several packages have no pre-built version
#   for it, so pip tries to compile from source and fails.
#   See docs/01-setup.md -> Troubleshooting T11.
#
# ---------------------------------------------------------------------------
# HOW TO READ THE VERSION RANGES
#
#   pandas>=2.2,<4     means "at least 2.2, but below 4".
#
#   The LOWER bound guarantees the features this project relies on exist.
#   The UPPER bound stops a future major release from silently changing
#   behaviour underneath the code.
#
#   Why the upper bound matters: these projects follow "semantic versioning",
#   where the FIRST number changes only when something deliberately breaks.
#   pandas 2 -> 3 is allowed to remove functions and change defaults; 2.2 -> 2.9
#   is not. So an upper bound at the next major version is the line between
#   "safe improvements" and "we make no promises".
#
#   EVERYDAY PARALLEL: a recipe saying "any medium onion" is fine. Saying "any
#   vegetable" is not. The bounds describe the range where the recipe still works.
#
#   Ranges are used here rather than exact pins so the project keeps receiving
#   security and bug fixes. For byte-for-byte reproducibility, see
#   requirements.lock.txt and the explanation in docs/01-setup.md Step 8.
# ---------------------------------------------------------------------------

# --- Core data handling ---
pandas>=2.2,<4           # tables in Python ("programmable Excel")
numpy>=1.26,<3           # fast numeric arrays; pandas is built on it

# --- Getting data from the internet ---
requests>=2.32,<3        # fetch pages and APIs over HTTP
tenacity>=8.2,<10        # retry politely when a server is briefly busy

# --- Storage ---
duckdb>=1.0,<2           # the analytics database (one file, no server)

# --- The graph ---
networkx>=3.3,<4         # build and walk graphs; classic algorithms included

# --- Visualisation ---
matplotlib>=3.8,<4       # static charts (for docs and figures)
plotly>=5.22,<8          # interactive charts you can hover and zoom
pyvis>=0.3.2,<0.4        # interactive network views in the browser

# --- Machine learning (Phase 7) ---
scikit-learn>=1.9,<2     # models + honest evaluation (cross-validation, metrics)

# --- The app ---
streamlit>=1.36,<2       # turns a Python script into a web app

# --- Quality ---
pytest>=8.2,<10          # runs automated checks on our own code
ruff>=0.5,<1             # spots style problems and likely bugs

# --- Configuration ---
python-dotenv>=1.0,<2    # reads optional API keys from a .env file

# ---------------------------------------------------------------------------
# A NOTE ON THE 0.x PACKAGES (pyvis, ruff)
#   Before version 1.0, the rules are different: the SECOND number is the one
#   allowed to break things. So pyvis is capped at <0.4 rather than <1, because
#   0.3 -> 0.4 could change behaviour the way 3 -> 4 would elsewhere.
#   Reading a version number correctly is a small skill that saves real time.
# ---------------------------------------------------------------------------

# NOTE: the node-embedding libraries (gensim, node2vec) are NOT here.
# They are the most fragile dependencies in the stack — they contain compiled
# C code and break first on new Python versions — and nothing before Phase 7
# needs them. They live in requirements-ml.txt, installed only when you reach
# that phase. Keeping them out means a broken embedding library can never
# block someone from setting the project up.
```

> **Why there are two requirements files.** `requirements.txt` holds everything
> Phases 1–6 need. A second file, `requirements-ml.txt`, holds two node-embedding
> libraries used only in Phase 7. Those two contain compiled C code, which makes
> them the most fragile part of the stack — they are always the first to break on
> a new Python release. Keeping them separate means a broken library can never
> stop you setting the project up and completing six phases. **Separating what
> you need to start from what you need for one later feature is a habit worth
> carrying into every project you build.**

Install everything you need for now:

```bash
pip install -r requirements.txt
```

Expect a wall of scrolling text for 1–3 minutes, ending with something like:

```
Successfully installed duckdb-1.1.3 matplotlib-3.9.2 networkx-3.4.2 numpy-2.1.3
pandas-2.2.3 plotly-5.24.1 pytest-8.3.3 pyvis-0.3.2 requests-2.32.3 ruff-0.7.4
streamlit-1.40.1 tenacity-9.0.0 python-dotenv-1.0.1 ...
```

Version numbers will differ from these and that's expected — `>=` means "this or
newer".

### Lock the exact versions

You've just installed working versions of 74 packages. **Write down exactly which
ones**, so this environment can be recreated identically — by you on another
machine, by anyone cloning the repository, or by you in a year when the latest
versions have moved on.

```bash
pip freeze > requirements.lock.txt
```

No output means success. Open the file and you'll see exact versions, one per
line:

```
altair==6.2.2
attrs==26.1.0
duckdb==1.5.5
networkx==3.6.1
numpy==2.4.6
pandas==3.0.5
...
```

**Two files, two jobs — and this trips people up, so it's worth being clear:**

| File | Contains | Answers |
|---|---|---|
| `requirements.txt` | Ranges (`pandas>=2.2,<4`) | *What does this project need?* |
| `requirements.lock.txt` | Exact versions (`pandas==3.0.5`) | *What exactly was working on the day it was tested?* |

*Everyday parallel:* `requirements.txt` is the shopping list — "a medium onion,
plain flour". `requirements.lock.txt` is the till receipt — the exact brands and
sizes you actually bought, on that day, from that shop. The list lets someone
cook the dish. The receipt lets them reproduce your exact result.

**Which one do people install from?**

- **Normally, `requirements.txt`** — you want the bug fixes and security patches
  that arrive within the allowed range.
- **`requirements.lock.txt` when something is wrong** — if the project suddenly
  misbehaves after an update, installing the locked versions tells you instantly
  whether a dependency change caused it. That is an enormously useful diagnostic
  and the main reason to keep the file.

**Both are committed to Git.** Regenerate the lockfile whenever you deliberately
change dependencies — a one-line command at the end of any phase that adds a
package.

### Verify

```bash
python -c "import pandas, networkx, duckdb, streamlit, requests; print('all core packages import OK')"
```

```
all core packages import OK
```

✅ **Checkpoint.** That line appears with no error above it.

❌ If you see `ModuleNotFoundError`, see
[Troubleshooting T3](#t3-modulenotfounderror-after-installing).

---

## 11. Step 9 — Protect your secrets before you have any

### Why now, before there's anything to protect

Because the one time it matters, it's already too late. Git remembers
everything: a password committed once and deleted in the next commit is still
sitting in the history, publicly, forever. Bots scan GitHub for exactly this,
within minutes of a push.

Set the locks up first, while the house is empty. It takes five minutes.

### `.gitignore` — the lock on the door

`.gitignore` is a list of things Git must never track. Replace the file GitHub
created with this fuller version (VS Code: open `.gitignore`, select all,
paste):

```gitignore
# ---------------------------------------------------------------
# MicrobeGraph — what Git must never publish
# ---------------------------------------------------------------

# Secrets — API keys, tokens, anything private. NEVER commit these.
.env
.env.*
!.env.example
.streamlit/secrets.toml
*.pem
*.key

# The virtual environment — rebuildable from requirements.txt,
# large, and machine-specific. Never commit it.
.venv/
venv/
env/

# Data — rebuilt by the pipeline. Keeping it out of Git is the proof
# the pipeline works, and keeps the repository small.
data/
*.duckdb
*.duckdb.wal
*.db
*.sqlite

# Python's own working files
__pycache__/
*.py[cod]
*.egg-info/
.pytest_cache/
.ruff_cache/

# Notebook checkpoints
.ipynb_checkpoints/

# Operating-system clutter
.DS_Store          # macOS
Thumbs.db          # Windows
desktop.ini        # Windows
*~                 # Linux editor backups

# Private scratch space — personal working notes, never published.
# Anything in here stays on your machine only.
.dev/

# Editor settings
.vscode/
.idea/
```

Note `!.env.example` — the `!` means "except this one". The example file
contains no real secrets and *should* be published, so others know which keys
the project can use.

### `.env.example` — the template

Create `.env.example` in the project root:

```bash
# MicrobeGraph — optional API keys
#
# HOW TO USE:
#   1. Copy this file:   cp .env.example .env      (Windows: copy .env.example .env)
#   2. Fill in real values in .env
#   3. .env is gitignored and must NEVER be committed
#
# Everything here is OPTIONAL. The project runs fully without any of it —
# missing keys just mean slower fetching or a hidden AI feature.

# NCBI (optional). A free key raises the request rate limit from 3/sec to 10/sec.
# Get one: https://www.ncbi.nlm.nih.gov/account/  →  Account settings → API Key
NCBI_API_KEY=

# NCBI asks tools to identify themselves by email. Politeness, not security.
NCBI_EMAIL=

# Anthropic (optional). Only needed for the plain-English answer layer.
# Without it, that one feature hides itself and everything else works.
ANTHROPIC_API_KEY=
```

### `check-public-safe.sh` — the guard at the door

`.gitignore` is the lock. This script is the guard who checks your bag on the
way out — because locks can be misconfigured, and a second, independent check
costs nothing.

Create `check-public-safe.sh` in the project root:

```bash
#!/usr/bin/env bash
# ---------------------------------------------------------------
# MicrobeGraph — pre-push safety gate
#
# WHY THIS EXISTS:
#   .gitignore tells Git what to ignore. This script checks what Git
#   is ACTUALLY tracking, right now. Two independent checks, because a
#   secret published once is public forever.
#
# USAGE:  git add -A  &&  ./check-public-safe.sh      (run before every push)
#         Windows:  git add -A ; bash check-public-safe.sh
#
# RUN "git add -A" FIRST. This script inspects what Git is TRACKING
# (git ls-files). A brand-new file that has never been staged is invisible
# to Git, and therefore invisible to this check. Staging first means the
# gate inspects exactly what you are about to publish.
# ---------------------------------------------------------------

set -uo pipefail
problems=0

echo "MicrobeGraph pre-push safety check"
echo "-----------------------------------"

# --- 1. Is any secret-shaped file being tracked by Git? -----------
echo -n "1. Secret files not tracked ......... "
tracked_secrets=$(git ls-files | grep -E '(^|/)\.env$|secrets\.toml$|\.pem$|\.key$' || true)
if [ -n "$tracked_secrets" ]; then
  echo "FAIL"
  echo "   Git is tracking these secret files:"
  echo "$tracked_secrets" | sed 's/^/     /'
  echo "   Fix: git rm --cached <file>   then commit."
  problems=$((problems+1))
else
  echo "OK"
fi

# --- 2. Does any tracked file contain something that looks like a key? ---
echo -n "2. No key-shaped strings ............ "
# sk-ant-... = Anthropic; ghp_ = GitHub token; long quoted value after api_key.
# .env.example is excluded because it holds empty placeholders on purpose.
hits=$(git grep -nIE '(sk-ant-[A-Za-z0-9_-]{10,}|ghp_[A-Za-z0-9]{20,}|api[_-]?key[[:space:]]*=[[:space:]]*["'"'"'][A-Za-z0-9]{16,})' \
        -- ':!.env.example' ':!check-public-safe.sh' ':!docs/*' 2>/dev/null || true)
if [ -n "$hits" ]; then
  echo "FAIL"
  echo "$hits" | sed 's/^/     /'
  problems=$((problems+1))
else
  echo "OK"
fi

# --- 3. Is the data folder or a database being tracked? -----------
echo -n "3. Data/database not tracked ........ "
tracked_data=$(git ls-files | grep -E '^data/|\.duckdb$|\.sqlite$|\.db$' || true)
if [ -n "$tracked_data" ]; then
  echo "FAIL"
  echo "$tracked_data" | head -5 | sed 's/^/     /'
  echo "   Fix: git rm -r --cached data/   then commit."
  problems=$((problems+1))
else
  echo "OK"
fi

# --- 4. Any hard-coded local paths that would break for others? ---
echo -n "4. No hard-coded local paths ........ "
paths=$(git grep -nIE '(/Users/[a-zA-Z]|/home/[a-zA-Z]|C:\\\\Users\\\\)' \
        -- ':!docs/*' ':!check-public-safe.sh' ':!README.md' 2>/dev/null || true)
if [ -n "$paths" ]; then
  echo "WARN"
  echo "$paths" | head -5 | sed 's/^/     /'
  echo "   These work on your machine only. Use relative paths instead."
else
  echo "OK"
fi

# --- 4b. Is the private scratch folder being tracked? -------------
echo -n "4b. Private .dev/ not tracked ....... "
if git ls-files | grep -qE '^\.dev/'; then
  echo "FAIL"
  echo "   .dev/ holds personal working notes and must never be published."
  echo "   Fix: git rm -r --cached .dev   then commit."
  problems=$((problems+1))
else
  echo "OK"
fi

# --- 5. Is the virtual environment being tracked? -----------------
echo -n "5. .venv not tracked ................ "
if git ls-files | grep -qE '^\.venv/'; then
  echo "FAIL"
  echo "   Fix: git rm -r --cached .venv   then commit."
  problems=$((problems+1))
else
  echo "OK"
fi

echo "-----------------------------------"
if [ "$problems" -eq 0 ]; then
  echo "SAFE TO PUSH"
  exit 0
else
  echo "NOT SAFE TO PUSH — $problems problem(s) above. Fix, then re-run."
  exit 1
fi
```

Make it runnable:

<details open>
<summary><b>🍎🐧 macOS / Linux</b></summary>

```bash
chmod +x check-public-safe.sh
./check-public-safe.sh
```

*What is `chmod +x`?* File permissions. `+x` marks the file "executable" —
allowed to be run as a program rather than just read. Without it you'd get
"Permission denied".

</details>

<details open>
<summary><b>🪟 Windows PowerShell</b></summary>

Windows has no Bash by default, but Git for Windows installed one. Run:

```powershell
bash check-public-safe.sh
```

If `bash` isn't found, use the full path (adjust if you installed elsewhere):

```powershell
& "C:\Program Files\Git\bin\bash.exe" check-public-safe.sh
```

</details>

Expected output:

```
MicrobeGraph pre-push safety check
-----------------------------------
1. Secret files not tracked ......... OK
2. No key-shaped strings ............ OK
3. Data/database not tracked ........ OK
4. No hard-coded local paths ........ OK
5. .venv not tracked ................ OK
-----------------------------------
SAFE TO PUSH
```

✅ **Checkpoint.** `SAFE TO PUSH`.

**From now on, run this before every push.** It takes one second and prevents
the one mistake that can't be undone.

---

## 12. Step 10 — The three-branch model

### What a branch is

A **branch** is an independent line of work in the same repository.

*Everyday example:* you're writing a report. You want to try a bold restructure
but don't want to wreck the version your colleague is reading. So you make a
copy called "experiment", rework it there, and if it turns out well you replace
the main version. If not, you delete the copy. Nothing was ever at risk.

Git makes those copies instant and free, because it stores the differences, not
whole duplicate files.

### The three branches, and what each is for

| Branch | Role | Everyday parallel |
|---|---|---|
| **`master`** | The stable, official version | The published edition on the shelf |
| **`beta`** | Release candidate — finished but getting a final look | The advance copy sent to reviewers |
| **`develop`** | Where all day-to-day work happens | Your working draft, with pen marks |

**The rule: you always work on `develop`.** You never edit `master` directly.
That's what keeps the official version always in a good state.

This is a simplified version of a real, widely-used industrial pattern — nothing
invented for the tutorial.

### Create them

You're currently on `master` (from the clone). Confirm:

```bash
git branch
```
```
* master
```
The `*` marks where you are.

Create `develop` from `master`:

```bash
git branch develop
```

Now publish all three branches to GitHub. Note that `beta` is created **on the
remote only** — pushed straight from `develop`:

```bash
git push -u origin develop
git push origin develop:beta
git push origin develop:master
```

> **Why no local `beta`?** Because you never work on it. The daily push command
> (below) sends local `develop` to remote `beta` directly, so a local copy would
> just be a branch you'd have to remember to keep in step — an extra thing to go
> stale for no benefit.
>
> *Everyday parallel:* you keep a working draft on your desk and email copies to
> two people. You don't need a third copy on your desk labelled "the one I
> emailed to Sam."
>
> Keeping a local `beta` is harmless if you prefer it. It just isn't needed.

*What's `origin`?* Git's default nickname for "the repository I cloned from" —
here, your GitHub copy. `-u` sets it as the default destination so later pushes
need less typing.

Move onto `develop`, where you'll now live:

```bash
git switch develop
```
```
Switched to branch 'develop'
```

Confirm the layout:

```bash
git branch -a
```
```
* develop
  master
  remotes/origin/beta
  remotes/origin/develop
  remotes/origin/master
```

Two local branches, three on the remote. The `remotes/origin/*` entries are
GitHub's copies. ✅

A useful variant shows which remote branch each local one tracks:

```bash
git branch -vv
```
```
* develop b9c3295 [origin/develop] chore: initial project structure
  master  b9c3295 [origin/master] chore: initial project structure
```

The name in square brackets is the branch's **upstream** — where a bare
`git push` or `git pull` would go. Both are correctly paired.

### The push that updates all three at once

This is the command you'll run at the end of every phase:

```bash
git push origin develop develop:beta develop:master
```

Read it as three instructions in one:

| Piece | Meaning |
|---|---|
| `origin` | Send to GitHub |
| `develop` | Update remote `develop` from local `develop` |
| `develop:beta` | Also update remote `beta` from local `develop` |
| `develop:master` | Also update remote `master` from local `develop` |

The colon means "from local **X**, into remote **Y**".

**Why do all three at once?** Because in this project the three branches serve
as *stages of visibility* rather than divergent work: `develop` is where the
work is done, and once a phase is complete and verified it *is* the official
version. Keeping them in lock-step with one command means the published `master`
is never quietly stale.

Then bring your **local** `master` back in step, so your computer matches GitHub:

```bash
git switch master
git pull --ff-only origin master
git switch develop
```

*Why this last bit matters:* the push updated GitHub's `master`, not your
laptop's. Without the sync-back, your local `master` slowly drifts behind and
one day confuses you. `--ff-only` means "only update if it's a clean
fast-forward; if it isn't, stop and tell me" — so Git can never silently invent
a merge you didn't ask for. **The flag is written into the command on purpose**,
so this works whether or not you set the optional `pull.ff` config earlier.

---

## 13. Step 11 — Your first push

Time to save everything you've created.

### 1. Check what changed

```bash
git status
```

```
On branch develop
Untracked files:
  (use "git add <file>..." to include in what will be committed)
        .env.example
        check-public-safe.sh
        docs/
        requirements.txt
        ...

nothing added to commit but untracked files present
```

**"Untracked"** means Git can see the files but isn't watching them yet.

Read this output every time before committing. It's how you notice you're about
to commit something you didn't mean to.

### 2. Stage the changes

```bash
git add -A
```

**Staging** means "include this in the next snapshot".

*Everyday example:* putting items in a shopping basket. Nothing's bought yet —
you're choosing what goes in this trip. `-A` means "everything that changed".

### 3. Run the safety gate

```bash
./check-public-safe.sh      # Windows: bash check-public-safe.sh
```

Must say `SAFE TO PUSH`. If not, fix what it names and re-run.

> **Why staging comes first — this ordering matters.** The gate inspects what
> Git is *tracking*, using `git ls-files`. A brand-new file that has never been
> staged is invisible to Git, and therefore invisible to the gate. Run the check
> before staging and you're inspecting the *previous* state of the repository,
> not the one you're about to publish.
>
> *Everyday parallel:* checking your bag before you've finished packing it.
>
> If the gate fails, take the offending file back out of the basket and fix it:
> ```bash
> git restore --staged path/to/file      # unstage, keeping the file on disk
> ```
> then correct the problem (usually a `.gitignore` entry) and re-run the gate.

### 4. Commit

```bash
git commit -m "chore: project scaffolding, docs, and safety gate"
```

```
[develop a1b2c3d] chore: project scaffolding, docs, and safety gate
 6 files changed, 812 insertions(+)
 create mode 100644 .env.example
 create mode 100755 check-public-safe.sh
 ...
```

**On commit messages.** They're notes to your future self, who will not remember
what you did. A common, clear convention prefixes the type:

- `feat:` a new capability
- `fix:` a correction
- `docs:` documentation only
- `chore:` housekeeping, setup, configuration
- `test:` tests added or changed

Good: `feat: add MIBiG source adapter with probe and fetch`
Bad: `stuff`, `update`, `asdf`, `final version 2 REAL`

### 5. Push

```bash
git push origin develop develop:beta develop:master
```

```
Enumerating objects: 12, done.
Counting objects: 100% (12/12), done.
Writing objects: 100% (10/10), 8.42 KiB | 8.42 MiB/s, done.
To https://github.com/yourname/microbegraph.git
   e5f6a7b..a1b2c3d  develop -> develop
   e5f6a7b..a1b2c3d  develop -> beta
   e5f6a7b..a1b2c3d  develop -> master
```

Three lines at the end = three branches updated. ✅

### 6. Sync local master

```bash
git switch master
git pull --ff-only origin master
git switch develop
```

### 7. See it online

Open `https://github.com/yourname/microbegraph`. Your files are there. Use the
branch dropdown (top left, says `master`) to confirm all three exist and match.

🎉 **You have just published a project.** That is not a small thing — the
scaffolding, the safety gate, and the branch model you've set up are how real
projects are run.

---

## 14. Step 12 — Verify everything

One script that checks every piece of the setup at once. Save it as
`check-setup.py` in the project root:

```python
"""
MicrobeGraph — setup verification.

WHY THIS EXISTS:
    Setup has many steps and a half-finished environment produces confusing
    errors three phases later. This checks every piece at once and tells you
    exactly which step to revisit.

USAGE:
    python check-setup.py
"""

import subprocess          # for running other programs (git) and reading output
import sys                 # for information about the running Python
from pathlib import Path   # for file paths that work on every operating system

# Pathlib note: we use Path("docs") rather than "docs/" or "docs\\" because
# Windows uses backslashes and Unix uses forward slashes. Path handles the
# difference, which is one reason this project runs unchanged on all three
# operating systems.

checks: list[tuple[str, bool, str]] = []   # (label, passed?, hint if failed)


def check(label: str, passed: bool, hint: str = "") -> None:
    """Record one check result."""
    checks.append((label, passed, hint))


# --- 1. Python version -------------------------------------------------
version = sys.version_info
# Upper bound matters as much as the lower one: several scientific packages
# have no pre-built version for a brand-new Python release, so pip tries to
# compile them from source and fails with C compiler errors. The ecosystem
# takes 6-12 months to catch up. See Troubleshooting T11.
check(
    f"Python {version.major}.{version.minor}.{version.micro}",
    (3, 10) <= version < (3, 14),
    "Need Python 3.11 or 3.12. "
    "3.14+ has no builds yet for some packages. See Step 1 / Troubleshooting T11.",
)

# 3.13 works for everything in requirements.txt, but the Phase 7 extras in
# requirements-ml.txt have no build for it yet. Flag it now rather than letting
# it surprise someone months later.
if version[:2] == (3, 13):
    print("\n  NOTE: Python 3.13 runs the core project fine, but the Phase 7")
    print("        extras (requirements-ml.txt) have no build for it yet.")
    print("        Prefer 3.11 or 3.12 if you have one available.")

# --- 2. Virtual environment active -------------------------------------
# When a venv is active, sys.prefix points inside it and differs from
# sys.base_prefix (the original Python installation).
in_venv = sys.prefix != sys.base_prefix
check(
    "Virtual environment active",
    in_venv,
    "Activate it: source .venv/bin/activate  "
    "(Windows: .\\.venv\\Scripts\\Activate.ps1). See Step 7.",
)

# --- 3. Required packages import ---------------------------------------
for package in ["pandas", "numpy", "requests", "duckdb", "networkx",
                "matplotlib", "plotly", "streamlit", "pytest"]:
    try:
        __import__(package)
        check(f"package: {package}", True)
    except ImportError:
        check(f"package: {package}", False,
              "Run: pip install -r requirements.txt  (with .venv active). See Step 8.")

# --- 4. Git available and configured -----------------------------------
try:
    subprocess.run(["git", "--version"], capture_output=True, check=True)
    check("git installed", True)

    name = subprocess.run(["git", "config", "user.name"],
                          capture_output=True, text=True).stdout.strip()
    email = subprocess.run(["git", "config", "user.email"],
                           capture_output=True, text=True).stdout.strip()
    check("git identity configured", bool(name and email),
          'Run: git config --global user.name "Your Name" (and user.email). See Step 3.')
except (subprocess.CalledProcessError, FileNotFoundError):
    check("git installed", False, "Install Git. See Step 3.")

# --- 5. Branches exist --------------------------------------------------
# Only master and develop are REQUIRED locally. The push command
#     git push origin develop develop:beta develop:master
# updates remote beta straight from local develop, so a local beta branch is
# never needed. Keeping one is a matter of taste, not correctness.
try:
    local = subprocess.run(["git", "branch"], capture_output=True,
                           text=True).stdout
    for branch in ["master", "develop"]:
        check(f"local branch: {branch}", branch in local,
              f"Create it: git branch {branch}. See Step 10.")

    # The remote is what actually matters for beta.
    remote = subprocess.run(["git", "branch", "-r"], capture_output=True,
                            text=True).stdout
    for branch in ["master", "beta", "develop"]:
        check(f"remote branch: origin/{branch}", f"origin/{branch}" in remote,
              f"Push it: git push origin develop:{branch}. See Step 10.")
except FileNotFoundError:
    pass

# --- 6. Folder structure ------------------------------------------------
for folder in ["docs", "src/microbegraph", "curation", "artifacts",
               "app", "tests", "data/raw", "data/processed"]:
    check(f"folder: {folder}", Path(folder).is_dir(),
          f"Create it: mkdir -p {folder}. See Step 6.")

# --- 7. Safety files ----------------------------------------------------
check("file: .gitignore", Path(".gitignore").is_file(), "See Step 9.")
check("file: requirements.txt", Path("requirements.txt").is_file(), "See Step 8.")
check("file: check-public-safe.sh", Path("check-public-safe.sh").is_file(), "See Step 9.")

# --- Report -------------------------------------------------------------
print("\nMicrobeGraph setup check")
print("=" * 52)

failed = 0
for label, passed, hint in checks:
    mark = "PASS" if passed else "FAIL"
    print(f"  [{mark}]  {label}")
    if not passed:
        failed += 1
        print(f"          → {hint}")

print("=" * 52)
if failed == 0:
    print("All checks passed. Your workshop is ready.\n")
    sys.exit(0)
else:
    print(f"{failed} check(s) failed — see the hints above.\n")
    sys.exit(1)
```

Run it:

```bash
python check-setup.py
```

Expected:

```
MicrobeGraph setup check
====================================================
  [PASS]  Python 3.12.7
  [PASS]  Virtual environment active
  [PASS]  package: pandas
  [PASS]  package: numpy
  [PASS]  package: requests
  [PASS]  package: duckdb
  [PASS]  package: networkx
  [PASS]  package: matplotlib
  [PASS]  package: plotly
  [PASS]  package: streamlit
  [PASS]  package: pytest
  [PASS]  git installed
  [PASS]  git identity configured
  [PASS]  branch: master
  [PASS]  branch: beta
  [PASS]  branch: develop
  [PASS]  folder: docs
  [PASS]  folder: src/microbegraph
  [PASS]  folder: curation
  [PASS]  folder: artifacts
  [PASS]  folder: app
  [PASS]  folder: tests
  [PASS]  folder: data/raw
  [PASS]  folder: data/processed
  [PASS]  file: .gitignore
  [PASS]  file: requirements.txt
  [PASS]  file: check-public-safe.sh
====================================================
All checks passed. Your workshop is ready.
```

🎉 ✅ **Major checkpoint.** Every `PASS`, no `FAIL`. **Your machine is set up.
You never have to do this again on this computer.**

Commit it:

```bash
git switch develop
git add -A
./check-public-safe.sh
git commit -m "chore: add setup verification script"
git push origin develop develop:beta develop:master
git switch master
git pull --ff-only origin master
git switch develop
```

---

## 15. Your daily rhythm from now on

Setup was the long part. Actual work looks like this:

**Starting a session:**

```bash
cd ~/projects/microbegraph          # Windows: cd $HOME\projects\microbegraph
source .venv/bin/activate           # Windows: .\.venv\Scripts\Activate.ps1
git switch develop
```

Three lines. That's it.

**Ending a session:**

```bash
git add -A                   # stage FIRST — the gate can only see tracked files

pytest -q                    # once tests exist (Phase 1 onward)
./check-public-safe.sh       # must say SAFE TO PUSH

git commit -m "feat: describe what you did"
git push origin develop develop:beta develop:master

git switch master
git pull --ff-only origin master
git switch develop
```

**On a second machine** (say you set up on your laptop and now want to work on a
Linux VM), the whole setup collapses to:

```bash
git clone https://github.com/yourname/microbegraph.git
cd microbegraph
python3.11 -m venv .venv        # or python3.12 — whichever you have
source .venv/bin/activate
pip install -r requirements.txt
python check-setup.py
```

Six lines, because everything needed was written down. **That is the entire
point of `requirements.txt`, `.gitignore`, and the verification script** — the
setup is a *file*, not a memory.

---

## 16. Troubleshooting

### T1: "python: command not found" / "not recognised"

The command exists but your computer doesn't know where to look (the PATH
problem from Step 1).

- **Windows:** the "Add python.exe to PATH" box wasn't ticked. Re-run the
  installer → **Modify** → ensure "Add Python to environment variables" is on.
  Then **open a new PowerShell window** — existing ones keep the old PATH.
- **macOS/Linux:** try `python3` instead of `python`. On RHEL 8 try
  `python3.12`. Whichever works is your command from now on.
- **Still stuck?** `which python3` (macOS/Linux) or `where.exe python`
  (Windows) shows where the system is looking.

### T2: "Permission denied" running `./check-public-safe.sh`

The file isn't marked executable.

```bash
chmod +x check-public-safe.sh
```

On Windows use `bash check-public-safe.sh` instead — Windows doesn't use the
executable bit.

### T3: `ModuleNotFoundError` after installing

Almost always: the virtual environment isn't active, so `pip` installed into a
different Python than the one running your script.

1. Look at your prompt. Is `(.venv)` there? If not, activate.
2. Confirm which Python is in charge:
   ```bash
   python -c "import sys; print(sys.executable)"
   ```
   The path must contain your project's `.venv`.
3. Reinstall with the environment active: `pip install -r requirements.txt`

**In VS Code specifically:** the editor may be using a different interpreter
than your terminal. Press <kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>P</kbd>
(<kbd>Cmd</kbd> on Mac), type `Python: Select Interpreter`, and choose the one
inside `./.venv`.

### T4: PowerShell "running scripts is disabled on this system"

Windows blocks scripts by default. Run once:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Then retry activation.

### T5: Git asks for a password and rejects the right one

GitHub stopped accepting account passwords for Git operations. Use your
**Personal Access Token** as the password (Step 5, Option A). Username stays
your GitHub username.

### T6: `git push` rejected — "Updates were rejected because the remote contains work that you do not have locally"

Someone (or you, from another machine, or GitHub's web editor) changed the
remote since you last synced.

```bash
git switch develop
git pull --ff-only origin develop
```

If that fails because histories diverged, see what you have:

```bash
git log --oneline -5
git log --oneline -5 origin/develop
```

Then either `git pull --rebase origin develop` (replays your commits on top of
theirs — the tidy option) or ask for help. **Never** `git push --force` on a
shared branch to make an error go away; it deletes other people's work.

### T7: `git pull --ff-only` fails — "Not possible to fast-forward"

Your local branch and the remote have both moved, so there's no clean line to
follow. This is Git protecting you, working exactly as configured.

Inspect first:

```bash
git log --oneline --graph --all -10
```

Usually you were on the wrong branch when you committed. Move the commit:

```bash
git switch develop
git cherry-pick <commit-hash-from-the-log>
```

### T8: `.venv` accidentally committed

It's huge and machine-specific. Remove it from tracking (files stay on disk):

```bash
git rm -r --cached .venv
git commit -m "chore: stop tracking .venv"
```

Check `.venv/` is in `.gitignore`, then re-run `./check-public-safe.sh`.

### T9: A secret was committed

Act fast, in this order:

1. **Revoke the key immediately** at the provider (GitHub → Settings →
   Developer settings for a token; the relevant console for an API key).
   Revoking is instant and total.
2. **Generate a new key.**
3. **Then** clean the history (`git filter-repo`, or GitHub Support for a
   public repo).

Order matters: rewriting history takes time, and copies may already exist.
Revoking makes the leaked value worthless immediately, which is the only step
that truly closes the hole.

### T10: RHEL 8 — `python3.12: command not found` after `dnf install`

Your RHEL 8 minor version may not carry that module. Check what's offered:

```bash
dnf module list python3*
```

Install whichever 3.9+ version is listed, then use that name everywhere
`python3.12` appears in this tutorial. **Do not** remove the system `python3` —
`dnf` itself depends on it.

### T11: pip fails to build a package with C compiler errors

**The symptom** — `pip install -r requirements.txt` runs for a while, then a wall
of red output ending with something like:

```
error: Failed building wheel for gensim
× Failed to build installable wheels for some pyproject.toml based projects
```

Scroll up and you'll see compiler errors like `no member named 'ma_version_tag'`,
`no member named 'ob_digit'`, or `no member named 'curexc_traceback'`.

**What it means — and it is not your fault.** Some Python packages contain code
written in C for speed. Normally pip downloads a ready-built version (a "wheel")
that someone has already compiled and tested for your exact Python version and
operating system. If no wheel exists for your combination, pip falls back to
compiling from source on your machine — and if that package's C code hasn't been
updated for your Python version yet, the compile fails.

Those specific errors are the giveaway: `ma_version_tag`, `ob_digit` and
`curexc_traceback` are internal parts of Python that recent releases **removed**.
The package is written against a version of Python that no longer exists.

**The cause, 95% of the time: your Python is too new.**

Check it:

```bash
python --version
```

If it says **3.14 or higher**, that's the problem. New Python releases take 6–12
months for the scientific ecosystem to catch up, because every package with
compiled code needs rebuilding and testing.

**The fix — rebuild the environment on a suitable Python version.**

1. **First check whether you already have one.** Type `python` and press
   <kbd>Tab</kbd> twice (PowerShell: run `py --list`):

   ```bash
   python⇥⇥
   ```
   ```
   python3.11          python3.13          python3.14
   ```

   Look for **3.11** or **3.12**. If one is there, **skip to step 2** — you don't
   need to install anything. Most people hitting this error already have a usable
   version and simply built the environment with the wrong one.

   Only if nothing in range is present: install **Python 3.12** from
   <https://www.python.org/downloads/>, scrolling past the big green button to
   find 3.12.x. It installs *alongside* your existing versions; nothing is
   removed.

2. **Delete the virtual environment.** It's disposable by design — this is
   exactly the situation venvs exist for. Nothing of yours is lost:

   ```bash
   deactivate                    # leave it first (ignore any error if not active)

   rm -rf .venv                  # macOS / Linux
   # Remove-Item -Recurse -Force .venv     # Windows PowerShell
   ```

3. **Create a new one, naming your chosen version explicitly:**

   ```bash
   python3.11 -m venv .venv                # macOS / Linux — use the version you found
   # python3.12 -m venv .venv              # ...or this one
   # py -3.12 -m venv .venv                # Windows
   ```

   ⚠️ **`python3.12: command not found` here means you don't have 3.12** — use
   whichever version the Tab-completion check in step 1 actually listed. The name
   must match something that exists on your machine.

4. **Activate and confirm the version:**

   ```bash
   source .venv/bin/activate               # Windows: .\.venv\Scripts\Activate.ps1
   python --version
   ```
   ```
   Python 3.11.9
   ```

5. **Install again:**

   ```bash
   pip install -r requirements.txt
   ```

   Expect it to be much faster this time — with wheels available, pip downloads
   ready-made packages instead of compiling anything.

✅ **Checkpoint.** `python check-setup.py` prints "All checks passed".

**If you cannot install a different Python** (a locked-down work machine, say),
you still have a route: everything in `requirements.txt` has wheels for a wide
range of versions, and the two fragile embedding libraries live separately in
`requirements-ml.txt`. Skip that second file and Phases 1–6 work normally.
Phase 7 documents a pure-scikit-learn fallback that computes embeddings without
gensim — slower on very large graphs, entirely adequate at this project's size.

**The lasting lesson.** For data and scientific work, run **one or two versions
behind the newest** Python. The newest release is for people testing the language
itself. This is not timidity — it's the standard practice in the field, and it
saves hours of exactly this kind of confusion.

### T12: Corporate proxy / firewall blocks `pip`

On a locked-down work VM, `pip` may fail with connection timeouts. Ask IT for
the proxy address, then:

```bash
pip install --proxy http://proxy.company.com:8080 -r requirements.txt
```

To make it permanent, set the `HTTPS_PROXY` environment variable, or add a
`pip.conf` (`pip.ini` on Windows). Your IT team will know which applies.

---

## 17. Checkpoint

You've finished setup when **all** of these are true:

- [ ] `python --version` inside the activated `.venv` prints 3.11 or 3.12
- [ ] VS Code is installed with the Python extension
- [ ] `git --version` works and `git config --global --list` shows your identity
- [ ] You have a GitHub account and a `microbegraph` repository
- [ ] The repository is cloned into `~/projects/microbegraph`
- [ ] Two local branches: `master` and `develop` (a local `beta` is optional)
- [ ] Three remote branches: `origin/master`, `origin/beta`, `origin/develop`
- [ ] `git branch` shows `* develop`
- [ ] Your prompt shows `(.venv)` when you're working
- [ ] `pip install -r requirements.txt` completed without errors
- [ ] `requirements.lock.txt` exists (created by `pip freeze`)
- [ ] `./check-public-safe.sh` prints `SAFE TO PUSH`
- [ ] `python check-setup.py` prints "All checks passed"
- [ ] You have pushed at least once and can see your files on github.com

**If anything is unticked, fix it now.** Every later phase assumes all of this.

**What you learned in this document:** what a terminal is and the five commands
that matter; what Python is and why version numbers matter; why a code editor
beats a text editor; what Git is, what a commit is, and what a branch is; how to
authenticate to GitHub safely; what a virtual environment is and the real
problem it solves; what a package and a requirements file are; why secrets must
be protected before you have any; the three-branch model and the push that keeps
them in step; and the habit of verifying every step instead of assuming.

That's a genuinely substantial foundation, and it transfers to every project you
ever build — not just this one.

---

**Next:** [`02-ontology-and-data-model.md`](02-ontology-and-data-model.md) — the
rulebook that decides what may become a dot and what may become an arrow, and
why writing it *before* the code is the difference between a graph and a tangle.
