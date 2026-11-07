"use client";

/**
 * Procedural ambience - every sound is synthesised live with Web Audio, so there
 * are no audio files and nothing copyrighted. Muted by default; the user opts in.
 */

type Stop = () => void;

class Ambience {
  private ctx: AudioContext | null = null;
  private master: GainNode | null = null;
  private current: { preset: string; out: GainNode; stop: Stop } | null = null;
  private volume = 0.35;

  private ensure() {
    if (!this.ctx) {
      const Ctx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      this.ctx = new Ctx();
      this.master = this.ctx.createGain();
      this.master.gain.value = this.volume;
      this.master.connect(this.ctx.destination);
    }
    if (this.ctx.state === "suspended") this.ctx.resume();
    return this.ctx;
  }

  setVolume(v: number) {
    this.volume = v;
    if (this.master && this.ctx) this.master.gain.setTargetAtTime(v, this.ctx.currentTime, 0.2);
  }

  play(preset: string) {
    if (this.current?.preset === preset) return;
    const ctx = this.ensure();
    this.fadeOutCurrent();
    if (preset === "none") return;
    const out = ctx.createGain();
    out.gain.value = 0;
    out.connect(this.master!);
    const stop = build(ctx, preset, out);
    out.gain.setTargetAtTime(1, ctx.currentTime, 0.8); // crossfade in
    this.current = { preset, out, stop };
  }

  stop() {
    this.fadeOutCurrent();
  }

  private fadeOutCurrent() {
    const cur = this.current;
    if (!cur || !this.ctx) return;
    cur.out.gain.setTargetAtTime(0, this.ctx.currentTime, 0.5);
    setTimeout(() => {
      cur.stop();
      cur.out.disconnect();
    }, 2500);
    this.current = null;
  }
}

function noiseBuffer(ctx: AudioContext, kind: "white" | "pink" | "brown") {
  const len = ctx.sampleRate * 3;
  const buf = ctx.createBuffer(1, len, ctx.sampleRate);
  const d = buf.getChannelData(0);
  let last = 0, b0 = 0, b1 = 0, b2 = 0;
  for (let i = 0; i < len; i++) {
    const w = Math.random() * 2 - 1;
    if (kind === "white") d[i] = w * 0.5;
    else if (kind === "brown") { last = (last + 0.02 * w) / 1.02; d[i] = last * 3.2; }
    else { b0 = 0.997 * b0 + w * 0.029; b1 = 0.985 * b1 + w * 0.032; b2 = 0.95 * b2 + w * 0.048; d[i] = (b0 + b1 + b2 + w * 0.02) * 0.9; }
  }
  return buf;
}

function noise(ctx: AudioContext, kind: "white" | "pink" | "brown") {
  const src = ctx.createBufferSource();
  src.buffer = noiseBuffer(ctx, kind);
  src.loop = true;
  src.start();
  return src;
}

function lfo(ctx: AudioContext, rate: number, depth: number, target: AudioParam) {
  const o = ctx.createOscillator();
  const g = ctx.createGain();
  o.frequency.value = rate;
  g.gain.value = depth;
  o.connect(g).connect(target);
  o.start();
  return o;
}

function filter(ctx: AudioContext, type: BiquadFilterType, freq: number, q = 0.7) {
  const f = ctx.createBiquadFilter();
  f.type = type;
  f.frequency.value = freq;
  f.Q.value = q;
  return f;
}

function tone(ctx: AudioContext, freq: number, type: OscillatorType, gain: number, out: AudioNode) {
  const o = ctx.createOscillator();
  const g = ctx.createGain();
  o.type = type;
  o.frequency.value = freq;
  g.gain.value = gain;
  o.connect(g).connect(out);
  o.start();
  return o;
}

// random one-shot events (drips, chirps, plinks, crackles)
function sprinkle(ctx: AudioContext, out: AudioNode, everyMs: [number, number], fire: (t: number) => void): Stop {
  let alive = true;
  const tick = () => {
    if (!alive) return;
    fire(ctx.currentTime);
    setTimeout(tick, everyMs[0] + Math.random() * (everyMs[1] - everyMs[0]));
  };
  setTimeout(tick, 400);
  return () => (alive = false);
}

function blip(ctx: AudioContext, out: AudioNode, t: number, freq: number, dur: number, vol: number, type: OscillatorType = "sine") {
  const o = ctx.createOscillator();
  const g = ctx.createGain();
  o.type = type;
  o.frequency.setValueAtTime(freq, t);
  g.gain.setValueAtTime(0, t);
  g.gain.linearRampToValueAtTime(vol, t + 0.01);
  g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
  o.connect(g).connect(out);
  o.start(t);
  o.stop(t + dur + 0.05);
}

function build(ctx: AudioContext, preset: string, out: GainNode): Stop {
  const nodes: (AudioScheduledSourceNode)[] = [];
  const stops: Stop[] = [];
  const bus = ctx.createGain();
  bus.connect(out);

  switch (preset) {
    case "desert_wind": {
      const n = noise(ctx, "pink"); const bp = filter(ctx, "bandpass", 500, 0.9); const g = ctx.createGain(); g.gain.value = 0.5;
      n.connect(bp).connect(g).connect(bus);
      nodes.push(n, lfo(ctx, 0.07, 350, bp.frequency), lfo(ctx, 0.11, 0.25, g.gain));
      break;
    }
    case "deep_ocean": {
      const n = noise(ctx, "brown"); const lp = filter(ctx, "lowpass", 320); const g = ctx.createGain(); g.gain.value = 0.55;
      n.connect(lp).connect(g).connect(bus);
      nodes.push(n, lfo(ctx, 0.09, 0.35, g.gain), lfo(ctx, 0.05, 150, lp.frequency), tone(ctx, 41, "sine", 0.12, bus));
      break;
    }
    case "space_hum": {
      const lp = filter(ctx, "lowpass", 600); lp.connect(bus);
      nodes.push(tone(ctx, 55, "sawtooth", 0.05, lp), tone(ctx, 55.6, "sawtooth", 0.05, lp), tone(ctx, 110.3, "sine", 0.05, lp));
      nodes.push(lfo(ctx, 0.04, 300, lp.frequency));
      break;
    }
    case "rain": {
      const n = noise(ctx, "white"); const hp = filter(ctx, "highpass", 900); const lp = filter(ctx, "lowpass", 7000); const g = ctx.createGain(); g.gain.value = 0.35;
      n.connect(hp).connect(lp).connect(g).connect(bus);
      nodes.push(n);
      break;
    }
    case "forest": {
      const n = noise(ctx, "pink"); const lp = filter(ctx, "lowpass", 1200); const g = ctx.createGain(); g.gain.value = 0.25;
      n.connect(lp).connect(g).connect(bus); nodes.push(n);
      stops.push(sprinkle(ctx, bus, [900, 3500], (t) => { const f = 2200 + Math.random() * 1800; blip(ctx, bus, t, f, 0.12, 0.05); blip(ctx, bus, t + 0.14, f * 1.1, 0.1, 0.04); }));
      break;
    }
    case "ember_crackle": {
      const n = noise(ctx, "brown"); const lp = filter(ctx, "lowpass", 250); const g = ctx.createGain(); g.gain.value = 0.5;
      n.connect(lp).connect(g).connect(bus); nodes.push(n);
      stops.push(sprinkle(ctx, bus, [60, 400], (t) => blip(ctx, bus, t, 800 + Math.random() * 2400, 0.02, 0.06, "square")));
      break;
    }
    case "city_night": {
      const n = noise(ctx, "brown"); const bp = filter(ctx, "bandpass", 180, 0.6); n.connect(bp).connect(bus); nodes.push(n);
      nodes.push(tone(ctx, 60, "sine", 0.04, bus));
      stops.push(sprinkle(ctx, bus, [4000, 9000], (t) => blip(ctx, bus, t, 440 + Math.random() * 200, 1.2, 0.02, "triangle")));
      break;
    }
    case "cavern": {
      const n = noise(ctx, "brown"); const lp = filter(ctx, "lowpass", 200); n.connect(lp).connect(bus); nodes.push(n);
      const dl = ctx.createDelay(1); dl.delayTime.value = 0.38; const fb = ctx.createGain(); fb.gain.value = 0.45;
      dl.connect(fb).connect(dl); dl.connect(bus);
      stops.push(sprinkle(ctx, dl, [1500, 4000], (t) => blip(ctx, dl, t, 1400 + Math.random() * 900, 0.08, 0.08)));
      break;
    }
    case "heartbeat": {
      const lp = filter(ctx, "lowpass", 400); lp.connect(bus);
      nodes.push(tone(ctx, 49, "sine", 0.05, lp));
      stops.push(sprinkle(ctx, lp, [950, 1050], (t) => { blip(ctx, lp, t, 55, 0.18, 0.5); blip(ctx, lp, t + 0.24, 50, 0.2, 0.35); }));
      break;
    }
    case "music_box": {
      const scale = [523.25, 587.33, 659.25, 783.99, 880, 1046.5];
      stops.push(sprinkle(ctx, bus, [350, 900], (t) => blip(ctx, bus, t, scale[Math.floor(Math.random() * scale.length)], 1.1, 0.07, "triangle")));
      break;
    }
    case "stadium": {
      const n = noise(ctx, "pink"); const bp = filter(ctx, "bandpass", 700, 0.5); const g = ctx.createGain(); g.gain.value = 0.3;
      n.connect(bp).connect(g).connect(bus); nodes.push(n, lfo(ctx, 0.06, 0.18, g.gain));
      break;
    }
    case "lounge": {
      // soft maj7 pad that breathes, plus the odd brushed-cymbal hiss
      const lp = filter(ctx, "lowpass", 900); const g = ctx.createGain(); g.gain.value = 0.5; lp.connect(g).connect(bus);
      [146.83, 185, 220, 277.18].forEach((f, i) => nodes.push(tone(ctx, f * (1 + i * 0.0015), "triangle", 0.025, lp)));
      nodes.push(lfo(ctx, 0.08, 0.2, g.gain), lfo(ctx, 0.03, 300, lp.frequency));
      const n = noise(ctx, "white"); const hp = filter(ctx, "highpass", 6000); const ng = ctx.createGain(); ng.gain.value = 0.015;
      n.connect(hp).connect(ng).connect(bus); nodes.push(n, lfo(ctx, 0.5, 0.012, ng.gain));
      break;
    }
    case "temple_bells": {
      // low drone + far-off bell strikes (inharmonic partials make it read as metal)
      const lp = filter(ctx, "lowpass", 300); lp.connect(bus);
      nodes.push(tone(ctx, 65.4, "sine", 0.05, lp), tone(ctx, 98, "sine", 0.03, lp));
      stops.push(sprinkle(ctx, bus, [3500, 8000], (t) => {
        const f = [392, 440, 523.25][Math.floor(Math.random() * 3)];
        [1, 2.76, 5.4].forEach((p, i) => blip(ctx, bus, t, f * p, 3.2 - i, 0.05 / (i + 1)));
      }));
      break;
    }
  }
  return () => {
    stops.forEach((s) => s());
    nodes.forEach((n) => { try { n.stop(); } catch { /* already stopped */ } });
    bus.disconnect();
  };
}

export const ambience = typeof window !== "undefined" ? new Ambience() : (null as unknown as Ambience);
