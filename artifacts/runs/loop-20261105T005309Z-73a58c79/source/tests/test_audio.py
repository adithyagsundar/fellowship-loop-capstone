"""Validate every bundled MUS score and reject corrupt/truncated score data."""
from pathlib import Path
import subprocess
import unittest


class MusicData(unittest.TestCase):
    def test_bundled_scores_and_invalid_data(self):
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run(["node", "--input-type=module", "-e", r'''
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';
import assert from 'node:assert/strict';
const sandbox = {window:{}};
runInNewContext(readFileSync('web/audio.js','utf8'), sandbox);
const audio = sandbox.window.DoomAudio;
const wad = readFileSync('assets/doom1.wad');
const count = wad.readUInt32LE(4), directory = wad.readUInt32LE(8);
let scores = 0;
for (let i=0; i<count; i++) {
  const entry = directory+i*16, offset=wad.readUInt32LE(entry), length=wad.readUInt32LE(entry+4);
  const bytes=wad.subarray(offset,offset+length);
  if (bytes.subarray(0,4).toString('binary') !== 'MUS\x1a') continue;
  const id=audio.register(bytes), score=audio.scores.get(id);
  assert(score.duration>0 && score.events.some(e=>e.type===1 && e.velocity>0));
  assert(score.events.every((e,j)=>e.time>=0 && e.time<=score.duration && (!j || e.time>=score.events[j-1].time)));
  assert.throws(()=>audio.register(bytes.subarray(0,bytes.length-1)), /Truncated/);
  audio.unregister(id); assert(!audio.scores.has(id)); scores++;
}
assert.equal(scores,13,'Expected all 13 shareware music scores');
assert.throws(()=>audio.register(new Uint8Array(16)), /Invalid MUS header/);
assert.equal(audio.context,null,'Parsing must not start audio before user interaction');
console.log('Validated 13 MUS scores, truncation rejection and deferred audio initialization');
'''], cwd=root, capture_output=True, text=True, timeout=15)
        print(result.stdout, flush=True)
        self.assertEqual(result.returncode, 0, result.stderr)
