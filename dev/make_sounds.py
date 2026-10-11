"""Synthesize original end-of-timer chimes (bell partials + sparkle) as 16-bit WAVs."""
import wave
from pathlib import Path

import numpy as np

RATE = 44100
OUT = Path(__file__).resolve().parent / "sound_samples"


def bell(freq, dur=0.9, vol=0.5, decay=4.5):
    t = np.arange(int(RATE * dur)) / RATE
    # inharmonic-ish partials give a glockenspiel / bell color
    partials = ((1.0, 1.0), (2.0, 0.45), (3.01, 0.22), (4.17, 0.12), (5.43, 0.06))
    tone = sum(a * np.sin(2 * np.pi * freq * m * t) * np.exp(-t * decay * m ** 0.6) for m, a in partials)
    attack = np.minimum(1, t / 0.004)
    return vol * tone * attack


def sparkle(start, count=10, seed=3):
    rng = np.random.default_rng(seed)
    out = []
    for i in range(count):
        f = rng.uniform(2600, 4200)
        out.append((start + i * 0.035 + rng.uniform(0, 0.02), bell(f, dur=0.25, vol=0.07, decay=18)))
    return out


def mix(events, length):
    buf = np.zeros(int(RATE * length))
    for at, sig in events:
        i = int(at * RATE)
        n = min(len(sig), len(buf) - i)
        buf[i:i + n] += sig[:n]
    peak = np.max(np.abs(buf)) or 1
    return buf / peak * 0.85


def save(name, buf):
    OUT.mkdir(exist_ok=True)
    with wave.open(str(OUT / name), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes((buf * 32767).astype("<i2").tobytes())
    print("wrote", OUT / name)


note = lambda n: 440 * 2 ** ((n - 69) / 12)  # MIDI number -> Hz

# A: bright rising arpeggio that lands on a shimmering chord ("level up" feel)
a = [(i * 0.09, bell(note(n), 1.1, 0.5)) for i, n in enumerate((84, 88, 91, 96))]
a += [(0.38, bell(note(n), 1.6, 0.35, 2.8)) for n in (84, 88, 91, 96)] + sparkle(0.42)
save("A_level_up.wav", mix(a, 2.2))

# B: two quick high dings, like picking up a coin
b = [(0.0, bell(note(93), 0.6, 0.6, 7)), (0.11, bell(note(100), 0.9, 0.6, 5))] + sparkle(0.16, 6, seed=7)
save("B_coin.wav", mix(b, 1.2))

# C: warm three-chord "quest complete" cadence
c = []
for i, chord in enumerate(((72, 76, 79), (74, 79, 83), (76, 79, 84, 88))):
    dur = 1.6 if i == 2 else 0.5
    c += [(i * 0.22, bell(note(n), dur, 0.32, 3.2 if i == 2 else 6)) for n in chord]
c += sparkle(0.5, 8, seed=11)
save("C_quest_done.wav", mix(c, 2.3))
