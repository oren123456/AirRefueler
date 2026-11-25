"""Procedural cockpit audio for the Mirage refuelling sim (48 kHz mono 16-bit).
Loops are built from periodic (FFT) noise / integer-cycle tones so they wrap seamlessly.
  A_ECS        air-conditioning hiss (loudest steady layer)
  A_Air        canopy airflow rush (scaled by IAS)
  A_Engine     M53 heard through the helmet: low rumble + faint turbine whine (pitch/volume by spool)
  A_Breath     oxygen-mask breathing: demand-valve click, inhale hiss, exhale puff (4 varied breaths)
  A_Wake       tanker wake: lumpy low buffet + airframe creaks (scaled by proximity)
  A_RadioHiss  faint open-mic radio hiss bed (gated with calls)
  S_Contact    probe seating: dull low thunk + muffled latch clank
  S_Disconnect probe pulling free: soft pop + clunk
  V_*          tanker calls: TTS -> radio band-pass, compression, grit, squelch clicks + hiss tail
argv[1] = folder with raw TTS wavs (cleared_contact/contact/disconnect)."""
import numpy as np, sys, os
from scipy import signal
from scipy.io import wavfile
SR = 48000
rng = np.random.default_rng(11)
OUT = sys.argv[2] if len(sys.argv) > 2 else "/tmp/aud/out"; os.makedirs(OUT, exist_ok=True)

def pnoise(sec, shape, seed):
    """periodic noise with magnitude spectrum shape(f) -> seamless loop"""
    n = int(sec * SR); f = np.fft.rfftfreq(n, 1 / SR); r = np.random.default_rng(seed)
    mag = shape(np.maximum(f, 1.0)); mag[0] = 0
    x = np.fft.irfft(mag * np.exp(2j * np.pi * r.random(len(f))), n)
    return x / np.sqrt(np.mean(x ** 2))
def plfo(sec, hz, seed, depth):
    """slow periodic random modulation (band-limited noise up to hz)"""
    n = int(sec * SR); k = max(2, int(hz * sec)); r = np.random.default_rng(seed)
    spec = np.zeros(n // 2 + 1, complex); spec[1:k + 1] = np.exp(2j * np.pi * r.random(k)) / np.arange(1, k + 1) ** 0.5
    x = np.fft.irfft(spec, n); x /= np.max(np.abs(x)) + 1e-9
    return 1.0 + depth * x
def tone(sec, hz, phase=0.0):
    n = int(sec * SR); cyc = round(hz * sec)          # integer cycles -> periodic
    return np.sin(2 * np.pi * cyc * np.arange(n) / n + phase)
def bp(lo, hi, order=2):
    return lambda f: 1.0 / np.sqrt(1 + (lo / f) ** (2 * order)) / np.sqrt(1 + (f / hi) ** (2 * order))
def save(name, x, peak=0.5):
    x = x / (np.max(np.abs(x)) + 1e-9) * peak
    wavfile.write(os.path.join(OUT, name + ".wav"), SR, (x * 32767).astype(np.int16)); print(name, len(x) / SR, "s")
def rms_norm(x, r): return x / np.sqrt(np.mean(x ** 2)) * r

# ---------- ECS hiss: pinkish, bump at 1.5-4 kHz, gentle flutter
T = 10.0
ecs = pnoise(T, lambda f: f ** -0.35 * bp(150, 9000)(f) * (1 + 1.2 * np.exp(-((np.log(f / 2500)) ** 2) / 0.5)), 1)
ecs *= plfo(T, 0.6, 2, 0.04)
save("A_ECS", ecs, 0.5)
# ---------- canopy airflow: brownish rumble + mid rush, gusty
T = 12.0
air = 0.8 * pnoise(T, lambda f: f ** -1.0 * bp(40, 700)(f), 3) + 0.45 * pnoise(T, lambda f: f ** -0.5 * bp(400, 3500)(f), 4)
air *= plfo(T, 0.8, 5, 0.18)
save("A_Air", air, 0.5)
# ---------- engine through the helmet: low rumble, combustion roar, faint turbine whine with slow beating
T = 8.0
rumble = pnoise(T, lambda f: bp(25, 160, 3)(f), 6)
roar = pnoise(T, lambda f: f ** -0.5 * bp(180, 900)(f), 7)
hum = tone(T, 47.0) * 0.5 + tone(T, 94.0, 1.0) * 0.25
whine = (tone(T, 2860.0) + 0.8 * tone(T, 2861.5, 0.7)) * 0.5 * plfo(T, 0.5, 8, 0.25) + 0.35 * tone(T, 5722.0, 0.3)
eng = 1.0 * rumble + 0.35 * roar + 0.18 * hum + 0.035 * whine
save("A_Engine", eng, 0.5)
# ---------- breathing through the mask regulator: 4 breaths, varied lengths, seamless
cycles = [4.1, 3.7, 4.4, 3.8]; T = sum(cycles); n = int(T * SR)
br = np.zeros(n)
def env(n_, a, r):   # attack/release fractions
    t = np.linspace(0, 1, n_); return np.clip(t / a, 0, 1) * np.clip((1 - t) / r, 0, 1) ** 1.5
def click(hz, dec):
    m = int(0.02 * SR); t = np.arange(m) / SR
    return np.sin(2 * np.pi * hz * t) * np.exp(-t / dec) + 0.5 * rng.standard_normal(m) * np.exp(-t / (dec * 0.5))
inh_b = signal.butter(2, [900, 6000], "bandpass", fs=SR, output="sos")
exh_b = signal.butter(2, [250, 1800], "bandpass", fs=SR, output="sos")
t0 = 0.0
for i, c in enumerate(cycles):
    s = int(t0 * SR)
    li = int((1.15 + 0.15 * i % 2) * SR); le = int((1.35 + 0.1 * (i % 3)) * SR); gap = int(0.25 * SR)
    ni = signal.sosfilt(inh_b, rng.standard_normal(li + 2000))[2000:] * env(li, 0.12, 0.35)
    ne = signal.sosfilt(exh_b, rng.standard_normal(le + 2000))[2000:] * env(le, 0.08, 0.6)
    ne *= 1 + 0.25 * np.sin(2 * np.pi * 28 * np.arange(le) / SR) * np.exp(-np.arange(le) / (0.25 * SR))   # exhale valve flutter
    cl = click(3200, 0.002)
    seg = [(0, cl * 0.6), (int(0.01 * SR), ni * 0.55), (li + gap, ne * 0.42), (li + gap, click(1800, 0.003) * 0.35)]
    for off, x in seg:
        a = (s + off) % n; m = len(x)
        idx = (np.arange(m) + a) % n; br[idx] += x
    t0 += c
br += 0.02 * pnoise(T, bp(200, 4000), 9)
save("A_Breath", br, 0.5)
# ---------- tanker wake: lumpy low buffet + creaks
T = 10.0; n = int(T * SR)
base = pnoise(T, lambda f: bp(15, 90, 3)(f), 10) * plfo(T, 2.5, 11, 0.6)
thumps = np.zeros(n)
for k in range(22):
    a = int(rng.uniform(0, n)); m = int(0.35 * SR); t = np.arange(m) / SR
    hz = rng.uniform(28, 55); x = np.sin(2 * np.pi * hz * t) * np.exp(-t / rng.uniform(0.05, 0.12)) * rng.uniform(0.4, 1.0)
    thumps[(np.arange(m) + a) % n] += x
creak = np.zeros(n)
for k in range(5):
    a = int(rng.uniform(0, n)); m = int(rng.uniform(0.15, 0.4) * SR); t = np.arange(m) / SR
    f0 = rng.uniform(280, 520); ph = 2 * np.pi * np.cumsum(f0 * (1 + 0.15 * np.sin(2 * np.pi * 9 * t))) / SR
    x = np.sign(np.sin(ph)) * 0.5 + np.sin(ph); x = signal.sosfilt(signal.butter(2, [200, 1500], "bandpass", fs=SR, output="sos"), x)
    creak[(np.arange(m) + a) % n] += x * np.sin(np.pi * t / t[-1]) * 0.15
wake = 1.0 * base + 1.2 * thumps + creak
save("A_Wake", wake, 0.55)
# ---------- radio hiss bed
T = 6.0
rh = pnoise(T, bp(300, 3200, 3), 12) * plfo(T, 3, 13, 0.1)
save("A_RadioHiss", rh, 0.4)
# ---------- contact: dull low thunk + muffled latch clank
m = int(1.2 * SR); t = np.arange(m) / SR
f = 72 - 18 * (1 - np.exp(-t / 0.05)); thunk = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.11)
thud = signal.sosfilt(signal.butter(2, 380, "low", fs=SR, output="sos"), rng.standard_normal(m)) * np.exp(-t / 0.03) * 0.8
cl = np.zeros(m); d = int(0.045 * SR)
for hz, dec, a in ((1180, 0.07, 0.25), (2710, 0.05, 0.15), (4120, 0.03, 0.08), (640, 0.12, 0.2)):
    cl[d:] += a * np.sin(2 * np.pi * hz * t[:m - d]) * np.exp(-t[:m - d] / dec)
cl = signal.sosfilt(signal.butter(2, 3000, "low", fs=SR, output="sos"), cl)
contact = 1.0 * thunk + thud + 0.6 * cl
save("S_Contact", contact, 0.8)
# ---------- disconnect: soft pop + clunk
m = int(0.8 * SR); t = np.arange(m) / SR
pop = signal.sosfilt(signal.butter(2, [150, 1400], "bandpass", fs=SR, output="sos"), rng.standard_normal(m)) * np.exp(-t / 0.018)
clunk = np.sin(2 * np.pi * 95 * t) * np.exp(-t / 0.07) * 0.7
ring = 0.12 * np.sin(2 * np.pi * 1530 * t) * np.exp(-t / 0.06)
save("S_Disconnect", pop + clunk + ring, 0.7)
# ---------- radio calls
src = sys.argv[1] if len(sys.argv) > 1 else None
if src:
    vb = signal.butter(4, [320, 2900], "bandpass", fs=SR, output="sos")
    for name, lead in (("cleared_contact", 0.3), ("contact", 0.6), ("disconnect", 0.25)):
        sr0, v = wavfile.read(os.path.join(src, name + ".wav")); v = v.astype(np.float64) / 32768
        v = signal.resample_poly(v, SR, sr0)
        nz = np.nonzero(np.abs(v) > 0.01)[0]; v = v[max(0, nz[0] - 800):nz[-1] + 2400]
        v = signal.sosfilt(vb, v)
        v = np.tanh(v / (np.max(np.abs(v)) + 1e-9) * 3.0) * 0.8                      # hard AGC + grit
        v = v * (1 + 0.04 * np.sin(2 * np.pi * 120 * np.arange(len(v)) / SR))           # faint hum modulation
        hiss_len = len(v) + int(0.5 * SR)
        hs = signal.sosfilt(signal.butter(3, [400, 3500], "bandpass", fs=SR, output="sos"), rng.standard_normal(hiss_len))
        hs = hs / np.sqrt(np.mean(hs ** 2)) * 0.06
        out = np.zeros(int(lead * SR) + hiss_len + int(0.12 * SR))
        a = int(lead * SR)
        k_on = click(2500, 0.0015) * 0.5; out[a:a + len(k_on)] += k_on
        out[a + int(0.05 * SR):a + int(0.05 * SR) + len(v)] += v
        out[a:a + hiss_len] += hs * np.clip(np.arange(hiss_len) / (0.01 * SR), 0, 1)
        e = a + hiss_len; tail = int(0.12 * SR)                                         # squelch tail (burst of louder hiss)
        out[e - 400:e - 400 + tail] += signal.sosfilt(signal.butter(2, [800, 5000], "bandpass", fs=SR, output="sos"), rng.standard_normal(tail)) * np.exp(-np.arange(tail) / (0.035 * SR)) * 0.35
        save("V_" + name.title().replace("_", ""), out, 0.7)
