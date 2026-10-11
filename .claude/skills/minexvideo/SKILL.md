---
name: minexvideo
description: Turns a LONG raw stream recording (a VOD of 1-5 hours) into finished, edited YouTube Shorts of Minecraft gameplay — automatically. It analyzes the whole VOD, finds the most viral-worthy moments (funny fails, big wins, rage, clutch plays, wholesome bits), cuts them into vertical clips under 60 seconds, and edits each one with karaoke captions, meme text, camera moves (punch zooms, shakes), emojis, speed ramps, slow motion, freeze frames, sound effects and optional music. TRIGGER when the user mentions a stream recording, VOD, raw video, long gameplay video, or asks for clips/shorts from their stream. Phrases - "make shorts from my stream", "here is my VOD", "find the best clips", "edit my stream", "cut my video into shorts", "make this clip funnier", "add captions", "install this skill".
---

# MineXVideo — from raw stream to finished Shorts

Takes one LONG raw recording (a whole stream: one to five hours) and delivers
**finished vertical Shorts, ready to upload**, in a tidy folder. The user does
not need to know anything about video editing, AI, or the command line. You do
all of it.

The pipeline: **analyze the VOD → pick the best moments → cut them into
vertical clips → edit each one → deliver organized in folders.**

---

## 🗣️ How to talk to the user

The people using this skill have **zero experience with Claude or editing
tools**. This changes how you communicate:

- **Plain words, always.** Never say "I'll run the transcription pipeline" —
  say "I'm listening to the whole video to find the best moments (this takes
  a while the first time)".
- **When the skill starts** (the user typed `/minexvideo` or asked for shorts
  without giving a file), greet them and ask for the video like this:

  > Hi! I'll find the best moments in your stream and turn them into edited
  > Shorts, ready to upload.
  >
  > To start, tell me where your recording is: find the video file,
  > **right-click it → "Copy as path"**, and paste it here.
  >
  > I'll save the finished Shorts in your **Downloads** folder (in a folder
  > called "MineXVideo Shorts"). If you'd rather have them somewhere else,
  > just tell me.

- **Tell them they can ask for anything in plain English**: "make clip 2
  funnier", "that zoom is too much", "remove the music", "cut the first bit".
  You translate that into edits (see the table near the end).
- **Report progress in human terms**: "Found 6 great moments — a creeper fail
  at 1:32:10, a clutch water bucket save at 2:04:55…" not file paths and JSON.
- **Long steps deserve a warning.** The very first video takes much longer
  (models get downloaded, ~3 GB). Say so, or they will think it crashed.

## ⚙️ Settings that persist

Keep a small `config.json` **next to this SKILL.md** (create it on first run):

```json
{ "output_dir": "C:/Users/<user>/Downloads/MineXVideo Shorts" }
```

If the user asks to change where Shorts are saved, update this file and
confirm in one sentence. Read it at the start of every session.

---

## The workflow, start to finish

### Step 1 — Analyze the VOD

```bash
python3 ~/.claude/skills/minexvideo/scripts/analyze_vod.py "<path-to-vod>"
```

This extracts the audio, measures loudness second by second, and transcribes
the whole thing with a fast Whisper model. It prints the workdir where it
leaves:

- `transcript.txt` — everything said, with `[HH:MM:SS]` timestamps
- `peaks.txt` — the loudest moments, ranked (screams, laughter, hype)
- `info.json` — duration, resolution, fps

⏳ On a PC without an NVIDIA GPU a 3-hour VOD can take a long while to
transcribe. Warn the user, and mention it only happens once per video (it is
cached). The analysis transcript uses a small model on purpose — final
caption quality does not depend on it, clips are re-transcribed properly.

### Step 2 — Pick the moments (this is YOUR judgement)

Read `transcript.txt` and `peaks.txt` and choose the clip-worthy segments.
The loudness peaks tell you where the streamer *reacted*; the transcript
tells you *why*. Cross-reference both. What makes a Minecraft Short work:

- 😂 **Funny fails** — dying stupidly, falling in lava, creeper ambushes
- 🔥 **Clutch plays** — MLG water bucket, 1-heart escapes, boss kills
- 💎 **Big moments** — rare loot, finding diamonds/netherite, completing a build
- 😡 **Rage / big reactions** — screaming, losing items, raid gone wrong
- 🤣 **Jokes and banter** — a good story, trolling a friend, chat moments
- 😮 **Surprises** — anything where the streamer goes "WHAT?!"

Rules for choosing:

- **Each clip must stand alone.** A viewer who never saw the stream must get
  it. If it needs context, either include the setup or skip it.
- **Under 60 seconds after editing — always.** Aim for **15–45 s** of source
  material. Shorter is better; the punchline decides the length, not the
  other way round. (Why 60 is a hard wall: YouTube's Shorts music licensing
  only covers up to 60 s — a longer video with a claimed track gets blocked.)
- **The moment needs a hook** — something you can promise in the first
  second ("HE HAD ONE HEART").
- Typically a 2–3 hour stream yields **3–8 good clips**. Do not pad the
  count with mediocre ones; a boring Short hurts the channel.

Present the list to the user in plain words ("I found 6 moments: …") and
**keep going without waiting** — this skill is meant to run start-to-finish.
They can ask for changes after seeing the results.

### Step 3 — Cut each moment into a vertical clip

```bash
python3 ~/.claude/skills/minexvideo/scripts/cut_clip.py "<vod>" <start> <end> \
  "<output_dir>/<vod-name>/short-1/clip.mp4"
```

- Times accept seconds or `H:MM:SS`. Cut a touch wide (±1–2 s of breathing
  room); tighter trimming happens in the edit.
- By default it **center-crops to 9:16** (1080x1920) — the standard Minecraft
  Shorts look. If the action is off-center (crosshair drifts left/right at
  the key moment), pass `--focus-x 35` / `--focus-x 65`. If the wide frame
  itself matters (a big build, the chat), use `--mode blur`.
- One folder per short: `<output_dir>/<vod-name>/short-1/`, `short-2/`, …

### Step 4 — Edit each clip

Each clip is edited through a plan file + render, exactly like a human editor
iterating. Full editing doctrine lives in `knowledge/` — **read
`knowledge/editing_choices.md` before writing your first plan**, and follow
`knowledge/hard_rules.md` always.

```bash
# 1. Write clip.plan.json (see "The plan" below) with at least the hook.
# 2. Preview render — transcribes the clip properly (word-level) on the way:
bash ~/.claude/skills/minexvideo/scripts/render.sh "<...>/short-1/clip.mp4"
# 3. Read <workdir>/words.json (printed by the render) and refine the plan:
#    memes on the punchlines, zooms on the hits, ramps over dead air.
# 4. Re-render the preview (cheap — only changed stages re-run) and check
#    frames with: bash scripts/extract_stills.sh "<...>/clip.mp4"
# 5. When the edit is right, deliver:
QUALITY=final bash ~/.claude/skills/minexvideo/scripts/render.sh "<...>/clip.mp4"
```

The pipeline is **incremental**: changing a beat only re-runs the render;
transcription and cuts are cached. Iterating is cheap — do it.

**This skill runs autonomously.** Unlike a human-supervised workflow, do not
stop to ask "is the preview OK?" — review your own preview stills against
the hard rules, fix what's off, then produce the final. The user reviews
finished Shorts and asks for changes in plain words afterwards.

### Step 5 — Deliver, tidy

For every short, the deliverable goes in its folder with a clean name:

```
MineXVideo Shorts/
└── my-stream-2026-08-28/
    ├── short-1/
    │   ├── short-1.mp4                ← ready to upload (no music)
    │   ├── short-1 with music.mp4     ← only when music helps (see Music)
    │   └── (clip.mp4, clip.plan.json, previews… – working files, leave them)
    ├── short-2/
    │   └── short-2.mp4
    └── ...
```

```bash
cp "<...>/short-1/clip.final.mp4" "<...>/short-1/short-1.mp4"
```

Finish by telling the user, in plain words, what each short is ("short-1 is
the creeper explosion fail, 34 seconds…"), where they are, and that they can
ask for any change by just describing it.

---

## 🎯 The 60-second rule

**Every short must come out under 60 seconds — aim at ~58 max.** YouTube's
Shorts music licensing only covers 60 s; past that, a claimed track blocks
the video. If a moment runs long, in order of preference:

1. **Cut tighter** — you control the cut; this is the big lever this skill
   has that a clip-only editor does not.
2. **Speed up the dead parts** (`ritmo` ramps, x2–x3 on walking/mining).
3. **Speed up everything** (`velocidad` up to ~1.5).
4. **Split it into two shorts** if it is really two moments.

## The one rule above all others

**Never cover the gameplay.** The viewer came to watch Minecraft. All
overlays are partial by design; captions run edge to edge of the short. If
an overlay does not react to what is on screen, it does not belong.

---

## The plan

Each clip is described by one JSON file next to it: `clip.mp4` →
`clip.plan.json`. ⚠️ **The plan's field names are in Spanish** (the render
machinery is shared with a sister skill) — copy them exactly as written
here. Everything the viewer READS (titles, meme text, labels) must be in
**English**.

```jsonc
{
  "accent": "grass",          // default color of the short
  "enfasis": ["one heart"],   // phrases captioned EXTRA LARGE (0–2, short words only)
  "grade": 1,                 // 0 = no color pop, 1 = default
  "apertura": 1.12,           // opening frame punch; false removes it
  "velocidad": 1.5,           // optional — speeds up the whole short (1 = off)

  // ── Editor tools. All optional; read knowledge/editing_choices.md first ──
  "ritmo": [ /* speed ramps & freeze frames per segment */ ],
  "efectos_voz": [ /* pitch-up, pitch-down, megaphone, echo, robot */ ],
  "subtitulos": { "estilo": "karaoke", "tramos": [ /* ... */ ] },
  "transiciones": "pixelize", // only with multiple clips joined
  "zoom": [ /* manual camera; otherwise derived from beats */ ],
  "sfx": [ { "path": "whoosh.mp3", "at_sec": 3.2 } ],
  "cortar_silencios": true,   // cut dead-air gaps
  "censura": true,            // profanity bleep — see Censorship

  "beats": [ /* the overlays — see vocabulary below */ ]
}
```

Every beat always carries `kind`, `start_sec`, `end_sec` and `reason`. The
`reason` is one line saying what the overlay adds — the linter requires it,
and if you cannot write one, the beat should not exist. Times are in
**seconds of the final timeline** (after ramps/speed), except `ritmo`, which
by necessity measures on its input — the pipeline prints the mapping.

### Accent colors — pick by meaning

| Accent | When |
|---|---|
| `grass` | Neutral, positive. Default. |
| `diamond` | Loot, achievements, something valuable. |
| `gold` | Numbers, records, counts. |
| `redstone` | Danger, death, fails, things going wrong. |
| `purple` | Secrets, magic, "what you didn't know". |
| `white` | When color would distract. |

### Beat vocabulary

| kind | For | Lane |
|---|---|---|
| `hook_title` | The frame-0 hook. **Mandatory, always at 0.0.** | top-center |
| `meme_text` | The punchline. Most used. 2–4 words, UPPERCASE. | top-center |
| `counter` | A number that counts up ("DIED 47 TIMES"). | top-center |
| `item_card` | Item/block card. **Only with a real icon PNG.** | per `anchor` |
| `tip_banner` | A usable fact or trick. | low band |
| `speech_bubble` | Comic bubble — voicing mobs, roleplay. | low band |
| `image_overlay` | Meme/screenshot as a floating card. Never full-screen. | center |
| `spotlight` | Darkens all but a circle. Use sparingly. | no lane |
| `emoji_burst` | Emoji reactions over gameplay. | no lane |

Two beats in the same lane must not overlap (the linter rejects it).
Full JSON schemas for every beat: `knowledge/templates.md`.

```jsonc
// The two you will use most:
{ "kind": "hook_title", "start_sec": 0.0, "end_sec": 2.0,
  "title": "ALMOST\nDIED", "emoji": "💀", "accent": "redstone",
  "reason": "..." }

{ "kind": "meme_text", "start_sec": 4.2, "end_sec": 6.0,
  "text": "THAT WAS\n*THE PLAN*",     // *word* takes the accent color
  "emoji": "😰", "impact": 1, "reason": "..." }
```

### Camera

If you say nothing, every `meme_text`/`counter` gets an automatic punch zoom.
Declare movement inside a beat for control:

```jsonc
{ "kind": "meme_text", ..., "zoom": { "tipo": "punch", "scale": 1.3,
    "focus": { "x": 62, "y": 44 }, "shake": 0.9, "rot": -1.2 } }
```

Types: `punch` (hit), `snap` (harder hit), `rampa` ("look at this"), `push`
(rising tension), `pull` (reveal). Scale 1.15–1.45; above 1.5 pixels show.
At most two zooms ≥1.3 per short. `shake` 0.4–1.2 for falls/explosions.

### Ritmo — speed ramps, slow motion, freezes

```jsonc
"ritmo": [
  { "tipo": "rampa", "start_sec": 12.0, "end_sec": 20.0, "factor": 3.0,
    "silencio": true },                      // fast-forward the boring part, muted
  { "tipo": "rampa", "start_sec": 31.2, "end_sec": 32.4, "factor": 0.5,
    "tono": "sigue" },                       // slow-mo the hit, voice drops too
  { "tipo": "congelado", "en_sec": 24.8, "duracion": 0.7 }  // freeze frame
]
```

With narration over it: max x1.6 speed-up. Without: x2–x4. Slow-mo only on
THE moment, under 1.5 s. Freeze only in a speech gap. `ritmo` times measure
on the source that enters that stage — decide ramps FIRST, render once, then
write beats reading the already-translated `words.json`. If the timeline
changes after beats exist: `python3 scripts/tiempo.py --workdir <wd> --recoloca plan.json`.

### Voice effects

```jsonc
"efectos_voz": [ { "start_sec": 12.4, "end_sec": 14.0, "tipo": "agudo" } ]
```

`agudo` (pitch up — mobs, panic), `grave` (villain), `megafono` (radio/server
announcement), `eco` (reveal, cave), `robot` (golem, AI). Max two per short,
0.8–3 s each, never over information the viewer must understand.

### Caption styles

Karaoke is the default and the signature. Two alternates, for SEGMENTS only:
`palabra` (one huge word at a time — bursts, countdowns) and `bloque` (boxed
line — snow/desert/End where outlines struggle). Under 45% of the short.

```jsonc
"subtitulos": { "tramos": [ { "start_sec": 20.0, "end_sec": 27.5, "estilo": "palabra" } ] }
```

### Joining multiple cuts into one short

`render.sh "c1.mp4" "c2.mp4"` joins them into a single timeline (in order,
no trimming — cut first with cut_clip.py). Optional transitions at the
joins: `"transiciones": "pixelize"` (place change), `smoothleft` (same
action continues), `fadewhite` 0.15–0.25 s (impact), `corte` (hard cut —
usually best). Duration 0.2–0.5 s. The printed map says where each clip
starts on the joined timeline.

---

## Sound effects (ElevenLabs)

The single highest-value editing touch. Declared in the plan:

```jsonc
"sfx": [ { "path": "whoosh.mp3", "at_sec": 3.2, "volumen": 0.9 } ]
```

**Check the library before generating** — 18 effects ship with the skill:

```bash
node ~/.claude/skills/minexvideo/scripts/audio_library.js          # all
node ~/.claude/skills/minexvideo/scripts/audio_library.js impact   # search
```

If nothing fits, generate (uses the ElevenLabs key in `api-keys.env`):

```bash
node ~/.claude/skills/minexvideo/scripts/elevenlabs_audio.js \
  --type sfx --prompt "heavy cartoon impact thud, short and punchy, no music" \
  --out big-thud.mp3 --dur 1.0 --desc "Heavy punchline thud" --tags "impact,punchline"
```

- Prompts describe the SOUND, not the scene. Always add `no music` to SFX
  prompts. `--dur` ≤ 1 s for editing hits.
- **A sound only plays where the game would make it.** No whoosh without a
  camera move, no ding without a counter. One effect per gesture that
  already exists in the edit; 3 good ones beat 9.
- Generated files land in the library and are reused — do not regenerate
  what exists (it costs the user's credits).

### Character voices — and one hard line

- ❌ **Never generate or clone the streamer's own voice.** If narration is
  missing, leave it missing.
- ✅ **Character voices are fine**: a villager, a creeper "speaking", the
  server announcer. `--type voice --text "..." --voice <id>`. Pick a voice
  per character and reuse it. Useful stock voices:
  `N2lVS1w4EtoT3dr4eOWO` (sly), `SOYHLrjzK2X1ezoPC6cr` (fierce — enemies),
  `IKne3meq5aSn9XLyUdCD` (deep, energetic), `JBFqnCBsd6RMkjVDRZzb` (warm narrator).

## Music — two files, the user chooses by watching

Music is **occasional, not default**. Generate a with-music version only
when it clearly helps: gaps in the narration, comedy where music lands the
joke, fast montages. Skip it when: voice runs wall-to-wall, the clip's own
audio IS the joke, the short is under ~12 s, or tension/silence carries it.
The user can also simply ask for it or forbid it — they win.

When you DO add music, deliver **both files**: `short-N.mp4` (no music — the
uploader may prefer YouTube's own track picker) and `short-N with music.mp4`.
SFX go in both. When you decide against music, say so in one sentence.

**Never render twice for this.** Render once without music, then:

```bash
node scripts/elevenlabs_audio.js --type music --dur 40 --out playful-comedy.mp3 \
  --prompt "Playful bouncy comedy music, ukulele and light percussion, upbeat, loopable, no vocals"
python3 scripts/mezcla_musica.py "short-1.mp4" "short-1 with music.mp4" \
  "<skill>/assets/audio/music/playful-comedy.mp3" --volumen 0.18 --ducking 1
```

Always `no vocals` in the prompt; the track's mood follows the **narration**,
not the gameplay. Generate 3–5 s longer than the short (fade-out needs tail).
Reuse library tracks; do not compose a new one per short.

## 🔇 Censorship — ON by default

Swearing gets bleeped in the audio AND masked in the captions (`f***`),
automatically, between transcription and captions. YouTube demonetizes
heavy profanity in the first seconds, so this protects the channel.
Disable per short with `"censura": false` if the user asks, or tune:

```jsonc
"censura": { "extra": ["someword"], "excluir": ["hell"] }
```

The list (English) lives in `scripts/censura.py`. Mild words (hell, damn,
crap) are deliberately not censored.

---

## Hard rules (linter-enforced or close)

1. **Hook at frame 0** — a `hook_title` starting at `0.0`, always.
2. **Captions always on** — most Shorts are watched muted.
3. **A beat every 2–4 seconds** — coverage between 40% and 75% of the clip.
4. **Safe zones** — top 8% and bottom 18% belong to YouTube's UI.
5. **Every beat justifies itself** via `reason`.
6. **The ending lands** — last beat is the punchline, never a sign-off.
7. **Special resources: ~one per 8 seconds, ceiling.** Remove any resource
   the short does not miss.
8. **Don't make two shorts the same** — vary the dominant register between
   shorts from the same VOD (rhythm / voice / data / reaction / sound).

Details and reasoning: `knowledge/hard_rules.md`.

## Translating user requests

| The user says… | You do… |
|---|---|
| "more energy" / "faster" | more beats, punch zooms, a speed ramp on the flattest stretch |
| "funnier" | more `emoji_burst` + `meme_text`; a pitch-up voice bit; freeze on the fail |
| "calmer" / "too much" | fewer beats, gentler zooms (`rampa` 1.15), no shakes |
| "easier to read" | fewer words per meme text, or a `bloque` caption segment |
| "it drags" | `ritmo` ramp x2–x3 over the slow part, or cut tighter |
| "highlight that moment" | slow-mo x0.5 with `tono: "sigue"` + punch 1.3 with shake |
| "more professional" | FEWER overlays, `focus` on zooms, one well-placed effect |
| "change the color" | `accent` in the plan |
| "no music" / "add music" | they win — regenerate the delivery accordingly |
| "different moment" / "clip X is boring" | go back to the transcript, pick a replacement |

## Commands reference

```bash
# Analyze a VOD (once per video, cached)
python3 scripts/analyze_vod.py "<vod>"

# Cut a moment to a vertical clip
python3 scripts/cut_clip.py "<vod>" 1:32:10 1:32:48 "<out>/clip.mp4" [--focus-x 40] [--mode blur]

# Preview render (default; transcribes on first run)
bash scripts/render.sh "clip.mp4"
NOMBRE=myshort bash scripts/render.sh "c1.mp4" "c2.mp4"   # joined, named

# Contact sheet of every beat (~2 s, check placements without watching)
bash scripts/extract_stills.sh "clip.mp4"

# Validate a plan without rendering (~50 ms — run before every render)
python3 scripts/lint_plan.py "clip.plan.json" "clip.mp4" --words <workdir>/words.json --workdir <workdir>

# Translate times between source and final timeline (when using ritmo/velocidad)
python3 scripts/tiempo.py --workdir <workdir> --tabla

# Final quality
QUALITY=final bash scripts/render.sh "clip.mp4"

# Audio library / generation
node scripts/audio_library.js [term] [--type sfx|music|voice]
node scripts/elevenlabs_audio.js --type sfx --prompt "..." --out x.mp3 --dur 1
```

Environment variables: `QUALITY` (preview|final), `CAPTIONS` (1|0),
`LANGUAGE` (default `en`), `MODELO` (Whisper model for clip transcription),
`NOMBRE` (project name), `FORCE_RENDER=1`.

## Reference files

- `knowledge/hard_rules.md` — the hard rules, with the why of each
- `knowledge/editing_choices.md` — **which situation calls for which tool**:
  ramps, voice, captions, camera, transitions, doses, combos. Read before
  writing plans.
- `knowledge/style.md` — the comedy register: pacing, tone, what to avoid
- `knowledge/templates.md` — every template in detail, full JSON schemas
