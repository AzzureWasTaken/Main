#!/usr/bin/env node
// Catalog of the audio already in the skill's library (generated with
// ElevenLabs or shipped with the skill).
// ALWAYS check it before calling elevenlabs_audio.js: if something usable
// already exists, reuse it and spend no credits.
//
//   node audio_library.js                → full catalog
//   node audio_library.js impact        → filter by term
//   node audio_library.js --type sfx    → sound effects only

const fs = require('fs');
const path = require('path');

const SKILL_DIR = path.resolve(__dirname, '..');
const LIB_DIR = process.env.AUDIO_LIB_DIR || path.join(SKILL_DIR, 'assets', 'audio');
const INDEX_FILE = path.join(LIB_DIR, 'INDEX.json');

let index = [];
try { index = JSON.parse(fs.readFileSync(INDEX_FILE, 'utf-8')); } catch { /* empty */ }

const args = process.argv.slice(2);
let typeFilter = null;
const terms = [];
for (let i = 0; i < args.length; i++) {
    if (args[i] === '--type') typeFilter = args[++i];
    else terms.push(args[i].toLowerCase());
}

if (!index.length) {
    console.log('The audio library is empty. Generate with:');
    console.log('  node scripts/elevenlabs_audio.js --type sfx --prompt "..." --out name.mp3 --dur 1.5 --desc "..." --tags "a,b"');
    process.exit(0);
}

const match = e => (!typeFilter || e.type === typeFilter) && (!terms.length || terms.some(t =>
    e.file.toLowerCase().includes(t) ||
    (e.desc || '').toLowerCase().includes(t) ||
    (e.tags || []).some(g => g.toLowerCase().includes(t))));

const hits = index.filter(match);
if (!hits.length) {
    console.log(`No results${terms.length ? ` for "${terms.join(' ')}"` : ''}${typeFilter ? ` (type ${typeFilter})` : ''} — ${index.length} sounds in the library.`);
    console.log('If something new is truly needed, generate it; otherwise reuse something similar.');
    process.exit(0);
}

const ICON = { sfx: '🔊', music: '🎵', voice: '🗣️' };
console.log(`${hits.length} of ${index.length} sounds:\n`);
for (const type of ['sfx', 'music', 'voice']) {
    const group = hits.filter(e => e.type === type);
    if (!group.length) continue;
    console.log(`── ${ICON[type]} ${type.toUpperCase()} ──`);
    for (const e of group) {
        const missing = fs.existsSync(path.join(LIB_DIR, e.path)) ? '' : '  [FILE MISSING]';
        console.log(`  ${e.file}${missing}   (${e.duration != null ? e.duration + 's' : '?'})`);
        console.log(`     ${e.desc}`);
        console.log(`     tags: ${(e.tags || []).join(', ') || '—'}  |  ${e.date}`);
    }
    console.log('');
}
console.log('In a short\'s plan the file name alone is enough — render.sh finds it.');
