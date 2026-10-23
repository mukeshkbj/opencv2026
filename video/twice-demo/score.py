"""Music bed and sound-effect track for the 100 s cut.

Run with the earshot venv Python (numpy, scipy, soundfile, earshot CLI):
  C:/Users/mukes/tools/earshot/.venv/Scripts/python.exe score.py
Writes assets/audio/music.wav and assets/audio/sfx.wav.
"""
import os
import re
import subprocess
import tempfile

import numpy as np
import soundfile as sf
from scipy.signal import butter, fftconvolve, sosfilt

SR = 48000
LEN = 100.0
N = int(LEN * SR)
BEAT = 60 / 105
rng = np.random.default_rng(7)

GROOVE = 21.8
STAMP = 16.6
SHUTTER = 31.6
SLIDE = GROOVE + 36 * BEAT
STOP = 69.8
LIGHT = 71.6
END_HIT = 96.0

EARSHOT = "C:/Users/mukes/tools/earshot/.venv/Scripts/earshot.exe"


def hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def lp(x, f, order=2):
    return sosfilt(butter(order, f, "low", fs=SR, output="sos"), x)


def hp(x, f, order=2):
    return sosfilt(butter(order, f, "high", fs=SR, output="sos"), x)


def bp(x, lo, hi):
    return sosfilt(butter(2, [lo, hi], "band", fs=SR, output="sos"), x)


def saw(f, n, detune=0.0):
    t = np.arange(n) / SR
    out = np.zeros(n)
    for k in range(1, int(8000 / f)):
        out += np.sin(2 * np.pi * k * f * (1 + detune) * t) / k
    return out * 0.6


def env(n, a, d, s=0.0, r=0.0):
    t = np.arange(n) / SR
    e = np.where(t < a, t / max(a, 1e-4), s + (1 - s) * np.exp(-(t - a) / max(d, 1e-4)))
    if r:
        e *= np.clip((n / SR - t) / r, 0, 1)
    return e


def place(bus, x, at):
    i = int(round(at * SR))
    if i >= len(bus):
        return
    j = min(len(bus), i + len(x))
    bus[max(i, 0):j] += x[max(-i, 0):j - i]


def chord(at, dur, notes, level, cutoff):
    n = int(dur * SR)
    tone = sum(saw(hz(m), n, d) for m in notes for d in (-0.004, 0.004))
    tone = lp(tone, cutoff) * env(n, 0.35, 99, 1.0, 0.4)
    return tone * level / len(notes), at


def kick(level=1.0):
    n = int(0.42 * SR)
    t = np.arange(n) / SR
    f = 48 + 90 * np.exp(-t / 0.035)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.16)
    click = hp(rng.standard_normal(n), 2500) * np.exp(-t / 0.004) * 0.25
    return (body + click) * level


def hat(level, decay=0.035):
    n = int(0.12 * SR)
    return hp(rng.standard_normal(n), 7000) * np.exp(-np.arange(n) / SR / decay) * level


def clap(level):
    n = int(0.3 * SR)
    x = bp(rng.standard_normal(n), 900, 3500)
    t = np.arange(n) / SR
    e = sum(np.exp(-np.clip(t - o, 0, None) / 0.012) * (t >= o) for o in (0, 0.011, 0.022))
    return x * (e + np.exp(-t / 0.12) * 0.6 * (t >= 0.022)) * level


def pluck(m, level, decay=0.22):
    n = int(0.6 * SR)
    t = np.arange(n) / SR
    tone = np.sin(2 * np.pi * hz(m) * t) + 0.35 * np.sin(4 * np.pi * hz(m) * t)
    return tone * np.exp(-t / decay) * env(n, 0.003, 99, 1.0) * level


def bass(m, dur, level):
    n = int(dur * SR)
    return lp(saw(hz(m), n), 380) * env(n, 0.005, dur * 0.6, 0.0, 0.03) * level


def sub_pulse(level):
    n = int(0.5 * SR)
    t = np.arange(n) / SR
    f = 46 + 50 * np.exp(-t / 0.05)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.22) * level


def noise_riser(dur, level):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = rng.standard_normal(n)
    out = np.zeros(n)
    blocks = 40
    for b in range(blocks):
        s, e = b * n // blocks, (b + 1) * n // blocks
        c = 400 * (14 ** (b / blocks))
        out[s:e] = bp(x, c * 0.7, min(c * 1.4, 20000))[s:e]
    return out * (t / dur) ** 2.2 * level


def crash(level):
    n = int(2.2 * SR)
    return hp(rng.standard_normal(n), 4000) * np.exp(-np.arange(n) / SR / 0.7) * level


def reverb(x, secs=2.4, mix=0.28):
    n = int(secs * SR)
    out = []
    for _ in range(2):
        ir = lp(rng.standard_normal(n) * np.exp(-np.arange(n) / SR / (secs / 6.9)), 6000)
        wet = fftconvolve(x, ir)[: len(x)]
        wet *= np.sqrt(np.mean(x**2) + 1e-12) / np.sqrt(np.mean(wet**2) + 1e-12)
        out.append(x * (1 - mix) + wet * mix)
    return np.stack(out)



AM, F, C, G = (57, 60, 64), (53, 57, 60), (48, 55, 64), (55, 59, 62)
PROG = [AM, F, C, G]
ROOTS = [33, 29, 36, 31]


def compose():
    pads = np.zeros(N)
    drums = np.zeros(N)
    keys = np.zeros(N)
    low = np.zeros(N)

    n = int(STAMP * SR)
    drone = lp(saw(hz(33), n) + saw(hz(40), n, 0.003), 260)
    drone *= np.clip(np.arange(n) / SR / 2.0, 0, 1) * (0.8 + 0.2 * np.sin(2 * np.pi * 0.18 * np.arange(n) / SR))
    place(low, drone * 0.28, 0)
    t = 0.03
    while t < STAMP - 0.05:
        place(drums, sub_pulse(0.3 + 0.25 * t / STAMP), t)
        t += BEAT
    t = 6.6
    while t < STAMP - 0.05:
        place(drums, hat(0.05 + 0.06 * (t - 6.6) / 10, 0.02), t)
        t += BEAT / 2
    n = int((STAMP - 10.0) * SR)
    place(pads, lp(saw(hz(58), n, 0.002), 1200) * env(n, 4.0, 99, 1.0, 0.05) * 0.10, 10.0)

    n = int((GROOVE - STAMP) * SR)
    swell = lp(saw(hz(33), n) + saw(hz(45), n, 0.004), 320) * np.linspace(0.1, 0.35, n)
    place(low, swell, STAMP + 0.05)
    place(pads, noise_riser(GROOVE - STAMP - 1.8, 0.10), STAMP + 1.8)

    for bar in range(21):
        at = GROOVE + bar * 4 * BEAT
        notes = PROG[bar % 4]
        x, _ = chord(at, 4 * BEAT + 0.4, notes, 0.30, 1500 + 900 * (at > SLIDE))
        place(pads, x, at)
        for e in range(8):
            bt = at + e * BEAT / 2
            if bt >= STOP - 0.25:
                break
            place(low, bass(ROOTS[bar % 4], BEAT / 2, 0.42), bt)
        for s in range(16):
            st = at + s * BEAT / 4
            if st < GROOVE + 8 * BEAT or st >= STOP - 0.25:
                continue
            m = notes[[0, 1, 2, 1][s % 4]] + 12 * (s % 8 >= 4)
            place(keys, pluck(m, 0.11), st)
    for b in range(84):
        bt = GROOVE + b * BEAT
        if bt >= STOP - 0.2:
            break
        lifted = bt >= SLIDE - 0.01
        if SLIDE - 4 * BEAT - 0.01 <= bt < SLIDE - 0.01:
            continue
        if lifted or b % 2 == 0:
            place(drums, kick(0.9), bt)
        if lifted:
            place(drums, hat(0.13), bt + BEAT / 2)
            if b % 2 == 1:
                place(drums, clap(0.32), bt)
        elif b % 2 == 1:
            place(drums, hat(0.08), bt + BEAT / 2)
    place(pads, noise_riser(4 * BEAT, 0.22), SLIDE - 4 * BEAT)
    place(drums, crash(0.22), SLIDE)

    gate = np.ones(N)
    i0, i1 = int((STOP - 0.12) * SR), int(LIGHT * SR)
    gate[i0:i1] = 0.0
    gate[i0 - int(0.03 * SR):i0] = np.linspace(1, 0, int(0.03 * SR))

    for bar in range(int((END_HIT - LIGHT) / (4 * BEAT)) + 1):
        at = LIGHT + bar * 4 * BEAT
        if at >= END_HIT - 0.4:
            break
        notes = PROG[bar % 4]
        dur = min(4 * BEAT + 0.4, END_HIT - at)
        x, _ = chord(at, dur, notes, 0.24, 1100)
        place(pads, x, at)
        for s in range(8):
            st = at + s * BEAT / 2
            if st >= 93.4:
                break
            m = notes[[0, 2, 1, 2][s % 4]] + 12
            place(keys, pluck(m, 0.075, 0.3), st)
        if at >= 82.2 - 0.1 and at < 93.4:
            place(drums, kick(0.45), at)
            place(drums, kick(0.35), at + 2 * BEAT)
    place(pads, noise_riser(END_HIT - 93.4, 0.12), 93.4)

    n = int((LEN - END_HIT) * SR)
    final = sum(saw(hz(m), n, d) for m in (45, 52, 57, 59, 64) for d in (-0.003, 0.003))
    final = lp(final, 2400) * env(n, 0.01, 1.6, 0.35, 0.8) * 0.09
    place(pads, final, END_HIT)
    place(low, sub_pulse(0.9), END_HIT)
    place(low, lp(saw(hz(33), int(2.5 * SR)), 200) * env(int(2.5 * SR), 0.01, 0.9) * 0.4, END_HIT)
    place(drums, kick(1.0), END_HIT)
    place(drums, crash(0.18), END_HIT)

    keys = reverb(keys, 1.8, 0.3)
    keys[1] = np.roll(keys[1], int(0.014 * SR))
    mix = reverb(pads, 2.8, 0.45) + keys + drums + lp(low, 600)
    mix *= gate
    fade = int(0.6 * SR)
    mix[:, -fade:] *= np.linspace(1, 0, fade)
    return mix


def voice_bus():
    bus = np.zeros(N)
    html = open("index.html", encoding="utf-8").read()
    for src, start in re.findall(r'src="(assets/vo2/[^"]+)" data-start="([\d.]+)"', html):
        x, sr = sf.read(src)
        if x.ndim > 1:
            x = x.mean(axis=1)
        if sr != SR:
            idx = np.arange(int(len(x) * SR / sr)) * sr / SR
            x = np.interp(idx, np.arange(len(x)), x)
        place(bus, x, float(start))
    return bus


def duck(music, voice, depth_db=-9.0):
    win = int(0.05 * SR)
    rms = np.sqrt(np.convolve(voice**2, np.ones(win) / win, "same"))
    on = (rms > 0.01).astype(float)
    g = np.empty(N)
    target = 10 ** (depth_db / 20)
    a_up, a_dn = 1 / (0.35 * SR), 1 / (0.08 * SR)
    level = 1.0
    hold = 0
    for i in range(0, N, 48):
        want = target if on[i] else 1.0
        if on[i]:
            hold = int(0.3 * SR)
        elif hold > 0:
            want = target
            hold -= 48
        step = (a_dn if want < level else a_up) * 48
        level += np.clip(want - level, -step, step)
        g[i:i + 48] = level
    return music * g


def render_sfx(sound, out, **kw):
    args = [EARSHOT, "sfx", "render", sound, "-o", out]
    for k, v in kw.items():
        args += [f"--{k}", str(v)]
    subprocess.run(args, check=True, capture_output=True)
    x, sr = sf.read(out)
    return x.mean(axis=1) if x.ndim > 1 else x


CUES = [
    ("cut_hit/sub", 0.03, 0.021, 0.7, {}),
    ("pro_pop_in/knock", 1.4, 0.011, 0.35, {}),
    ("pro_pop_in/knock", 3.1, 0.011, 0.35, {}),
    *[("knock/wood", 6.6 + t, 0.015, 0.12, {}) for t in (1.0, 1.2, 1.4, 1.6)],
    ("cut_hit/punch", STAMP, 0.058, 0.95, {}),
    ("impact/punch", STAMP, 0.066, 0.55, {}),
    ("pro_whoosh_big/swell", GROOVE, 0.354, 0.35, {}),
    ("shutter/dslr", SHUTTER, 0.042, 0.6, {}),
    ("swish/soft", 35.6, 0.110, 0.2, {}),
    ("swish/flick", 40.6, 0.111, 0.25, {}),
    ("cut_hit/air", SLIDE, 0.043, 0.4, {}),
    ("swish/soft", 49.6, 0.110, 0.2, {}),
    ("click/soft", 50.47, 0.004, 0.2, {}),
    ("swish/soft", 58.6, 0.110, 0.2, {}),
    ("notify/mid_tine", 67.3, 0.038, 0.3, {}),
    ("glitch/hit", STOP, 0.252, 0.45, {}),
    ("cut_hit/sub", STOP, 0.021, 0.9, {}),
    ("cut_hit/punch", STOP, 0.058, 0.6, {}),
    ("pro_whoosh_big/tonal", LIGHT, 0.350, 0.25, {}),
    ("swish/soft", 82.2, 0.110, 0.2, {}),
    ("ui_pop/wide", 79.8, 0.044, 0.25, {}),
    ("ui_pop/wide", 83.8, 0.044, 0.28, {}),
    ("ui_pop/wide", 86.0, 0.044, 0.28, {}),
    ("ui_pop/wide", 87.9, 0.044, 0.32, {}),
    ("reverse_swell/cymbal", END_HIT, 0.518, 0.3, {}),
    ("impact/classic", END_HIT, 0.117, 0.6, {}),
]
CUES += [("typing_key/light", 66.2 + i * 0.056, 0.013, 0.08, {"seed": i}) for i in range(8)]
CUES += [("typing_key/light", 68.2 + i * 0.075, 0.013, 0.08, {"seed": 20 + i}) for i in range(12)]


def sfx_track():
    bus = np.zeros(N)
    with tempfile.TemporaryDirectory() as tmp:
        cache = {}
        for k, (sound, at, peak, level, kw) in enumerate(CUES):
            key = (sound, tuple(sorted(kw.items())))
            if key not in cache:
                cache[key] = render_sfx(sound, os.path.join(tmp, f"{k}.wav"), **kw)
            place(bus, cache[key] * level, at - peak)
    return bus


def write(path, x, peak_db):
    x = np.atleast_2d(x)
    x = x / (np.max(np.abs(x)) + 1e-12) * 10 ** (peak_db / 20)
    sf.write(path, np.repeat(x, 3 - len(x), axis=0).T, SR, subtype="PCM_24")


if __name__ == "__main__":
    os.makedirs("assets/audio", exist_ok=True)
    music = duck(compose(), voice_bus())
    write("assets/audio/music.wav", music, -9.0)
    write("assets/audio/sfx.wav", sfx_track(), -3.0)
    print("ok")
