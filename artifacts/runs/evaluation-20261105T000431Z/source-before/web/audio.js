/* Web Audio backend: original unsigned 8-bit DMX effects and MUS scores.
 * Music uses a small oscillator/noise synth, not an OPL/GENMIDI emulator.
 * AudioContext is created/resumed only from a user gesture. */
(() => {
  function parseMUS(bytes) {
    const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
    if (bytes.length < 16 || String.fromCharCode(...bytes.slice(0, 4)) !== 'MUS\x1a') throw new Error('Invalid MUS header');
    let pos = view.getUint16(6, true), time = 0;
    const end = pos + view.getUint16(4, true), events = [], velocity = Array(16).fill(100);
    if (pos < 16 || end > bytes.length) throw new Error('Truncated MUS score');
    const read = () => { if (pos >= end) throw new Error('Truncated MUS event'); return bytes[pos++]; };
    while (pos < end) {
      const descriptor = read(), channel = descriptor & 15, type = (descriptor >> 4) & 7;
      const event = {time: time / 140, channel, type};
      if (type === 6) return {events, duration: Math.max(time / 140, 0.1)};
      if (type === 0) event.note = read() & 127;
      else if (type === 1) {
        const note = read(); event.note = note & 127;
        if (note & 128) velocity[channel] = read() & 127;
        event.velocity = velocity[channel];
      } else if (type === 2) event.bend = (read() - 128) / 64;
      else if (type === 3) event.control = read();
      else if (type === 4) { event.control = read(); event.value = Math.min(read(), 127); }
      else throw new Error('Unsupported MUS event');
      events.push(event);
      if (descriptor & 128) {
        let delta = 0, b, count = 0;
        do { b = read(); delta = delta * 128 + (b & 127); if (++count > 5) throw new Error('Invalid MUS delay'); } while (b & 128);
        time += delta;
      }
    }
    throw new Error('MUS score missing end marker');
  }
  const A = window.DoomAudio = {
    context: null, muted: false, volume: 0.7, musicLevel: 0.6,
    effects: new Map(), buffers: new Map(), scores: new Map(), nextId: 1,
    voices: new Map(), song: null, timer: null, stats: {effects: 0, notes: 0, effectNames: {}},
    async unlock() {
      if (!this.context) {
        const Context = window.AudioContext || window.webkitAudioContext;
        if (!Context) throw new Error('Web Audio is unavailable');
        const c = this.context = new Context();
        this.master = c.createGain(); this.master.gain.value = this.muted ? 0 : this.volume;
        this.outputMeter = c.createAnalyser(); this.outputMeter.fftSize = 2048;
        this.master.connect(this.outputMeter); this.outputMeter.connect(c.destination);
        this.sfxMeter = c.createAnalyser(); this.sfxMeter.connect(this.master);
        this.musicBus = c.createGain(); this.musicBus.gain.value = this.musicLevel * 0.25;
        this.musicMeter = c.createAnalyser(); this.musicBus.connect(this.musicMeter); this.musicMeter.connect(this.master);
        this.noise = c.createBuffer(1, c.sampleRate, c.sampleRate);
        let seed = 17; const samples = this.noise.getChannelData(0);
        for (let i=0;i<samples.length;i++) { seed = (Math.imul(seed,1664525)+1013904223) >>> 0; samples[i] = seed/2147483648-1; }
        if (this.song) this.song.base = c.currentTime + 0.05;
      }
      await this.context.resume();
      if (!this.timer) this.timer = setInterval(() => this.pump(), 25);
      this.pump(); this.updateUI();
    },
    updateUI() {
      const button = document.getElementById('sound');
      if (button) { button.textContent = !this.context ? 'Enable sound' : this.muted ? 'Unmute' : 'Mute'; button.setAttribute('aria-pressed', String(this.muted)); }
    },
    setMuted(value) { this.muted = value; if (this.master) this.master.gain.setValueAtTime(value ? 0 : this.volume, this.context.currentTime); this.updateUI(); },
    setVolume(value) { this.volume = Math.max(0, Math.min(1, value)); if (this.master) this.master.gain.setValueAtTime(this.muted ? 0 : this.volume, this.context.currentTime); },
    musicVolume(value) { this.musicLevel = value; if (this.musicBus) this.musicBus.gain.setValueAtTime(value * 0.25, this.context.currentTime); },
    stop(channel) {
      const sound = this.effects.get(channel); if (!sound) return;
      sound.source.stop(); sound.source.disconnect(); sound.gain.disconnect(); sound.pan.disconnect(); this.effects.delete(channel);
    },
    stopAll() { for (const channel of this.effects.keys()) this.stop(channel); this.stopMusic(); },
    playing(channel) { return this.effects.has(channel); },
    params(channel, volume, separation) {
      const sound = this.effects.get(channel); if (!sound) return;
      sound.gain.gain.setValueAtTime(volume / 127, this.context.currentTime);
      sound.pan.pan.setValueAtTime((separation - 127) / 127, this.context.currentTime);
    },
    effect(channel, volume, separation, lump, bytes, name) {
      if (!this.context || this.context.state !== 'running') return -1;
      const c = this.context;
      let buffer = this.buffers.get(lump);
      if (!buffer) {
        if (bytes.length < 40 || bytes[0] !== 3 || bytes[1] !== 0) return -1;
        const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
        const rate = view.getUint16(2, true), length = view.getUint32(4, true);
        if (rate < 3000 || rate > 96000 || length <= 32 || length > bytes.length - 8) return -1;
        // DMX includes 16 padding samples at each end.
        buffer = c.createBuffer(1, length - 32, rate);
        const pcm = buffer.getChannelData(0);
        for (let i=0;i<pcm.length;i++) pcm[i] = (bytes[24+i]-128)/128;
        this.buffers.set(lump, buffer);
      }
      this.stop(channel);
      const source = c.createBufferSource(), gain = c.createGain(), pan = c.createStereoPanner();
      source.buffer = buffer; source.connect(gain); gain.connect(pan); pan.connect(this.sfxMeter);
      this.effects.set(channel, {source, gain, pan}); this.params(channel, volume, separation);
      source.onended = () => {
        if (this.effects.get(channel)?.source === source) this.effects.delete(channel);
        source.disconnect(); gain.disconnect(); pan.disconnect();
      };
      source.start(); this.stats.effects++; this.stats.effectNames[name] = (this.stats.effectNames[name] || 0) + 1;
      return channel;
    },
    register(bytes) { const id = this.nextId++; this.scores.set(id, parseMUS(bytes)); return id; },
    unregister(id) { if (this.song?.id === id) this.stopMusic(); this.scores.delete(id); },
    release(key, when) {
      const voice = this.voices.get(key); if (!voice) return;
      voice.gain.gain.cancelScheduledValues(when);
      voice.gain.gain.setTargetAtTime(0, when, 0.015); voice.source.stop(when + 0.08);
      this.voices.delete(key);
    },
    clearVoices() { for (const key of this.voices.keys()) this.release(key, this.context.currentTime); },
    stopMusic() { if (this.context) this.clearVoices(); this.song = null; },
    playMusic(id, looping) {
      this.stopMusic(); const score = this.scores.get(id); if (!score) return;
      this.channels = Array.from({length:16}, () => ({program:0, volume:1, pan:0, bend:0}));
      this.song = {id, score, looping, index:0, base:(this.context?.currentTime || 0)+0.05, paused:false}; this.pump();
    },
    pauseMusic() {
      if (!this.song || this.song.paused) return;
      this.song.paused = true; this.song.pausedAt = this.context?.currentTime || 0;
      if (this.context) this.clearVoices();
    },
    resumeMusic() {
      if (!this.song?.paused) return;
      this.song.base += (this.context?.currentTime || 0) - this.song.pausedAt; this.song.paused = false;
    },
    note(event, when) {
      const c = this.context, channel = this.channels[event.channel], key = `${event.channel}:${event.note}`;
      this.release(key, when);
      if (!event.velocity) return;
      if (this.voices.size >= 64) this.release(this.voices.keys().next().value, when);
      const drum = event.channel === 15;
      const source = drum ? c.createBufferSource() : c.createOscillator();
      if (drum) { source.buffer = this.noise; source.playbackRate.value = 0.5 + event.note / 100; }
      else {
        source.type = ['triangle','sine','sawtooth','square'][Math.floor(channel.program/8)%4];
        source.frequency.value = 440 * Math.pow(2, (event.note-69)/12);
        source.detune.setValueAtTime(channel.bend*100, when);
      }
      const gain = c.createGain(), pan = c.createStereoPanner();
      gain.gain.setValueAtTime(0, when); gain.gain.linearRampToValueAtTime(event.velocity/127*channel.volume*0.18, when+0.005);
      pan.pan.value = channel.pan;
      source.connect(gain); gain.connect(pan); pan.connect(this.musicBus);
      const voice = {source, gain, pan, channel:event.channel, velocity:event.velocity};
      this.voices.set(key, voice);
      source.onended = () => { if (this.voices.get(key) === voice) this.voices.delete(key); source.disconnect(); gain.disconnect(); pan.disconnect(); };
      source.start(when);
      if (drum) { gain.gain.setTargetAtTime(0, when+0.01, 0.035); source.stop(when+0.22); }
      this.stats.notes++;
    },
    event(event, when) {
      const channel = this.channels[event.channel];
      if (event.type === 0) this.release(`${event.channel}:${event.note}`, when);
      else if (event.type === 1) this.note(event, when);
      else if (event.type === 2) {
        channel.bend = event.bend;
        for (const voice of this.voices.values()) if (voice.channel === event.channel && voice.source.detune) voice.source.detune.setValueAtTime(event.bend*100, when);
      } else if (event.type === 3 && (event.control === 10 || event.control === 11)) {
        for (const [key,voice] of this.voices) if (voice.channel === event.channel) this.release(key, when);
      } else if (event.type === 4) {
        if (event.control === 0) channel.program = event.value;
        if (event.control === 3) channel.volume = event.value/127;
        if (event.control === 4) channel.pan = (event.value-64)/64;
        for (const voice of this.voices.values()) if (voice.channel === event.channel) {
          if (event.control === 3) voice.gain.gain.setValueAtTime(voice.velocity/127*channel.volume*0.18, when);
          if (event.control === 4) voice.pan.pan.setValueAtTime(channel.pan, when);
        }
      }
    },
    pump() {
      const s = this.song, c = this.context;
      if (!s || s.paused || !c || c.state !== 'running') return;
      // A backgrounded tab may miss its scheduling window; don't burst all old notes.
      if (c.currentTime - s.base > s.score.duration + 1) { this.clearVoices(); s.index=0; s.base=c.currentTime+0.02; }
      const horizon = c.currentTime+0.08;
      while (s.index < s.score.events.length && s.base+s.score.events[s.index].time < horizon) {
        const e = s.score.events[s.index++]; this.event(e, Math.max(c.currentTime, s.base+e.time));
      }
      if (s.index === s.score.events.length && c.currentTime >= s.base+s.score.duration) {
        this.clearVoices();
        if (s.looping) { s.index=0; s.base += s.score.duration; }
        else this.song=null;
      }
    },
    rms(which='output') {
      const meter = {output:this.outputMeter, music:this.musicMeter, sfx:this.sfxMeter}[which];
      if (!meter) return 0;
      const samples = new Float32Array(meter.fftSize); meter.getFloatTimeDomainData(samples);
      return Math.sqrt(samples.reduce((sum,x) => sum+x*x,0)/samples.length);
    }
  };
})();
