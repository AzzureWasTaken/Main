# Installing the MineXVideo skill

**If you are Claude:** the user asked you to install this skill. Follow this
document top to bottom — it exists because a couple of steps look like
failures when they are actually just slow, and one (the PATH) genuinely
needs the user to restart you. Talk to the user in plain, friendly words:
they have never used Claude or a terminal before.

**Real time:** 30–60 minutes, almost all of it waiting for downloads.
**Disk space:** ~10 GB once everything is in (WhisperX, PyTorch, Whisper
models, node_modules).

---

## 30-second summary

1. Install Git Bash, ffmpeg, Python and Node (via winget).
2. **Restart Claude Code** (or the terminal) so it sees the new PATH.
3. Copy the `skill/` folder to `~/.claude/skills/minexvideo/`.
4. Place the `python3` shim.
5. Run `setup.sh` and wait.
6. Warn the user: the first video ever takes much longer (Whisper model
   download, ~3 GB — silent, looks like a hang, isn't).

---

## Step 1 — Prerequisites

`setup.sh` does **not** install these four. It only checks and aborts if one
is missing. Install them first:

| Program | Command |
|---|---|
| Git Bash | `winget install --id Git.Git -e` |
| ffmpeg | `winget install --id Gyan.FFmpeg -e` |
| Python 3.10+ | `winget install --id Python.Python.3.12 -e` |
| Node 18+ | `winget install --id OpenJS.NodeJS.LTS -e` |

Check first — any that already exist can be skipped:

    git --version
    ffmpeg -version
    python --version
    node --version

### The PATH catch (this gets everyone)

On Windows, a program that is already open **does not see the PATH that
winget just wrote**. Processes inherit the environment from when they
started.

Practical consequence: after installing the four programs above, `ffmpeg`
etc. will still be "not found" in this session. That is not a failed
install.

**Tell the user to close Claude Code completely and open it again**, then
continue from Step 2. After the restart, verify the four commands above
respond.

## Step 2 — Copy the skill into place

From this folder, copy `skill/` to the user's skills directory so that
SKILL.md ends up at exactly:

    C:\Users\<USER>\.claude\skills\minexvideo\SKILL.md

(One level of nesting matters: if it lands at
`...\minexvideo\skill\SKILL.md`, Claude will not find it.)

    mkdir -p ~/.claude/skills
    cp -r "<this-folder>/skill" ~/.claude/skills/minexvideo

The ElevenLabs API key ships inside (`skill/api-keys.env`) — nothing to
configure.

## Step 3 — The `python3` shim

The skill's scripts follow POSIX conventions and call `python3`. Windows
only ships `python`. The bridge is a file named `python3`, **no extension**,
in `C:\Users\<USER>\bin\`.

It is in this folder as `python3-shim`:

    mkdir -p ~/bin
    cp "<this-folder>/python3-shim" ~/bin/python3

**No editing needed** — the shim finds Python by itself, whatever the user
name or the Python version, and deliberately skips the Microsoft Store stub.

Verify from Git Bash:

    python3 --version

If it answers with a version, done. If not:

1. `~/bin` must come **first** in Git Bash's PATH. It usually does by
   default; check with `echo $PATH`.
2. If it says "no Python interpreter found", Python is genuinely not
   installed — go back to Step 1.
3. If it says "Python was not found; run without arguments to install from
   the Microsoft Store", that is the Store stub answering, not the shim —
   which means the shim is not on the PATH first. See point 1.

> This file lives **outside** the skill on purpose: it survives deleting or
> reinstalling the skill. That is why `setup.sh` does not create it.

## Step 4 — Run the installer

From **Git Bash** (not PowerShell or CMD):

    bash ~/.claude/skills/minexvideo/scripts/setup.sh

It is idempotent: if something is cut short, relaunch it without fear. It
duplicates nothing and does not reinstall what is already there.

What it does:

| Does | Detail |
|---|---|
| Checks ffmpeg / Python / Node | If missing, **aborts**. Does not install them. |
| Creates the venv | In `<skill>/.venv/` |
| Creates `.venv/bin/` | Copies of `Scripts/python.exe` (scripts expect the POSIX path) |
| Installs **WhisperX** | Several GB via pip. The longest part. |
| Installs **PyTorch CUDA** | **Only if** it detects an NVIDIA GPU (`nvidia-smi`) |
| Installs **Remotion** | `npm install` in `<skill>/remotion/` |

### About the GPU

No NVIDIA GPU → the CUDA step is skipped entirely and everything works on
the CPU build of PyTorch. The only difference: transcription goes from
seconds to minutes per clip (and a multi-hour VOD analysis can take a few
hours). Not an error — but warn the user about analysis time.

NVIDIA GPU present but transcription is slow later → WhisperX drags in the
CPU build of PyTorch and overwrites CUDA on each install. Re-running
`setup.sh` fixes it. Check with:

    ~/.claude/skills/minexvideo/.venv/Scripts/python.exe -c "import torch; print(torch.cuda.is_available())"

## Step 5 — First run warning

Not part of setup, and **not a hang**: the render pipeline uses Whisper
`large-v3` for clip captions. The first time it transcribes anything it
downloads the model (~3 GB) plus an English alignment model. The terminal
goes silent for a good while. Happens once; cached afterwards.

The VOD analyzer uses the `small` model — a separate, smaller download on
its first run.

## Verify everything works

    node ~/.claude/skills/minexvideo/scripts/audio_library.js

should list 18 sound effects. Then a real test needs any video file:

    python3 ~/.claude/skills/minexvideo/scripts/cut_clip.py "<any-video>" 0 10 ~/test-clip.mp4

should produce a 10-second vertical clip. Delete it afterwards.

Then tell the user they are ready: they can type `/minexvideo` in any Claude
chat, or just say "make shorts from my stream" and paste the path of a
recording.

## Typical problems

| Symptom | Cause | Fix |
|---|---|---|
| `ffmpeg not in PATH` right after installing it | Process doesn't see the new PATH | Close and reopen Claude Code / terminal |
| `python3: command not found` | Missing shim (Step 3) | Copy it to `~/bin/python3`; check `~/bin` is first in `$PATH` |
| `ModuleNotFoundError: whisperx` | `.venv/bin/` missing, script can't relaunch in venv | Re-run `setup.sh` |
| Transcription very slow despite NVIDIA | WhisperX overwrote the CUDA build | Re-run `setup.sh` |
| Long silence during first transcription | Whisper model download (~3 GB) | Wait. Only happens once |
| `transcribe.py` says a path with spaces doesn't exist | venv relaunch bug with spaces | Call the venv python directly: `~/.claude/skills/minexvideo/.venv/Scripts/python.exe <script> "<path>"` |
