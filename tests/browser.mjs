// No npm dependencies. Node 22's WebSocket talks to Chrome's DevTools protocol.
// Tests the built dist/ through HTTP; never calls dg_key directly.
import { spawn, execFileSync } from 'node:child_process';
import { createServer } from 'node:http';
import { readFileSync, writeFileSync, mkdirSync, mkdtempSync, rmSync, existsSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import assert from 'node:assert/strict';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const fault = process.env.DOOM_TEST_FAULT || '';
assert(['', 'ignore-input', 'blank-canvas', 'silent-effects'].includes(fault), 'Unknown DOOM_TEST_FAULT');
const output = join(root, 'artifacts', 'runs', `browser-${new Date().toISOString().replaceAll(':', '-')}-${process.pid}`);
mkdirSync(output, {recursive: true});
const report = { status: 'FAIL', fault, started: new Date().toISOString(), checks: [], console: [], errors: [], requests: [] };
const hash = data => createHash('sha256').update(data).digest('hex');
const git = args => execFileSync('git', args, {cwd: root, encoding: 'utf8'});
report.revision = git(['rev-parse', 'HEAD']).trim();
report.workingTree = git(['status', '--short']);
report.hashes = {};
for (const file of ['build.sh', 'platform/doomgeneric_wasm.c', 'platform/doom_audio.c', 'platform/SDL_mixer.h', 'web/audio.js', 'dist/audio.js', 'web/index.html', 'tests/test_browser.py', 'tests/test_audio.py', 'tests/browser.mjs', 'assets/doom1.wad', 'dist/doom.js', 'dist/doom.wasm', 'dist/doom.data', 'dist/index.html']) {
    report.hashes[file] = existsSync(join(root, file)) ? hash(readFileSync(join(root, file))) : null;
}
writeFileSync(join(output, 'source.patch'), git(['diff', '--', 'platform', 'web']));
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
let browser, socket, server, profile, evaluate;
let chromeLog = '';
const check = (name, detail = {}) => { report.checks.push({name, ...detail}); console.log(`PASS ${name}`); };
try {
    for (const f of ['doom.js', 'doom.wasm', 'doom.data', 'index.html', 'audio.js'])
        assert(existsSync(join(root, 'dist', f)), `Missing dist/${f}; run bash build.sh first`);
    assert.equal(report.hashes['web/index.html'], report.hashes['dist/index.html'], 'dist/index.html is stale; rebuild');
    assert.equal(report.hashes['web/audio.js'], report.hashes['dist/audio.js'], 'dist/audio.js is stale; rebuild');
    server = createServer((req, res) => {
        const file = new URL(req.url, 'http://localhost').pathname.slice(1) || 'index.html';
        if (file === 'favicon.ico') { res.writeHead(204); res.end(); return; }
        if (!['index.html', 'doom.js', 'doom.wasm', 'doom.data', 'audio.js'].includes(file)) { res.writeHead(404); res.end(); return; }
        res.setHeader('Content-Type', {'index.html':'text/html', 'doom.js':'text/javascript', 'audio.js':'text/javascript', 'doom.wasm':'application/wasm', 'doom.data':'application/octet-stream'}[file]);
        res.end(readFileSync(join(root, 'dist', file)));
    });
    await new Promise((resolve, reject) => { server.once('error', reject); server.listen(0, '127.0.0.1', resolve); });
    const url = `http://127.0.0.1:${server.address().port}/`;
    const chrome = process.env.CHROME_BIN || ['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '/usr/bin/google-chrome', '/usr/bin/chromium', '/usr/bin/chromium-browser'].find(existsSync);
    assert(chrome, 'Chrome not found; set CHROME_BIN');
    profile = mkdtempSync(join(tmpdir(), 'doom-browser-'));
    browser = spawn(chrome, ['--headless=new', '--remote-debugging-port=0', `--user-data-dir=${profile}`, '--no-first-run', '--no-default-browser-check', '--disable-background-timer-throttling', '--disable-renderer-backgrounding', '--window-size=900,700', 'about:blank'], {stdio:['ignore','ignore','pipe']});
    browser.on('error', e => { chromeLog += e.stack; });
    browser.stderr.on('data', data => { chromeLog += data; });
    const deadline = Date.now() + 15000;
    while (!existsSync(join(profile, 'DevToolsActivePort'))) {
        assert(Date.now() < deadline, `Chrome startup failed: ${chromeLog}`);
        await delay(100);
    }
    const port = readFileSync(join(profile, 'DevToolsActivePort'), 'utf8').split('\n')[0];
    const targets = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
    socket = new WebSocket(targets.find(t => t.type === 'page').webSocketDebuggerUrl);
    await new Promise((resolve, reject) => { socket.onopen = resolve; socket.onerror = reject; });
    let serial = 0;
    const pending = new Map();
    socket.onmessage = ({data}) => {
        const event = JSON.parse(data);
        if (event.id) {
            const waiter = pending.get(event.id);
            if (!waiter) return;
            pending.delete(event.id);
            clearTimeout(waiter.timer);
            event.error ? waiter.reject(new Error(JSON.stringify(event.error))) : waiter.resolve(event.result);
        } else if (event.method === 'Runtime.exceptionThrown') {
            report.errors.push(event.params.exceptionDetails);
        } else if (event.method === 'Runtime.consoleAPICalled') {
            report.console.push({type: event.params.type, args: event.params.args.map(a => a.value ?? a.description)});
            if (event.params.type === 'error') report.errors.push(event.params);
        } else if (event.method === 'Network.loadingFailed') report.errors.push(event.params);
        else if (event.method === 'Network.responseReceived') {
            report.requests.push({url: event.params.response.url, status: event.params.response.status});
            if (event.params.response.status >= 400) report.errors.push(event.params.response);
        }
    };
    const cdp = (method, params = {}) => new Promise((resolve, reject) => {
        const id = ++serial;
        const timer = setTimeout(() => { pending.delete(id); reject(new Error(`CDP timeout: ${method}`)); }, 10000);
        pending.set(id, {resolve, reject, timer});
        socket.send(JSON.stringify({id, method, params}));
    });
    evaluate = async expression => {
        const result = await cdp('Runtime.evaluate', {expression, returnByValue: true});
        assert(!result.exceptionDetails, JSON.stringify(result.exceptionDetails));
        return result.result.value;
    };
    const until = async (expression, message, timeout = 10000) => {
        const deadline = Date.now() + timeout;
        while (!await evaluate(expression)) {
            assert(Date.now() < deadline, message);
            await delay(100);
        }
    };
    const screenshot = async name => {
        const result = await cdp('Page.captureScreenshot', {format: 'png'});
        writeFileSync(join(output, `${name}.png`), Buffer.from(result.data, 'base64'));
    };
    await cdp('Runtime.enable'); await cdp('Page.enable'); await cdp('Network.enable');
    report.browser = await cdp('Browser.getVersion');
    if (fault) await cdp('Page.addScriptToEvaluateOnNewDocument', {source: fault === 'ignore-input'
        ? "window.addEventListener('keydown', e => e.stopImmediatePropagation(), true);"
        : fault === 'silent-effects' ? 'AudioBufferSourceNode.prototype.connect = function(target) { return target; };' : 'CanvasRenderingContext2D.prototype.putImageData = function() {};'});
    await cdp('Page.navigate', {url});
    await until('typeof Module !== "undefined" && !!Module._dg_game_tics && Module._dg_frame_count() > 2', 'Engine never started; rebuild to include diagnostics', 20000);
    assert(report.console.some(line => line.args.some(arg => String(arg).includes('adding /doom1.wad'))), 'No WAD load reported');
    for (const file of ['doom.js', 'doom.wasm', 'doom.data'])
        assert(report.requests.some(r => r.url.endsWith(`/${file}`) && r.status === 200), `${file} did not load`);
    const canvas = await evaluate(`(() => { const c = Module.canvas; const p = c.getContext('2d').getImageData(0,0,c.width,c.height).data; let lit=0; for(let i=0;i<p.length;i+=4) if(p[i]+p[i+1]+p[i+2]>30 && p[i+3]) lit++; return {width:c.width,height:c.height,lit}; })()`);
    assert.equal(canvas.width, 640); assert.equal(canvas.height, 400);
    assert(canvas.lit > 1000, 'Canvas is blank');
    check('WAD and WebAssembly load; canvas contains rendered pixels', canvas);
    await screenshot('boot');
    const key = async (code, type) => {
        const keys = {Escape:['Escape',27], Enter:['Enter',13], ArrowUp:['ArrowUp',38], ArrowRight:['ArrowRight',39], ControlLeft:['Control',17], ControlRight:['Control',17], Space:[' ',32], KeyW:['w',87], KeyS:['s',83], KeyA:['a',65], KeyD:['d',68], ShiftLeft:['Shift',16], ShiftRight:['Shift',16], Tab:['Tab',9], Digit1:['1',49], Digit2:['2',50], KeyP:['p',80]};
        const [value, vk] = keys[code];
        await cdp('Input.dispatchKeyEvent', {type, key:value, code, windowsVirtualKeyCode:vk, nativeVirtualKeyCode:vk});
    };
    const tap = async code => { await key(code,'keyDown'); await delay(100); await key(code,'keyUp'); await delay(250); };
    const click = async (selector, fraction=0.5) => {
        const point = await evaluate(`(() => {const r=document.querySelector(${JSON.stringify(selector)}).getBoundingClientRect(); return {x:r.x+r.width*${fraction},y:r.y+r.height/2};})()`);
        await cdp('Input.dispatchMouseEvent', {type:'mousePressed',button:'left',clickCount:1,...point});
        await cdp('Input.dispatchMouseEvent', {type:'mouseReleased',button:'left',clickCount:1,...point});
        await delay(150);
    };
    assert.equal(await evaluate('DoomAudio.context'), null, 'Audio started without a user gesture');
    await click('#sound');
    await until('DoomAudio.context?.state === "running"', 'Sound button failed to unlock AudioContext');
    check('Enable sound button unlocks audio through a real user gesture');
    await click('#canvas');
    await tap('Escape');
    await until('!!Module._dg_menu_active()', 'Escape did not open the menu');
    await screenshot('menu');
    // Default main menu -> New Game -> episode one -> default difficulty.
    await tap('Enter'); await tap('Enter'); await tap('Enter');
    await until('!!Module._dg_in_level() && !Module._dg_menu_active()', 'Keyboard failed to start a playable level');
    await delay(1500); // Allow the initial screen wipe to finish.
    check('Real keyboard events open menu and start a new game');
    await screenshot('level');
    const sample = () => evaluate('({time:performance.now(), frames:Module._dg_frame_count(), tics:Module._dg_game_tics()})');
    const before = await sample(); await delay(3000); const after = await sample();
    const rate = (after.tics-before.tics)*1000/(after.time-before.time);
    assert(after.frames > before.frames + 10, 'Rendering stopped');
    assert(rate > 28 && rate < 42, `Simulation speed ${rate.toFixed(2)} tics/s, expected ~35`);
    check('Continuous rendering and simulation pacing', {before, after, ticsPerSecond:rate});
    const position = () => evaluate('[Module._dg_player_x(),Module._dg_player_y()]');
    const start = await position();
    const pixelsBefore = await evaluate('Module.canvas.toDataURL()');
    await key('ArrowUp','keyDown'); await delay(650); await key('ArrowUp','keyUp'); await delay(300);
    const moved = await position();
    assert(Math.hypot(moved[0]-start[0],moved[1]-start[1]) > 65536, 'Movement key did not move the player');
    assert.notEqual(await evaluate('Module.canvas.toDataURL()'), pixelsBefore, 'Canvas did not update after movement');
    check('Movement changes world position and rendered view', {start, moved});
    const angle = await evaluate('Module._dg_player_angle()');
    await key('ArrowRight','keyDown'); await delay(300); await key('ArrowRight','keyUp');
    assert.notEqual(await evaluate('Module._dg_player_angle()'), angle, 'Turn key had no effect');
    check('Turning changes player angle');
    const ammo = await evaluate('Module._dg_bullets()');
    await key('ControlLeft','keyDown'); await delay(1000); await key('ControlLeft','keyUp');
    const remaining = await evaluate('Module._dg_bullets()');
    assert(remaining < ammo, 'Fire key did not consume ammunition');
    check('Firing consumes ammunition', {before:ammo, after:remaining});
    await key('ControlLeft','keyDown');
    await until('DoomAudio.rms("sfx") > 0.001', 'No sound-effect waveform while firing');
    const effectRMS = await evaluate('DoomAudio.rms("sfx")');
    await key('ControlLeft','keyUp');
    assert(await evaluate('(DoomAudio.stats.effectNames.pistol || 0) > 0'), 'Pistol sound never requested');
    check('Pistol sound produces a nonzero audio waveform', {rms:effectRMS});
    await until('DoomAudio.rms("music") > 0.0001', 'Music produces no waveform');
    check('WAD music score produces a nonzero audio waveform', {rms:await evaluate('DoomAudio.rms("music")')});
    await click('#sound'); await delay(200);
    assert(await evaluate('DoomAudio.muted'), 'Mute button failed');
    assert(await evaluate('DoomAudio.rms() < 0.00001'), 'Muted output is not silent');
    await click('#sound');
    await until('DoomAudio.rms() > 0.0001', 'Unmute failed to restore audio');
    await click('#volume', 0.01); await delay(200);
    assert.equal(await evaluate('DoomAudio.volume'), 0, 'Volume slider did not reach zero');
    assert(await evaluate('DoomAudio.rms() < 0.00001'), 'Zero-volume output is not silent');
    await click('#volume', 0.7);
    await until('DoomAudio.rms() > 0.0001', 'Volume slider failed to restore audio');
    check('Mute, unmute and volume controls affect actual output samples');
    await click('#canvas');
    await key('Space','keyDown');
    await until('!!Module._dg_use_down()', 'Use key did not reach engine');
    await key('Space','keyUp');
    await until('!Module._dg_use_down()', 'Use key remained held after release');
    check('Use press and release reach the game simulation');
    await key('ArrowRight','keyDown'); await delay(200);
    // CDP browser focus emulation sends an actual blur event to this page.
    await cdp('Emulation.setFocusEmulationEnabled', {enabled:true});
    await cdp('Emulation.setFocusEmulationEnabled', {enabled:false});
    // Headless Chrome does not consistently change OS focus. Explicitly dispatch
    // blur to test the application's release handler, not OS focus integration.
    await evaluate('window.dispatchEvent(new Event("blur"))');
    await delay(300);
    const stoppedAngle = await evaluate('Module._dg_player_angle()');
    await delay(600);
    assert.equal(await evaluate('Module._dg_player_angle()'), stoppedAngle, 'Held turn key stayed active after blur');
    await key('ArrowRight','keyUp');
    check('Blur handler releases a held turn key (synthetic blur)');
    await key('KeyW','keyDown'); await delay(200);
    const walking = await evaluate('Module._dg_forward()'); assert(walking > 0, 'W does not move forward');
    await key('ShiftLeft','keyDown'); await key('ShiftRight','keyDown'); await delay(200);
    assert(await evaluate('Module._dg_forward()') > walking, 'Shift does not run');
    await key('ShiftLeft','keyUp'); await delay(200);
    assert(await evaluate('Module._dg_forward()') > walking, 'Releasing left Shift cancelled held right Shift');
    await key('ShiftRight','keyUp'); await key('KeyW','keyUp');
    await key('KeyS','keyDown'); await delay(200);
    assert(await evaluate('Module._dg_forward()') < 0, 'S does not move backward');
    await key('KeyS','keyUp');
    for (const [code,sign] of [['KeyA',-1],['KeyD',1]]) {
        await key(code,'keyDown'); await delay(200);
        assert((await evaluate('Module._dg_side()'))*sign > 0, `${code} does not strafe`);
        await key(code,'keyUp');
    }
    check('W/S movement, A/D strafing and overlapping Shift run keys');
    await tap('Digit1'); await until('Module._dg_weapon() === 0', 'Weapon 1 did not select fists');
    await tap('Digit2'); await until('Module._dg_weapon() === 1', 'Weapon 2 did not select pistol');
    await tap('Tab'); assert(await evaluate('!!Module._dg_automap()'), 'Tab failed to open map');
    await tap('Tab'); assert(!await evaluate('!!Module._dg_automap()'), 'Tab failed to close map');
    check('Weapon selection and automap toggle');
    await click('#menu'); await until('!!Module._dg_menu_active()', 'Menu button failed');
    await click('#menu'); await until('!Module._dg_menu_active()', 'Menu button failed to close menu');
    await click('#pause'); await until('!!Module._dg_paused()', 'Pause button failed');
    await delay(250);
    assert(await evaluate('DoomAudio.rms("music") < 0.00001'), 'Music did not pause');
    await click('#pause'); await until('!Module._dg_paused()', 'Resume button failed');
    await until('DoomAudio.rms("music") > 0.0001', 'Music did not resume');
    await tap('KeyP'); await until('!!Module._dg_paused()', 'P shortcut failed');
    await tap('KeyP'); await until('!Module._dg_paused()', 'P resume shortcut failed');
    check('Menu and pause/resume buttons, P shortcut, music pause/resume');
    await screenshot('after-input');
    assert.equal(report.errors.length, 0, `Runtime/network errors: ${JSON.stringify(report.errors)}`);
    check('No uncaught page errors, console errors or failed network requests');
    report.status = 'PASS';
} catch (error) {
    report.failure = error.stack;
    console.error(error.stack);
    process.exitCode = 1;
} finally {
    report.finished = new Date().toISOString();
    report.limitations = ['Audio checks measure the Web Audio graph, not physical speakers or musical fidelity. Music uses simplified instruments, not OPL emulation.', 'Does not verify mouse aiming or save persistence.', 'Use checks engine input state, not successful door/switch interaction.', 'Focus-loss check dispatches synthetic blur; OS focus transitions are not verified.', 'Timing tolerance is 28–42 simulation tics/s over three seconds.', 'No claim of enforced role permissions or full assignment acceptance.'];
    writeFileSync(join(output, 'results.json'), JSON.stringify(report, null, 2));
    socket?.close();
    if (browser && browser.exitCode === null) {
        const exited = new Promise(resolve => browser.once('exit', resolve));
        browser.kill();
        await Promise.race([exited, delay(2000)]);
        if (browser.exitCode === null) browser.kill('SIGKILL');
    }
    server?.closeAllConnections(); server?.close();
    writeFileSync(join(output, 'chrome.log'), chromeLog);
    if (profile) rmSync(profile, {recursive:true, force:true, maxRetries:3});
    console.log(`${report.status}: ${output}`);
}
