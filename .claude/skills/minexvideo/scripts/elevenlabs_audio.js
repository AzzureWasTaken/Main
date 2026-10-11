#!/usr/bin/env node
// Generate audio with ElevenLabs (sound effects, music, character voices)
// and REGISTER it in the skill's audio library (assets/audio/INDEX.json)
// so it can be found and reused later.
//
//   node elevenlabs_audio.js --type sfx   --prompt "..." --out hit.mp3 --dur 1.0
//   node elevenlabs_audio.js --type music --prompt "..." --out theme.mp3 --dur 35
//   node elevenlabs_audio.js --type voice --text "..."  --out line.mp3 --voice <id>
//
// Common flags:
//   --desc "..."     human-readable description (so it can be found later)
//   --tags "a,b,c"   search tags
//   --force          regenerate even if the file already exists
//   --ephemeral      do not register in the library (single-video use)
//
// If the file already exists it does NOT regenerate: it returns the path and
// spends no credits. Reads ELEVENLABS_API_KEY from the environment or from
// the skill's api-keys.env file.

const fs = require('fs');
const path = require('path');

const SKILL_DIR = path.resolve(__dirname, '..');
const LIB_DIR = process.env.AUDIO_LIB_DIR || path.join(SKILL_DIR, 'assets', 'audio');
const INDEX_FILE = path.join(LIB_DIR, 'INDEX.json');
const KEY_FILE = path.join(SKILL_DIR, 'api-keys.env');
const SUBDIR = { sfx: 'sfx', music: 'music', voice: 'voices' };

function loadKey() {
    if (process.env.ELEVENLABS_API_KEY) return process.env.ELEVENLABS_API_KEY;
    try {
        const m = fs.readFileSync(KEY_FILE, 'utf-8').match(/^ELEVENLABS_API_KEY=(.+)$/m);
        if (m) return m[1].trim();
    } catch { /* fall through */ }
    console.error(`ERROR: ELEVENLABS_API_KEY not found (environment or ${KEY_FILE})`);
    process.exit(1);
}

function parseArgs(argv) {
    const a = { type: null, prompt: null, text: null, out: null, dur: null,
                voice: 'JBFqnCBsd6RMkjVDRZzb', desc: null, tags: [],
                force: false, ephemeral: false, influence: 0.45 };
    for (let i = 2; i < argv.length; i++) {
        const k = argv[i], next = () => argv[++i];
        if (k === '--type') a.type = next();
        else if (k === '--prompt') a.prompt = next();
        else if (k === '--text') a.text = next();
        else if (k === '--out') a.out = next();
        else if (k === '--dur') a.dur = parseFloat(next());
        else if (k === '--voice') a.voice = next();
        else if (k === '--desc') a.desc = next();
        else if (k === '--tags') a.tags = next().split(',').map(s => s.trim()).filter(Boolean);
        else if (k === '--influence') a.influence = parseFloat(next());
        else if (k === '--force') a.force = true;
        else if (k === '--ephemeral') a.ephemeral = true;
        else { console.error(`Unknown argument: ${k}`); process.exit(1); }
    }
    if (!SUBDIR[a.type]) { console.error('ERROR: --type must be sfx | music | voice'); process.exit(1); }
    if (a.type === 'voice' && !a.text) { console.error('ERROR: --text is required for --type voice'); process.exit(1); }
    if (a.type !== 'voice' && !a.prompt) { console.error('ERROR: --prompt is required'); process.exit(1); }
    if (!a.out) { console.error('ERROR: --out is required (e.g. hit.mp3)'); process.exit(1); }
    if (!/\.mp3$/i.test(a.out)) a.out += '.mp3';

    const hasFolder = a.out.includes('/') || a.out.includes('\\');
    a.outPath = (!hasFolder && !a.ephemeral)
        ? path.join(LIB_DIR, SUBDIR[a.type], a.out)
        : path.resolve(a.out);
    a.name = path.basename(a.outPath);
    return a;
}

const readIndex = () => { try { return JSON.parse(fs.readFileSync(INDEX_FILE, 'utf-8')); } catch { return []; } };

function register(a, dur) {
    fs.mkdirSync(LIB_DIR, { recursive: true });
    const index = readIndex().filter(e => !(e.file === a.name && e.type === a.type));
    index.push({
        file: a.name,
        type: a.type,
        path: `${SUBDIR[a.type]}/${a.name}`,
        desc: a.desc || (a.prompt || a.text).slice(0, 90),
        tags: a.tags,
        prompt: a.prompt || undefined,
        text: a.text || undefined,
        voice: a.type === 'voice' ? a.voice : undefined,
        duration: dur,
        date: new Date().toISOString().slice(0, 10)
    });
    index.sort((x, y) => (x.type + x.file).localeCompare(y.type + y.file));
    fs.writeFileSync(INDEX_FILE, JSON.stringify(index, null, 2));
}

function durationOf(file) {
    try {
        const { execFileSync } = require('child_process');
        const out = execFileSync('ffprobe', ['-v', 'error', '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1', file], { encoding: 'utf-8' });
        return Math.round(parseFloat(out.trim()) * 100) / 100;
    } catch { return null; }
}

async function main() {
    const key = loadKey();
    const a = parseArgs(process.argv);

    if (fs.existsSync(a.outPath) && !a.force) {
        console.log(JSON.stringify({
            audioPath: a.outPath, reused: true,
            duration: durationOf(a.outPath),
            note: 'Already existed — not regenerated (use --force to redo it).'
        }, null, 2));
        return;
    }

    let url, body;
    if (a.type === 'sfx') {
        url = 'https://api.elevenlabs.io/v1/sound-generation';
        body = { text: a.prompt, prompt_influence: a.influence };
        if (a.dur) body.duration_seconds = Math.min(Math.max(a.dur, 0.5), 22);
    } else if (a.type === 'music') {
        url = 'https://api.elevenlabs.io/v1/music';
        body = { prompt: a.prompt, music_length_ms: Math.round((a.dur || 20) * 1000) };
    } else {
        url = `https://api.elevenlabs.io/v1/text-to-speech/${a.voice}`;
        body = { text: a.text, model_id: 'eleven_multilingual_v2' };
    }

    const r = await fetch(url, {
        method: 'POST',
        headers: { 'xi-api-key': key, 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
    });
    if (!r.ok) {
        console.error(`ERROR ${r.status}: ${(await r.text()).slice(0, 400)}`);
        process.exit(1);
    }
    fs.mkdirSync(path.dirname(a.outPath), { recursive: true });
    fs.writeFileSync(a.outPath, Buffer.from(await r.arrayBuffer()));

    const dur = durationOf(a.outPath);
    if (!a.ephemeral) register(a, dur);

    console.log(JSON.stringify({
        audioPath: a.outPath, type: a.type, duration: dur,
        inLibrary: !a.ephemeral
    }, null, 2));
}

main().catch(e => { console.error('FATAL:', e.message); process.exit(1); });
