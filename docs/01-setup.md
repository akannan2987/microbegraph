[← Handbook](HANDBOOK.md) · [README](../README.md) · [Glossary](GLOSSARY.md) · [Git workflow](GIT-WORKFLOW.md) · [Phase 1](03-ingestion-mibig.md)

# 01. Setup: from a blank laptop to a working workshop

**Prerequisites:** a computer running Windows 10/11, macOS, or Linux (RHEL 8 /
Rocky / AlmaLinux), an internet connection, and permission to install software.
I don't assume any programming experience. If you have never opened a terminal
in your life, you're exactly the reader I had in mind when I wrote this.

**Learning goal:** by the end you will have a terminal you're comfortable in,
Python installed and verified, a code editor, Git configured, a GitHub account,
an empty MicrobeGraph repository with three branches (`master`, `beta`,
`develop`), a sealed Python toolbox for this project, and a safety gate that
stops you from ever publishing a secret. You will also understand *why* each of
those exists.

**Time:** 60-90 minutes the first time. You only do this once per machine;
after that, day-to-day work comes down to three or four short commands.

**Checkpoint at the end:** a `check-setup` command that verifies every piece.

![Set up once per machine, then repeat a short loop](img/setup_flow.svg)

> Every term here is also in [`GLOSSARY.md`](GLOSSARY.md).

---

## Contents

1. [How to read this document](#1-how-to-read-this-document)
2. [Step 0. The terminal, explained](#2-step-0-the-terminal-explained)
3. [Step 1. Install Python](#3-step-1-install-python)
4. [Step 2. Install a code editor (VS Code)](#4-step-2-install-a-code-editor-vs-code)
5. [Step 3. Install and configure Git](#5-step-3-install-and-configure-git)
6. [Step 4. Create your GitHub account](#6-step-4-create-your-github-account)
7. [Step 5. Connect your computer to GitHub](#7-step-5-connect-your-computer-to-github)
8. [Step 6. Create the project folder](#8-step-6-create-the-project-folder)
9. [Step 7. The virtual environment](#9-step-7-the-virtual-environment-what-and-why)
10. [Step 8. Install the project's packages](#10-step-8-install-the-projects-packages)
11. [Step 9. Protect your secrets before you have any](#11-step-9-protect-your-secrets-before-you-have-any)
12. [Step 10. The three-branch model](#12-step-10-the-three-branch-model)
13. [Step 11. Your first push](#13-step-11-your-first-push)
14. [Step 12. Verify everything](#14-step-12-verify-everything)
15. [Your daily rhythm from now on](#15-your-daily-rhythm-from-now-on)
16. [Troubleshooting](#16-troubleshooting)
17. [Checkpoint](#17-checkpoint)

---

## 1. How to read this document

A few ground rules first.

1. Go one step at a time, in order. Later steps assume the earlier ones worked.
2. Type the commands rather than pasting them, at least at first. It's slower,
   but it teaches your fingers what the words are. Start pasting once you're
   bored.
3. **Always check the expected output.** Every command below shows what success
   looks like. If yours differs, stop and look in
   [Troubleshooting](#16-troubleshooting) before carrying on. Pushing on past a
   failed step is the single most common way beginners get stuck for hours.
4. Expect errors, and read them. Everyone who writes code reads error messages
   all day. What you're learning is to read the error, work out which step it
   belongs to, and fix that step.

A few conventions used throughout:

- Lines starting with `$` are commands you type (don't type the `$` itself).
- <kbd>Enter</kbd> means press the Enter/Return key.
- Where operating systems differ, you'll see three labelled blocks. **Do only
  the one for your machine.**

---

## 2. Step 0. The terminal, explained

### What it is

A **terminal** (also "command line", "shell", "console") is a window where you
type instructions to your computer as text instead of clicking.

Clicking through folders is a bit like wandering round a supermarket looking
for the pasta. Using the terminal is more like handing the shop assistant a
written list. It takes longer to learn and is far faster once you know it, and
a written list can be handed to someone else and produce the same result. That
reproducibility is why every serious data project is run from the terminal.

You won't need many commands. Realistically, five of them do 90% of the work.

### Open it

**Windows**: press <kbd>Win</kbd>, type `PowerShell`, press <kbd>Enter</kbd>.
Use PowerShell rather than the older "Command Prompt", because every Windows
command in this tutorial assumes PowerShell.

**macOS**: press <kbd>Cmd</kbd>+<kbd>Space</kbd>, type `Terminal`, press
<kbd>Enter</kbd>.

**Linux (RHEL 8)**: <kbd>Ctrl</kbd>+<kbd>Alt</kbd>+<kbd>T</kbd>, or find
"Terminal" in the applications menu. On a headless VM you're already there when
you SSH in.

### The five commands you actually need

Try each one now; none of them can do any harm.

```bash
pwd
```
*"Print working directory": where am I right now?* You should see a path:

```
/Users/yourname          # macOS
/home/yourname           # Linux
C:\Users\yourname        # Windows PowerShell
```

```bash
ls
```
*List what's in this folder.* You'll see names like `Documents` and `Downloads`.
(On Windows PowerShell, `ls` works and so does `dir`.)

```bash
cd Documents
```
*"Change directory": go into the Documents folder.* No output means it worked.
That's a general rule in terminals. Tools print something when there's a
problem and stay quiet when all is well.

```bash
cd ..
```
*Go up one level.* Two dots always mean "the folder above this one".

```bash
mkdir practice
```
*Make a folder called `practice`.* Run `ls` to see that it appeared. You can
delete it in your normal file browser afterwards.

Three habits will save you a lot of time:

- Press <kbd>Tab</kbd> to autocomplete names. Type `cd Doc` then <kbd>Tab</kbd>.
  It completes to `Documents`. This prevents typos, which are the #1 cause of
  "command not found".
- Press <kbd>↑</kbd> to bring back the previous command. You'll use this
  constantly.
- Press <kbd>Ctrl</kbd>+<kbd>C</kbd> to cancel a command that's hanging.

That's enough terminal for this entire project. Everything else is a matter
of copying a command, checking the output, and moving on.

---

## 3. Step 1. Install Python

### What Python is, and why this project uses it

**Python** is a programming language: a way of writing instructions a computer
can follow. I chose it for this project because it's unusually readable (its
code looks close to English), it's free, it runs identically on Windows, macOS
and Linux, and every library MicrobeGraph needs (graphs, databases, web apps,
AI) already exists for it.

Choosing a language for a project is like choosing the language to write a
manual in: you pick the one your readers and your reference material already
speak. In data work, that's Python.

The project targets **Python 3.12**, and the version number matters. 3.12 and
3.9 differ in ways that break libraries.

**Use Python 3.11 or 3.12.** (3.13 also works for the core project, but 3.11
and 3.12 have pre-built versions of every package this project uses, including
the Phase 7 extras, so they're the choices that won't bite you later.)

Before you install anything, check what you already have (the next section shows
how). Machines often carry several versions, and using one you already own is
faster and tidier than adding another.

> ⚠️ **Do not use Python 3.14 (or whatever the newest release is).** It's a
> real trap, and it catches almost everyone once. Many scientific packages
> contain compiled C code, and someone has to rebuild and test each of them for
> every new Python release, which takes 6-12 months. Until that happens, `pip`
> finds no ready-made version, tries to compile from source, and fails with a
> wall of C compiler errors that look alarming and have nothing to do with you.
>
> It's rather like buying a new phone model on launch day: the phone is fine,
> but half your favourite apps haven't been updated for it yet.
>
> For data work, the professional habit is to always run one or two versions
> behind the newest. The newest release is for people testing the language
> itself. If you hit this, see [Troubleshooting T11](#t11-pip-fails-to-build-a-package-with-c-compiler-errors).

Python 2 is a different, long-dead language. Never use it.

### First: check what you already have

**Don't install anything yet.** A lot of machines already have more than one
Python, and adding another you don't need only makes clutter.

Type `python` and press the <kbd>Tab</kbd> key twice (don't press Enter):

```bash
python⇥⇥
```

Your shell lists every matching command it can find:

```
python              python3.11          python3.13          python3.14
python3             python3.11-config   python3.13-config   python3.14-config
```

Pressing Tab twice asks the shell to show every installed command that starts
with what you typed. It's the fastest way I know to see which Python versions a
machine actually has, and the trick works for any command, not only this one.

Look through the list for a version in the **3.11-3.13** range. (3.10 is too
old: one of the packages, scikit-learn, now needs 3.11 or newer.)

- **See `python3.11` or `python3.12`?** You're done. Skip the installation
  below entirely, write the name down, and use it in Step 7.
- **Only `python3.13`?** It's usable, but read the note below before you pick
  it.
- **Only `python3.14` or nothing in range?** Install 3.12 using the instructions
  below.

> **On 3.13 specifically:** everything in `requirements.txt` works on it. But
> `gensim`, one of the two Phase 7 extras in `requirements-ml.txt`, was last
> released before 3.13 existed and has no pre-built version for it. If you have
> 3.11 or 3.12 available, use one of those instead. Otherwise you'll meet the same
> problem months from now, at Phase 7, rather than today.

On Windows, Tab-completion works differently in PowerShell, so list your
versions with `py --list` instead.

### Install it (only if the check above found nothing suitable)

<details open>
<summary><b>🪟 Windows</b></summary>

1. Go to <https://www.python.org/downloads/windows/>
2. Scroll down to **Python 3.12.x** and download its "Windows installer
   (64-bit)". **Don't** click the big green button at the top of the page: it
   gives you the newest release, which is exactly what you don't want (see the
   warning above).
3. Run the installer. **Before clicking Install, tick the box at the bottom that
   says "Add python.exe to PATH".** Everyone misses this step, and it's behind
   most of the "python is not recognised" errors people hit later.

   *What is PATH?* It's a list of folders your computer searches when you type
   a command name. If Python isn't in one of them, typing `python` gets you "not
   recognised" even though Python is installed, rather like a phone book that
   doesn't list a number you own.
4. Click **Install Now**, wait, then **Close**.
5. **Close your PowerShell window and open a new one.** PATH changes only apply
   to terminals opened after the change.

</details>

<details open>
<summary><b>🍎 macOS</b></summary>

macOS ships with an old Python that must not be used for projects, so install
your own.

**Option A, the installer (simplest):**
1. Go to <https://www.python.org/downloads/macos/>
2. Scroll down to **Python 3.12.x** and download its macOS 64-bit universal2
   installer. Skip the big green button at the top; it gives you the newest
   release, which you don't want (see the warning above).
3. Run it and accept the defaults.
4. It installs as `python3.12`, alongside any other version you have. Use that
   exact name when creating the virtual environment in Step 7.

**Option B. Homebrew** (if you already have it, or want a package manager):
```bash
brew install python@3.12
```

</details>

<details open>
<summary><b>🐧 Linux. RHEL 8 / Rocky / AlmaLinux</b></summary>

RHEL 8 ships with Python 3.6, which is too old. Install 3.12 alongside it, and
**do not remove or replace the system Python**: the system's own tools depend on
it. (This is a common RHEL trap. Replacing the system Python breaks `yum`/`dnf`
itself.)

```bash
sudo dnf install -y python3.12 python3.12-pip
```

If your RHEL 8 minor version doesn't offer `python3.12`, use `python3.11` or
`python3.9` (both work) and substitute that name everywhere `python3.12`
appears below:

```bash
sudo dnf install -y python3.11 python3.11-pip
```

*What is `dnf`?* It's RHEL's package manager, a sort of app store for
command-line software. `sudo` means "run this as administrator". You'll be
asked for your password, and the cursor won't move while you type it. That's
normal.

</details>

### Verify it

This is the pattern for the whole tutorial: install something, then check that
it really worked before you move on.

```bash
python --version          # Windows, macOS
python3 --version         # macOS, Linux
python3.12 --version      # RHEL 8, if you installed 3.12 alongside
```

Expected output (your patch number may differ):

```
Python 3.12.7
```

✅ **Checkpoint.** You want a version between 3.11 and 3.13, ideally 3.12. Note
down which command produced it (`python`, `python3`, or `python3.12`), because
you'll use that same word throughout this tutorial. The rest of this document
writes it as `python`; substitute yours.

⚠️ **If it says 3.14 or higher, stop and install 3.12** using the instructions
above. If you carry on, things will work for several steps and then fail
confusingly at `pip install`. Installing 3.12 doesn't remove your other
version. The two live side by side, and you use `python3.12` when you create
the virtual environment.

❌ If you see "command not found" or "not recognised", go to
[Troubleshooting T1](#t1-python-command-not-found--not-recognised).

---

## 4. Step 2. Install a code editor (VS Code)

### Why not just use Notepad?

A **code editor** is a text editor that understands code. It colours the parts
of your program differently (so a typo often becomes visible before you run
anything), warns about mistakes as you type, and has a terminal built in so you
don't switch windows constantly.

Think of writing a letter in Notepad versus in Word. Both produce text, but only
Word tells you "you've misspelled this" while you're writing.

I use **VS Code** here. It's free, made by Microsoft, identical on all three
operating systems, and by a wide margin the most common editor in this field.

### Install it

1. Go to <https://code.visualstudio.com/>
2. The site detects your system; click the big download button.
3. Install with defaults.
   - **Windows:** tick "Add to PATH" and "Open with Code" if offered.
   - **macOS:** drag it to Applications.
   - **RHEL 8:** the `.rpm` download, then
     `sudo dnf install -y ./code-*.rpm`
4. Open VS Code.
5. Click the **Extensions** icon in the left bar (four squares), search for
   **Python**, and install the one published by **Microsoft**.

   *What's an extension?* An add-on that teaches the editor about a particular
   language, much like installing a dictionary for a language your word
   processor didn't know.

✅ **Checkpoint.** VS Code opens and the Python extension appears in your
installed list.

---

## 5. Step 3. Install and configure Git

### What Git is, properly

**Git** is a system that records snapshots of your project over time.

If you've played video games you already know the idea: you save before the
hard bit, and if it goes badly you reload. Git does that for your work, except
that every save is permanent and labelled with a message explaining what
changed, and you can compare any two saves to see exactly what's different.

It's also close to "Version history" in Google Docs, with two differences: you
choose when a version is created, and you write a note saying why.

Three words you'll use constantly:

| Word | Plain meaning | Everyday parallel |
|---|---|---|
| **repository** ("repo") | The project folder Git is watching, plus its whole history | A document with its full version history |
| **commit** | One saved snapshot, with a message | Clicking "save a named version" |
| **branch** | A parallel line of work | A photocopy of the draft you can scribble on without touching the original |

**Git ≠ GitHub.** Git is the program on your computer. GitHub is a website
that stores copies of Git repositories online, so your work is backed up and
other people can read it. You can use Git with no GitHub at all, but for this
project I want the backup and a public home.

### Install it

<details open>
<summary><b>🪟 Windows</b></summary>

1. Go to <https://git-scm.com/download/win>; the download starts automatically.
2. Run the installer and **accept every default**. There are a lot of screens,
   and the defaults are right for this project. One thing worth noticing is that
   it installs "Git Bash", an extra terminal. You can ignore it, since
   PowerShell is enough.
3. Close and reopen PowerShell.

</details>

<details open>
<summary><b>🍎 macOS</b></summary>

```bash
git --version
```
If Git isn't installed, macOS offers to install the Developer Tools. Accept,
and wait a few minutes. Otherwise, run `brew install git`.

</details>

<details open>
<summary><b>🐧 Linux. RHEL 8</b></summary>

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

Every commit is stamped with a name and an email address. You set them once
per machine.

```bash
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

> **Privacy note:** this email is embedded in every public commit. If you'd
> rather not publish your real address, GitHub gives you a free no-reply one:
> after creating your account (next step), go to
> **Settings → Emails → Keep my email addresses private**, and it shows an
> address like `12345678+username@users.noreply.github.com`. Use that here
> instead. You can change it later at any time.

One more setting worth having:

```bash
# Make "master" the default branch name for new repositories.
# (Git's historical default; some newer installs default to "main".
#  This project uses master, so set it explicitly.)
git config --global init.defaultBranch master
```

### Optional: the fast-forward-only preference

Some people like one more setting. It's optional, so decide for yourself:

```bash
git config pull.ff only
```

"Fast-forward" means Git can update your branch by moving its pointer along an
existing line, with nothing to reconcile. That's the clean case. `pull.ff only`
says: *if a pull isn't that clean, stop and tell me rather than inventing a
merge commit I didn't ask for.*

Compare a colleague adding paragraphs to the end of your draft (you just accept
them) with a colleague rewriting your middle section while you were rewriting
it too (someone has to decide what the document says). The setting says "in
the second case, ask me."

It's optional here because every `pull` in this project's documented workflow
already passes the flag on the command line,

```bash
git pull --ff-only origin master
```

so the config adds nothing to *this* project. It only helps in repositories
where you might forget the flag.

If you do want it, you also choose a scope. Git config can be set at two levels
(or not at all), and the more specific one wins:

| Command | Applies to | When you'd want it |
|---|---|---|
| `git config pull.ff only` | **This repository only** (`.git/config`) | You like the safety net here but don't want to change how Git behaves elsewhere |
| `git config --global pull.ff only` | Your whole user account | You want it everywhere, always |
| *(don't set it)* |  | Perfectly fine; the workflow's explicit `--ff-only` covers you |

It's the difference between a house rule and a rule for one room: "no shoes in
the flat" versus "no shoes in the bedroom."

I decided not to set this globally. The reasoning: every `pull` in this
project's documented workflow already passes `--ff-only` on the command line, so
the config adds nothing here and only changes how Git behaves in my other
repositories. If you want the safety net without that side effect, set it for
this repository alone by dropping `--global`.

My own suggestion is the repository-scoped version. It's a comfortable middle
ground, with protection where you're working and no side effects on your other
projects. Skipping it entirely is a perfectly reasonable choice
too, and the tutorial works either way.

<details>
<summary><b>🪟 Windows only, one extra setting</b></summary>

Windows and Unix mark line endings differently, which can make Git report that
every line of a file changed when nothing did. This setting handles the
translation:

```powershell
git config --global core.autocrlf true
```

On macOS/Linux the equivalent (`input`) is already the sensible default.

</details>

Now check all of it:

```bash
git config --global --list
```

```
user.name=Your Name
user.email=your.email@example.com
init.defaultbranch=master
```

(You may see other lines too, because Git installations and other tools add
their own settings. That's normal. If you set `pull.ff` globally above, it
appears here. If you set it per-repository it won't; check with
`git config --list --local` from inside the project instead.)

✅ **Checkpoint.** Your name and email appear.

---

## 6. Step 4. Create your GitHub account

**GitHub** is where your repositories live online. It's free, and it's the
standard place for this kind of work to be published and read.

1. Go to <https://github.com/> and click **Sign up**.
2. Choose a username you're happy for people to see, since it becomes part of
   every URL (`github.com/yourname/microbegraph`). Something close to your real
   name is the norm.
3. Verify your email address.
4. The free plan is all you need. Public repositories are free and unlimited.

✅ **Checkpoint.** You can log in and see your (empty) profile page.

---

## 7. Step 5. Connect your computer to GitHub

Whenever your computer uploads something, it has to prove it's you. There are
two ways to set that up.

### Option A. Personal Access Token (simplest; recommended to start)

A **Personal Access Token** (PAT) is a long password generated for programs
rather than people. Your normal GitHub password won't work for Git operations.
GitHub does that on purpose: a token can be limited in scope, and revoked on its
own without changing your account password.

1. Log in to GitHub.
2. Click your avatar (top right) → **Settings**.
3. Scroll to the bottom of the left sidebar → **Developer settings**.
4. **Personal access tokens** → **Tokens (classic)** → **Generate new token
   (classic)**.
5. **Note:** `microbegraph laptop`. **Expiration:** 90 days is a sensible
   balance. **Scopes:** tick **`repo`** and **`workflow`**, and nothing else.
   `repo` lets Git push your code. `workflow` lets it push the file that switches
   on automatic testing in Phase 1 (`.github/workflows/ci.yml`); without it GitHub
   refuses that one push (see [T13](#t13-push-refused-refusing-to-allow-a-personal-access-token-to-create-or-update-workflow)).
6. Click **Generate token**, then **copy it immediately**: GitHub shows it once
   and never again. Paste it somewhere safe (a password manager is ideal).

When Git asks for a password later, paste the token. To avoid re-pasting every
time, turn on the credential helper:

```bash
# Windows
git config --global credential.helper manager

# macOS
git config --global credential.helper osxkeychain

# Linux (RHEL 8), caches in memory for 1 hour; nothing written to disk
git config --global credential.helper 'cache --timeout=3600'
```

> ⚠️ **Never** paste a token into a file inside your project, into code, or into
> a commit message. If you ever do it by accident, go straight to GitHub →
> Settings → Developer settings, revoke the token, and generate a new one. A
> revoked token stops working instantly. This is the kind of accident
> `check-public-safe.sh` (Step 9) is there to prevent.

### Option B. SSH keys (nicer long-term)

An **SSH key** is a matched pair of files: a *private* key that never leaves
your machine and a *public* key you give GitHub. They prove your identity
without any password being sent.

The pair works like a physical key and the lock it fits. You keep the key; the
lock is fitted to the door, and on its own it's useless to a thief.

```bash
# 1. Generate the pair (press Enter three times to accept defaults)
ssh-keygen -t ed25519 -C "your.email@example.com"

# 2. Show the PUBLIC key (safe to share, never show the one without .pub)
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
Despite how it reads, that message means it worked.

✅ **Checkpoint.** You have either a token saved safely, or a working SSH key.

---

## 8. Step 6. Create the project folder

### Create the repository on GitHub first

I create it online first and then clone it down, because that avoids a whole
category of "these two repositories don't know about each other" confusion.

1. GitHub → **+** (top right) → **New repository**.
2. **Repository name:** `microbegraph`
3. **Description:** `A knowledge graph of microbes, the molecules they make, and the crop diseases those molecules act on.`
4. **Public.**
5. ✅ **Add a README file**. This creates the first commit, so the repository
   isn't empty (an empty repo has no branches, which makes the next steps
   awkward).
6. **Add .gitignore:** choose **Python** from the dropdown. (We'll replace it
   with a fuller version in Step 9.)
7. **Choose a license:** **MIT**. It's the standard permissive licence: anyone
   may use your work as long as they keep your copyright notice.
8. **Create repository.**

### Clone it to your computer

To **clone** a repository means to download a copy of it, including its whole
history, that stays wired up to talk to the original.

First decide where projects live on your machine, and stick to it:

```bash
# macOS / Linux
mkdir -p ~/projects
cd ~/projects

# Windows PowerShell
mkdir $HOME\projects
cd $HOME\projects
```

`~` and `$HOME` are both shorthand for your home folder: `~/projects` is
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

`.git` is the hidden folder that holds the entire history. **Never edit or
delete it**: as far as Git is concerned, that folder *is* the repository. (The
`-a` flag means "show hidden files"; on Windows PowerShell use `ls -Force`.)

### Create the folder structure

These are empty scaffolding folders that later phases will fill. Creating them
now means every later instruction has a place to put things.

<details open>
<summary><b>🍎🐧 macOS / Linux</b></summary>

```bash
mkdir -p docs src/microbegraph curation artifacts app mcp tests notebooks data/raw data/processed
```
*(one command; `-p` creates parent folders as needed)*

</details>

<details open>
<summary><b>🪟 Windows PowerShell</b></summary>

```powershell
"docs","src/microbegraph","curation","artifacts","app","mcp","tests","notebooks","data/raw","data/processed" | ForEach-Object { New-Item -ItemType Directory -Force -Path $_ }
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

*Why?* `.gitkeep` is only a naming convention, not a Git feature. Git tracks
files rather than folders, so putting one dummy file inside a folder is how you
make an "empty" folder survive a clone.

✅ **Checkpoint.** `ls` shows the new folders.

---

## 9. Step 7. The virtual environment: what and why

Beginners tend to skip this concept and regret it later, so it's worth reading
the why before the how.

### The problem it solves

Python libraries are installed on your machine and shared by everything. Project
A needs version 1.0 of a library; project B needs version 2.0. Install 2.0 and
project A breaks, with an error that has nothing obviously to do with the
install you just did. This is known, affectionately, as *dependency hell*.

Picture one shared kitchen for a whole apartment block. Someone swaps the flour
for gluten-free, and your bread recipe fails without you having any idea why. A
**virtual environment** is your own private kitchen cupboard, holding your
ingredients at your versions, untouched by anyone else's changes.

Or think of a separate toolbox for each project instead of one giant shared
garage. Each toolbox holds exactly the tools that project needs, at the
versions it needs.

In concrete terms, a virtual environment (`venv`) is a **folder** containing
its own copy of Python and its own libraries. That gives you two big benefits:

1. **Isolation:** projects can't break each other.
2. **Reproducibility:** you can write down exactly what's in the toolbox
   (`requirements.txt`) so anyone, on any operating system, can build an
   identical one. That's what makes "clone this repo and run it" actually work.

### Create it

Run this **inside** the `microbegraph` folder:

```bash
# Use the exact version name you identified in Step 1.
python3.11 -m venv .venv        # macOS / Linux, if 3.11 is what you have
python3.12 -m venv .venv        # ...or 3.12
python -m venv .venv            # only if `python --version` already shows 3.11-3.12
# py -3.12 -m venv .venv        # Windows, choosing a specific version
```

⚠️ **Name the version explicitly rather than using bare `python`.** On a machine
with several versions installed, plain `python` may point at whichever one was
installed last. That's often the newest, which is exactly the one you don't
want. Naming it takes two extra characters and prevents the most common setup
failure in this whole document.

I learned this the slow way. After the 3.14 failure described in Troubleshooting
T11 I went off to download 3.12, and only then discovered I already had 3.11
sitting on the machine. Typing `python` and pressing Tab twice would have told
me that in two seconds. Check what you have before you install anything.

If you get `command not found`, that version isn't installed. Go back to Step 1
and use a name the Tab-completion check actually listed.

*Reading the command:* `-m venv` means "run the built-in module called venv",
and `.venv` is the folder to create. By convention the name starts with a dot,
which hides it, because the folder holds machinery rather than your content.

If nothing is printed, it worked.

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

That prefix is your signal. If you don't see `(.venv)`, you're outside the
toolbox, and `pip install` would put packages in the wrong place. Get into the
habit of glancing at it.

**You must activate once per terminal session**, which means every time you
open a new window to work on this project. Activation isn't permanent, and
that's by design.

To leave the environment, type `deactivate`.

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
`.venv`, and the version is in the 3.11-3.12 range. If the path points somewhere
else (like `/usr` or `C:\Python312`), the environment isn't active; re-run the
activate command. If the *version* is wrong, delete `.venv` and recreate it with
the right Python named: `rm -rf .venv`, then `python3.11 -m venv .venv`.

---

## 10. Step 8. Install the project's packages

### What a package is

A **package** (or library) is code someone else wrote and published so you don't
have to write it yourself.

Using one is like buying flour instead of growing wheat. You *could* implement
graph algorithms from scratch, but it would take months, and yours would be
slower and buggier than NetworkX, which hundreds of people have improved over
twenty years.

**pip** is Python's package installer: the program that fetches packages and
installs them.

### The requirements file

Rather than installing packages one at a time and forgetting which, I list them
in `requirements.txt`. That file is the project's shopping list, and anyone can
use it to rebuild an identical toolbox.

Create it in the project root (VS Code: **File → New File**, save as
`requirements.txt`):

```
# MicrobeGraph, core Python dependencies
#
# Install with:  pip install -r requirements.txt
#
# PYTHON VERSION: 3.11 or 3.12.
#   3.13 also runs everything here, but the Phase 7 extras in
#   requirements-ml.txt have no build for 3.13 yet.
#   3.10 is too old: scikit-learn 1.9 needs 3.11 or newer.
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
#   The upper bound matters because these projects follow "semantic
#   versioning", where the FIRST number changes only when a release breaks
#   something on purpose.
#   pandas 2 -> 3 is allowed to remove functions and change defaults; 2.2 -> 2.9
#   is not. So an upper bound at the next major version is the line between
#   "safe improvements" and "we make no promises".
#
#   A recipe can say "any medium onion" and still work, but it can't say "any
#   vegetable". The bounds describe the range where the recipe still works.
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
scikit-learn>=1.9,<2     # models + careful evaluation (cross-validation, metrics)

# --- The app ---
streamlit>=1.36,<2       # turns a Python script into a web app

# --- Quality ---
pytest>=8.2,<10          # runs automated checks on our own code
ruff>=0.5,<1             # spots style problems and likely bugs

# --- Configuration ---
python-dotenv>=1.0,<2    # reads optional API keys from a .env file

# ---------------------------------------------------------------------------
# IF YOU ADD A PACKAGE HERE, ADD IT TO check-setup.py TOO.
#   Otherwise the setup check quietly verifies fewer things than it claims,
#   and a green result stops meaning what you think it means. A check script
#   that has drifted from reality is worse than none, because it reassures
#   you about things it no longer checks.
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# A NOTE ON THE 0.x PACKAGES (pyvis, ruff)
#   Before version 1.0, the rules are different: the SECOND number is the one
#   allowed to break things. So pyvis is capped at <0.4 rather than <1, because
#   0.3 -> 0.4 could change behaviour the way 3 -> 4 would elsewhere.
#   It's a small detail, but reading version numbers correctly saves time.
# ---------------------------------------------------------------------------

# NOTE: the node-embedding libraries (gensim, node2vec) are NOT here.
# They are the most fragile dependencies in the stack: they contain compiled
# C code and break first on new Python versions, and nothing before Phase 7
# needs them. They live in requirements-ml.txt, which you install only when
# you reach that phase, so a broken embedding library can never stop someone
# from setting the project up.
```

> **Why there are two requirements files.** `requirements.txt` holds everything
> Phases 1-6 need. A second file, `requirements-ml.txt`, holds two node-embedding
> libraries used only in Phase 7. Those two contain compiled C code, which makes
> them the most fragile part of the stack: they're always the first to break on
> a new Python release. Keeping them separate means a broken library can never
> stop you setting the project up and completing six phases. I've come to think
> this is a good habit for any project: keep what you need to get started apart
> from what you need for one later feature.

Install everything you need for now:

```bash
pip install -r requirements.txt
```

Expect a wall of scrolling text for 1-3 minutes, ending with something like:

```
Successfully installed duckdb-1.1.3 matplotlib-3.9.2 networkx-3.4.2 numpy-2.1.3
pandas-2.2.3 plotly-5.24.1 pytest-8.3.3 pyvis-0.3.2 requests-2.32.3 ruff-0.7.4
streamlit-1.40.1 tenacity-9.0.0 python-dotenv-1.0.1 ...
```

Your version numbers will differ from these. That's expected, since `>=` means
"this or newer".

### Lock the exact versions

You've just installed working versions of 74 packages. Now **write down exactly
which ones**, so the environment can be recreated identically: by you on another
machine, by anyone cloning the repository, or by you in a year's time when the
latest versions have moved on.

```bash
pip freeze --exclude-editable > requirements.lock.txt
```

Windows PowerShell writes files with `>` in an encoding Git treats as binary, so
on Windows use this instead:

```powershell
pip freeze --exclude-editable | Set-Content -Encoding utf8 requirements.lock.txt
```

Again, no output means it worked. (`--exclude-editable` leaves out MicrobeGraph
itself once it's installed in Phase 1. Without it, the lockfile would gain a
line pointing at *your* copy of the project, which no other computer can install
from.) Open the file and you'll see exact versions, one per line:

```
altair==6.2.2
attrs==26.1.0
duckdb==1.5.5
networkx==3.6.1
numpy==2.4.6
pandas==3.0.5
...
```

You now have two files with two different jobs. This trips people up, so it's
worth spelling out:

| File | Contains | Answers |
|---|---|---|
| `requirements.txt` | Ranges (`pandas>=2.2,<4`) | *What does this project need?* |
| `requirements.lock.txt` | Exact versions (`pandas==3.0.5`) | *What exactly was working on the day it was tested?* |

`requirements.txt` is the shopping list ("a medium onion, plain flour").
`requirements.lock.txt` is the till receipt: the exact brands and sizes you
actually bought, on that day, from that shop. With the list, someone can cook
the dish; with the receipt, they can reproduce your exact result.

So which one do people install from?

- Normally `requirements.txt`, because you want the bug fixes and security
  patches that arrive within the allowed range.
- `requirements.lock.txt` when something is wrong. If the project suddenly
  misbehaves after an update, installing the locked versions tells you straight
  away whether a dependency change caused it. That's a very useful diagnostic,
  and the main reason to keep the file.

**Both are committed to Git.** Regenerate the lockfile whenever you change
dependencies on purpose. It's a one-line command at the end of any phase that
adds a package.

### Install MicrobeGraph itself (from Phase 1 on)

The packages above are other people's code. MicrobeGraph's own code lives in
`src/microbegraph/`, and from Phase 1 on there's a command to run,
`python -m microbegraph.fetch`. So that Python can find it from any folder, you
install the project into `.venv` as well, once:

```bash
pip install -e .
```

The `.` means "the project in this folder", and `-e` means **editable**: Python
gets a pointer to `src/microbegraph/` rather than a copy, so every change you
make takes effect at once. It's like a library card that says "shelf 4" instead
of a photocopy of the book.

This needs the file `pyproject.toml`, which arrives in Phase 1. **If you are
setting up before Phase 1 exists, skip this command**; the Phase 1 guide
([`03-ingestion-mibig.md`, Step 1](03-ingestion-mibig.md#5-step-1-make-microbegraph-an-installable-package))
tells you when. If you cloned the finished repository, run it now.

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

## 11. Step 9. Protect your secrets before you have any

### Why now, before there's anything to protect

By the time you need this protection, it's too late to add it. Git remembers
everything: a password committed once and deleted in the next commit is still
sitting in the history, publicly, forever, and bots scan GitHub for exactly
this within minutes of a push.

So set the locks up first, while the house is empty. It takes five minutes.

### `.gitignore`, the lock on the door

`.gitignore` is a list of things Git must never track. Replace the file GitHub
created with this fuller version (VS Code: open `.gitignore`, select all,
paste):

```gitignore
# ---------------------------------------------------------------
# MicrobeGraph, what Git must never publish
# ---------------------------------------------------------------

# Secrets: API keys, tokens, anything private. NEVER commit these.
.env
.env.*
!.env.example
.streamlit/secrets.toml
*.pem
*.key

# The virtual environment is large and machine-specific, and it can be
# rebuilt from requirements.txt, so never commit it.
.venv/
venv/
env/

# Data, rebuilt by the pipeline. Keeping it out of Git keeps the repository
# small and shows that the pipeline really can rebuild it.
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
.DS_Store
Thumbs.db
desktop.ini
*~

# --- R -----------------------------------------------------------
# The installed package library: large, machine-specific, and fully
# rebuildable from renv.lock: the R counterpart of .venv/ for Python.
renv/library/
renv/staging/
renv/python/
renv/sandbox/

# A saved snapshot of your entire R workspace. Never commit this: it can
# silently contain data or credentials, and it makes scripts appear to work
# when they only work on YOUR machine.
.RData
.Rhistory
.Rapp.history

# RStudio's per-user state (open tabs, pane sizes)
.Rproj.user/

# Output from R CMD check
*.Rcheck/

# NOT ignored, and committed on purpose:
#   microbegraph.Rproj:  so everyone gets the same project settings
#   renv.lock:           so everyone can rebuild the same package versions
#   .Rprofile:           so renv activates automatically on open

# Private scratch space, personal working notes, never published.
# Anything in here stays on your machine only.
.dev/

# Editor settings
.vscode/
.idea/
```

It's worth knowing what the `.dev/` line costs you. I keep working notes there,
gitignored so they never reach GitHub. Six weeks later I came back to the
project and the folder was gone from the machine I had been working on. Because
it was gitignored there was no copy anywhere, which is exactly what I had asked
for.

Gitignoring a file makes it private and also leaves it without a backup, and
you can't have one without the other. If you want both privacy and a backup,
keep the files in a separate private repository rather than an ignored folder
inside a public one.

Note the `!.env.example` line. The `!` means "except this one": the example
file contains no real secrets and *should* be published, so others know which
keys the project can use.

### `.env.example`, the template

Create `.env.example` in the project root:

```bash
# MicrobeGraph, optional API keys
#
# HOW TO USE:
#   1. Copy this file:   cp .env.example .env      (Windows: copy .env.example .env)
#   2. Fill in real values in .env
#   3. .env is gitignored and must NEVER be committed
#
# Everything here is OPTIONAL. The project runs fully without any of it;
# missing keys just mean slower fetching or a hidden AI feature.

# NCBI (optional). A free key raises the request rate limit from 3/sec to 10/sec.
# Get one: https://www.ncbi.nlm.nih.gov/account/  →  Account settings → API Key
NCBI_API_KEY=

# NCBI asks tools to identify themselves by email. It's a courtesy rather
# than a security measure.
NCBI_EMAIL=

# Anthropic (optional). Only needed for the plain-English answer layer.
# Without it, that one feature hides itself and everything else works.
ANTHROPIC_API_KEY=
```

### `check-public-safe.sh`, the guard at the door

If `.gitignore` is the lock, this script is the guard who checks your bag on the
way out. Locks can be misconfigured, and a second, independent check costs
nothing.

Create `check-public-safe.sh` in the project root:

```bash
#!/usr/bin/env bash
# ---------------------------------------------------------------
# MicrobeGraph, pre-push safety gate
#
# WHY THIS EXISTS:
#   .gitignore tells Git what to ignore. This script checks what Git
#   is ACTUALLY tracking, right now. That makes two independent checks,
#   which is worth having because a secret published once is public forever.
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

# --- 5. Are the language environments being tracked? --------------
# Both are large, machine-specific, and rebuildable from their lockfiles:
# .venv/ from requirements.lock.txt, renv/library/ from renv.lock.
echo -n "5. .venv not tracked ................ "
if git ls-files | grep -qE '^\.venv/'; then
  echo "FAIL"
  echo "   Fix: git rm -r --cached .venv   then commit."
  problems=$((problems+1))
else
  echo "OK"
fi

echo -n "5b. renv/library not tracked ........ "
if git ls-files | grep -qE '^renv/(library|staging|sandbox)/'; then
  echo "FAIL"
  echo "   The R package library is hundreds of MB and rebuildable from renv.lock."
  echo "   Fix: git rm -r --cached renv/library   then commit."
  problems=$((problems+1))
else
  echo "OK"
fi

echo "-----------------------------------"
if [ "$problems" -eq 0 ]; then
  echo "SAFE TO PUSH"
  exit 0
else
  echo "NOT SAFE TO PUSH, $problems problem(s) above. Fix, then re-run."
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

`chmod +x` changes the file's permissions. The `+x` marks it "executable",
meaning it's allowed to run as a program rather than only be read; without it
you'd get "Permission denied".

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

**From now on, run this before every push.** It takes one second, and it
guards against the one mistake you can't undo.

---

## 12. Step 10. The three-branch model

### What a branch is

A **branch** is an independent line of work in the same repository.

Say you're writing a report and want to try a bold restructure, but you don't
want to wreck the version your colleague is reading. So you make a copy called
"experiment" and rework it there. If it turns out well, you replace the main
version; if not, you delete the copy, and the original was never at risk.

Git makes those copies instant and free because it stores the differences
rather than whole duplicate files.

![Where your work goes: develop, then beta and master](img/git_branch_model.svg)

### The three branches, and what each is for

| Branch | Role | Everyday parallel |
|---|---|---|
| **`master`** | The stable, official version | The published edition on the shelf |
| **`beta`** | Release candidate, finished but getting a final look | The advance copy sent to reviewers |
| **`develop`** | Where all day-to-day work happens | Your working draft, with pen marks |

**The rule: you always work on `develop`.** You never edit `master` directly,
and that's what keeps the official version in a good state.

This is a simplified version of a widely used industry pattern; I didn't invent
it for the tutorial.

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

Now publish all three branches to GitHub. `beta` is created **on the remote
only**, pushed straight from `develop`:

```bash
git push -u origin develop
git push origin develop:beta
git push origin develop:master
```

> **Why no local `beta`?** Because you never work on it. The daily push command
> (below) sends local `develop` to remote `beta` directly, so a local copy would
> be one more branch to remember to keep in step, and one more thing to go stale
> for no benefit.
>
> If you keep a working draft on your desk and email copies to two people, you
> don't need a third copy on your desk labelled "the one I emailed to Sam."
>
> A local `beta` does no harm if you'd like one; it just isn't needed.

`origin` is Git's default nickname for "the repository I cloned from", which
here is your GitHub copy. `-u` sets it as the default destination, so later
pushes need less typing.

Move onto `develop`, which is where you'll spend your time from now on:

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

That's two local branches and three on the remote; the `remotes/origin/*`
entries are GitHub's copies. ✅

A useful variant shows which remote branch each local one tracks:

```bash
git branch -vv
```
```
* develop b9c3295 [origin/develop] chore: initial project structure
  master  b9c3295 [origin/master] chore: initial project structure
```

The name in square brackets is the branch's **upstream**: where a bare
`git push` or `git pull` would go. Here both are paired correctly.

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

Why do all three at once? In this project the three branches are *stages of
visibility* rather than separate lines of work. `develop` is where the work
is done, and once a phase is complete and verified, that work becomes the
official version. Keeping them in step with one command means the published
`master` is never quietly out of date.

Then bring your **local** `master` back in step, so your computer matches GitHub:

```bash
git switch master
git pull --ff-only origin master
git switch develop
```

*Why this last bit matters:* the push updated GitHub's `master`, but not your
laptop's. Without the sync-back, your local `master` slowly drifts behind and
one day confuses you. `--ff-only` means "only update if it's a clean
fast-forward; if it isn't, stop and tell me", so Git can never quietly invent a
merge you didn't ask for. I wrote the flag into the command on purpose, so this
works whether or not you set the optional `pull.ff` config earlier.

---

## 13. Step 11. Your first push

Now you can save everything you've created so far.

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

"Untracked" means Git can see the files but isn't watching them yet.

Read this output every time before committing. It's how you notice you're about
to commit something you didn't mean to.

### 2. Stage the changes

```bash
git add -A
```

**Staging** means "include this in the next snapshot".

It's like putting items in a shopping basket: nothing's bought yet, you're only
choosing what goes in on this trip. `-A` means "everything that changed".

### 3. Run the safety gate

```bash
./check-public-safe.sh      # Windows: bash check-public-safe.sh
```

It must say `SAFE TO PUSH`. If it doesn't, fix whatever it names and run it
again.

> **Why staging comes first.** I had this the wrong way round for the first few
> weeks. The gate ran before `git add`, printed SAFE TO PUSH every time, and was
> telling the truth about the wrong snapshot.
>
> The gate inspects what Git is *tracking*, using `git ls-files`. A brand-new
> file that has never been staged is invisible to Git, and so it's invisible to
> the gate too. If you run the check before staging, you're inspecting the
> *previous* state of the repository rather than the one you're about to publish.
>
> It's like checking your bag before you've finished packing it.
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

A word on commit messages: they're notes to your future self, who won't
remember what you did. A common convention starts each message with its type:

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

The three lines at the end are the three branches being updated. ✅

### 6. Sync local master

```bash
git switch master
git pull --ff-only origin master
git switch develop
```

### 7. See it online

Open `https://github.com/yourname/microbegraph` and your files are there. Use
the branch dropdown (top left; it says `master`) to confirm all three branches
exist and match.

**You've just published a project.** That's worth a moment: the
scaffolding, the safety gate and the branch model you've set up are how real
projects are run.

---

## 14. Step 12. Verify everything

This one script checks every piece of the setup at once. Save it as
`check-setup.py` in the project root:

```python
"""
MicrobeGraph, setup verification.

WHY THIS EXISTS:
    Setup has many steps, and a half-finished environment tends to produce
    confusing errors three phases later. This script checks every piece at
    once and tells you exactly which step to revisit.

USAGE:
    python check-setup.py
"""

import shutil              # for finding command-line tools on the PATH
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
# Both bounds matter. The LOWER one: scikit-learn 1.9, which this project
# needs, no longer supports Python 3.10. The UPPER one: a brand-new Python
# release is newer than anything this project is tested on, and some
# scientific packages take months to publish ready-built versions for it
# (pip then tries to compile them and fails). See Troubleshooting T11.
check(
    f"Python {version.major}.{version.minor}.{version.micro}",
    (3, 11) <= version < (3, 14),
    "Need Python 3.11 or 3.12 (3.13 also works for Phases 1-6). "
    "See Step 1 / Troubleshooting T11.",
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
    "(Windows:.\\.venv\\Scripts\\Activate.ps1). See Step 7.",
)

# --- 3. Required packages import ---------------------------------------
# Every package in requirements.txt is listed here. If you add one there,
# add it here too, or this check quietly stops meaning what it says.
#
# NOTE ON THE PAIRS BELOW: a package's INSTALL name and its IMPORT name are
# not always the same. You install "scikit-learn" but you write
# "import sklearn"; you install "python-dotenv" but you write "import dotenv".
# So each entry is (name you install, name you import).
#
# It's like a shop that sells "sparkling mineral water", which at home you
# just call "fizzy water": one thing with two names, depending on where you are.
PACKAGES = [
    ("pandas", "pandas"),
    ("numpy", "numpy"),
    ("requests", "requests"),
    ("tenacity", "tenacity"),
    ("duckdb", "duckdb"),
    ("networkx", "networkx"),
    ("matplotlib", "matplotlib"),
    ("plotly", "plotly"),
    ("pyvis", "pyvis"),
    ("scikit-learn", "sklearn"),        # installs as scikit-learn, imports as sklearn
    ("streamlit", "streamlit"),
    ("pytest", "pytest"),
    ("python-dotenv", "dotenv"),        # installs as python-dotenv, imports as dotenv
]

for install_name, import_name in PACKAGES:
    try:
        __import__(import_name)
        check(f"package: {install_name}", True)
    except ImportError:
        check(f"package: {install_name}", False,
              "Run: pip install -r requirements.txt  (with .venv active). See Step 8.")

# ruff is checked differently, for a reason that's useful to know.
#
# Most packages are LIBRARIES: code you import into your own program.
# ruff is a TOOL: a standalone program you run from the terminal. It installs
# a command rather than something importable, so "import ruff" fails even
# when it is installed perfectly well. Testing it that way would report a
# problem that does not exist, which is worse than not testing it at all.
#
# A kitchen comparison: you check the flour by looking in the cupboard, and
# you check the oven by turning it on. They are different kinds of thing, so
# they need different tests.
check(
    "tool: ruff",
    shutil.which("ruff") is not None,
    "Run: pip install -r requirements.txt  (with .venv active). See Step 8.",
)

# --- 3b. The project's own package -----------------------------------------
# From Phase 1 on, MicrobeGraph is itself an installed package, so that
#     python -m microbegraph.fetch
# works from any folder. "pip install -e ." installs it in EDITABLE mode:
# Python gets a pointer to src/microbegraph/ instead of a copy, so your edits
# are live immediately. We check two things: that it imports at all, and that
# it imports from THIS folder (not from a stale copy somewhere else).
try:
    import microbegraph
    here = Path("src/microbegraph").resolve()
    found = Path(microbegraph.__file__).resolve().parent
    check("package: microbegraph (editable install)", found == here,
          f"It imports from {found}, not from this folder. "
          "Run: pip install -e .  (with .venv active, from the project folder). See Step 8.")
except ImportError:
    check("package: microbegraph (editable install)", False,
          "Run: pip install -e .  (with .venv active, from the project folder). See Step 8.")

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
# never needed. Keeping one anyway is purely a matter of taste.
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
# data/raw and data/processed are NOT checked: data/ is never in Git, so a
# fresh clone does not have it, and the pipeline creates those folders itself
# the first time it writes to them (Phase 1 onwards).
# app/ is not checked either: it arrives with its first file in Phase 8.
for folder in ["docs", "src/microbegraph", "curation", "artifacts", "tests"]:
    check(f"folder: {folder}", Path(folder).is_dir(),
          f"Create it: mkdir -p {folder}. See Step 6.")

# --- 7. Safety files ----------------------------------------------------
check("file: .gitignore", Path(".gitignore").is_file(), "See Step 9.")
check("file: requirements.txt", Path("requirements.txt").is_file(), "See Step 8.")
check("file: pyproject.toml", Path("pyproject.toml").is_file(),
      "It arrives in Phase 1 (docs/03-ingestion-mibig.md). See Step 8.")
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
    print(f"{failed} check(s) failed, see the hints above.\n")
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
  [PASS]  package: tenacity
  [PASS]  package: duckdb
  [PASS]  package: networkx
  [PASS]  package: matplotlib
  [PASS]  package: plotly
  [PASS]  package: pyvis
  [PASS]  package: scikit-learn
  [PASS]  package: streamlit
  [PASS]  package: pytest
  [PASS]  package: python-dotenv
  [PASS]  tool: ruff
  [PASS]  package: microbegraph (editable install)
  [PASS]  git installed
  [PASS]  git identity configured
  [PASS]  local branch: master
  [PASS]  local branch: develop
  [PASS]  remote branch: origin/master
  [PASS]  remote branch: origin/beta
  [PASS]  remote branch: origin/develop
  [PASS]  folder: docs
  [PASS]  folder: src/microbegraph
  [PASS]  folder: curation
  [PASS]  folder: artifacts
  [PASS]  folder: tests
  [PASS]  file: .gitignore
  [PASS]  file: requirements.txt
  [PASS]  file: pyproject.toml
  [PASS]  file: check-public-safe.sh
====================================================
All checks passed. Your workshop is ready.
```

✅ **Major checkpoint.** Every line says `PASS` and none says `FAIL`. Your
machine is set up, and you never have to do this again on this computer.

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

Setup was the long part. Day-to-day work looks like this:

**Starting a session:**

```bash
cd ~/projects/microbegraph          # Windows: cd $HOME\projects\microbegraph
source .venv/bin/activate           # Windows: .\.venv\Scripts\Activate.ps1
git switch develop
```

That's three lines. (The [Handbook](HANDBOOK.md#every-session-after-setup)
keeps the up-to-date version of this routine.)

**Ending a session:**

```bash
git add -A                   # stage FIRST, the gate can only see tracked files

pytest -q                    # once tests exist (Phase 1 onward)
ruff check .                 # once code exists (Phase 1 onward)
./check-public-safe.sh       # must say SAFE TO PUSH

git commit -m "feat: describe what you did"
git push origin develop develop:beta develop:master
## --tags is optional, only when a release tag was created

git switch master
git pull --ff-only origin master
git switch develop
```

On a second machine (say you set up on your laptop and now want to work on a
Linux VM), the whole setup shrinks to this:

```bash
git clone https://github.com/yourname/microbegraph.git
cd microbegraph
git switch develop              # creates your local develop from origin/develop
python3.11 -m venv .venv        # or python3.12, whichever you have
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
python check-setup.py
```

It's eight lines because everything needed was written down. That's what
`requirements.txt`, `.gitignore` and the verification script are for: the setup
lives in files instead of in your memory.

---

## 16. Troubleshooting

### T1: "python: command not found" / "not recognised"

The command exists but your computer doesn't know where to look (the PATH
problem from Step 1).

- **Windows:** the "Add python.exe to PATH" box wasn't ticked. Re-run the
  installer → **Modify** → ensure "Add Python to environment variables" is on.
  Then **open a new PowerShell window**; existing windows keep the old PATH.
- **macOS/Linux:** try `python3` instead of `python`. On RHEL 8 try
  `python3.12`. Whichever works is your command from now on.
- **Still stuck?** `which python3` (macOS/Linux) or `where.exe python`
  (Windows) shows where the system is looking.

### T2: "Permission denied" running `./check-public-safe.sh`

The file isn't marked executable.

```bash
chmod +x check-public-safe.sh
```

On Windows, use `bash check-public-safe.sh` instead, because Windows doesn't
use the executable bit.

### T3: `ModuleNotFoundError` after installing

Almost always, this means the virtual environment isn't active, so `pip`
installed into a different Python from the one running your script.

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

Windows blocks scripts by default. Run this once:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Then try activating again.

### T5: Git asks for a password and rejects the right one

GitHub stopped accepting account passwords for Git operations. Use your
**Personal Access Token** as the password (Step 5, Option A). The username is
still your GitHub username.

### T6: `git push` rejected, "Updates were rejected because the remote contains work that you do not have locally"

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

Then either run `git pull --rebase origin develop` (which replays your commits
on top of theirs, the tidier option) or ask for help. **Never** run
`git push --force` on a shared branch to make an error go away; it deletes other
people's work.

### T7: `git pull --ff-only` fails, "Not possible to fast-forward"

Your local branch and the remote have both moved, so there's no clean line to
follow. This is Git protecting you, doing exactly what it was configured to
do.

Look before you change anything:

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

The order matters. Rewriting history takes time, and copies may already exist;
revoking makes the leaked value worthless immediately, and it's the only step
that actually closes the hole.

### T10: RHEL 8, `python3.12: command not found` after `dnf install`

Your RHEL 8 minor version may not carry that module. Check what's offered:

```bash
dnf module list python3*
```

Install whichever 3.9+ version is listed, then use that name everywhere
`python3.12` appears in this tutorial. **Do not** remove the system `python3`:
`dnf` itself depends on it.

### T11: pip fails to build a package with C compiler errors

This one cost me an evening, so it gets a long entry.

I ran `pip install -r requirements.txt` and got 788 lines of red output. The
line that mattered was buried in the middle:

```
error: Failed building wheel for gensim
× Failed to build installable wheels for some pyproject.toml based projects
```

Above it, pages of C compiler complaints about things called `ma_version_tag`,
`ob_digit` and `curexc_traceback`.

I started reading from the bottom, which was the wrong end. The answer was
sitting in the file paths, and every one of them said `python3.14`.

So what was going on? Some Python packages contain C code for speed. Normally
pip downloads a pre-built version, called a wheel, that someone has
already compiled and tested for your exact Python version and operating system.
No wheel existed for 3.14, so pip fell back to compiling gensim from source on
my laptop. Gensim's C code refers to internal parts of Python that newer
versions have removed, so the compile failed.

Nothing was wrong with my machine, my setup, or the package. I was just early.
The scientific Python ecosystem usually takes six to twelve months to catch up
with a new release, because every package containing C code has to be rebuilt
and tested.

**So check your version before reading any of the error:**

```bash
python --version
```

If it says 3.14 or higher, that's your cause: you're inside the 6-12 months the
ecosystem needs to rebuild and test every package with compiled code.

**The fix: rebuild the environment on a suitable Python version.**

1. **First check whether you already have one.** Type `python` and press
   <kbd>Tab</kbd> twice (PowerShell: run `py --list`):

   ```bash
   python⇥⇥
   ```
   ```
   python3.11          python3.13          python3.14
   ```

   Look for **3.11** or **3.12**. If one is there, **skip to step 2**; you don't
   need to install anything. Most people who hit this error already have a
   usable version and just built the environment with the wrong one.

   Only if nothing in range is there, install **Python 3.12** from
   <https://www.python.org/downloads/>, scrolling past the big green button to
   find 3.12.x. It installs *alongside* your existing versions, and nothing is
   removed.

2. **Delete the virtual environment.** It's disposable by design (this is
   exactly the situation venvs exist for), and nothing of yours is lost:

   ```bash
   deactivate                    # leave it first (ignore any error if not active)

   rm -rf .venv                  # macOS / Linux
   # Remove-Item -Recurse -Force .venv     # Windows PowerShell
   ```

3. **Create a new one, naming your chosen version explicitly:**

   ```bash
   python3.11 -m venv .venv                # macOS / Linux, use the version you found
   # python3.12 -m venv .venv              # ...or this one
   # py -3.12 -m venv .venv                # Windows
   ```

   ⚠️ **`python3.12: command not found` here means you don't have 3.12.** Use
   whichever version the Tab-completion check in step 1 actually listed; the name
   must match something that exists on your machine.

4. **Activate and confirm the version:**

   ```bash
   source .venv/bin/activate               # Windows:.\.venv\Scripts\Activate.ps1
   python --version
   ```
   ```
   Python 3.11.9
   ```

5. **Install again:**

   ```bash
   pip install -r requirements.txt
   ```

   Expect it to be much faster this time: with wheels available, pip downloads
   ready-made packages instead of compiling anything.

✅ **Checkpoint.** `python check-setup.py` prints "All checks passed".

If you can't install a different Python (on a locked-down work machine, say),
there's still a route: everything in `requirements.txt` has wheels for a wide
range of versions, and the two fragile embedding libraries live separately in
`requirements-ml.txt`. Skip that second file and Phases 1-6 work normally.
Phase 7 documents a pure-scikit-learn fallback that computes embeddings without
gensim. It's slower on very large graphs, but entirely adequate at this
project's size.

The lesson I took from it: for data and scientific work, run **one or two
versions behind the newest** Python. The newest release is for people testing
the language itself. Staying a little behind is standard practice in the field,
and it saves hours of exactly this kind of confusion.

### T12: Corporate proxy / firewall blocks `pip`

On a locked-down work VM, `pip` may fail with connection timeouts. Ask IT for
the proxy address, then:

```bash
pip install --proxy http://proxy.company.com:8080 -r requirements.txt
```

To make it permanent, set the `HTTPS_PROXY` environment variable, or add a
`pip.conf` (`pip.ini` on Windows). Your IT team will know which applies.

### T13: Push refused: "refusing to allow a Personal Access Token to create or update workflow"

**When:** the first push that includes `.github/workflows/ci.yml` (Phase 1).

**Why:** files in `.github/workflows/` tell GitHub to run programs, so GitHub
asks for an extra permission before accepting them. A token made with only the
`repo` scope does not have it. Nothing is wrong with your code.

**Fix (Personal Access Token users):**

1. GitHub → avatar → **Settings** → **Developer settings** → **Personal access
   tokens** → **Tokens (classic)**.
2. Click your `microbegraph laptop` token, tick **`workflow`** as well as `repo`,
   and click **Update token**. (Fine-grained tokens: give the repository
   **Workflows: Read and write**.)
3. Push again. If Git still uses the old permission, clear the stored password so
   it asks for the token again:
   * Windows: **Credential Manager** → *Windows Credentials* → remove the
     `git:https://github.com` entry.
   * macOS: **Keychain Access** → search `github.com` → delete the entry.
   * Linux / RHEL 8 (cache helper): `git credential-cache exit`.

**SSH users** (Option B in Step 5) are not affected: SSH keys can push workflow
files already.

### T14: `bash check-public-safe.sh` fails with `$'\r': command not found` (Windows)

**Why:** Windows ends lines with two invisible characters, macOS and Linux with
one, and bash only understands the second kind. The repository's
`.gitattributes` file tells Git to always write shell scripts with Linux line
endings, but a copy checked out *before* that file existed keeps the old ones.

**Fix** (once, in the project folder):

```powershell
git add --renormalize .
Remove-Item check-public-safe.sh
git checkout -- check-public-safe.sh
bash check-public-safe.sh
```

The script is written out again with the right line endings and runs normally.

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
- [ ] `requirements.lock.txt` exists (created by `pip freeze --exclude-editable`)
- [ ] `./check-public-safe.sh` prints `SAFE TO PUSH`
- [ ] `python check-setup.py` prints "All checks passed"
- [ ] You have pushed at least once and can see your files on github.com

**If anything is unticked, fix it now.** Every later phase assumes all of this.

Along the way you've learned what a terminal is and the five commands that
matter; what Python is and why version numbers matter; why a code editor
beats a text editor; what Git is, what a commit is, and what a branch is; how to
authenticate to GitHub safely; what a virtual environment is and the real
problem it solves; what a package and a requirements file are; why secrets must
be protected before you have any; the three-branch model and the push that keeps
them in step; and the habit of verifying every step instead of assuming.

That's a solid foundation, and it carries over to every project you build
after this one.

---

> **From here on, every change you make ends with the same short sequence.**
> The commit-message convention, a ready-written message for every phase, and
> what to do when something goes wrong are all in
> [`GIT-WORKFLOW.md`](GIT-WORKFLOW.md). Keep it open in a tab.

**Next:** [`02-ontology-and-data-model.md`](02-ontology-and-data-model.md), the
rulebook that decides what may become a dot and what may become an arrow, and
why it's worth writing *before* any code (it's what keeps the graph from
turning into a tangle).
