#!/usr/bin/env python3
"""Read Tektronix .wfm, simulate an ideal 117 MHz Gaussian LPF, and plot ±20 ns.

Install: pip install numpy matplotlib tm_data_types
Run:     python plot_wfm_117mhz.py single_bunch_4mA.wfm

The original waveform (including any preceding pulse) is preserved.
This is an ideal zero-phase Gaussian LPF, NOT a SPICE model of the RLC filter.
"""
import argparse
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt


def read_wfm(filename):
    try:
        from tm_data_types import read_file
    except ImportError as exc:
        raise SystemExit('Install Tektronix reader: pip install tm_data_types') from exc
    waveform = read_file(str(filename))
    t = np.asarray(waveform.normalized_horizontal_values, dtype=float)
    v = np.asarray(waveform.normalized_vertical_values, dtype=float)
    return t, v


def gaussian_lowpass(v, dt, cutoff_hz):
    """Gaussian frequency response, -3 dB at cutoff_hz; pad to limit wraparound."""
    n = len(v)
    # Zero-pad at both ends so the FFT's periodic boundary does not affect the pulse.
    pad = min(n // 2, max(1024, int(np.ceil(20e-9 / dt))))
    extended = np.pad(v, (pad, pad), mode='constant')
    nfft = 1 << (len(extended) - 1).bit_length()
    freq = np.fft.rfftfreq(nfft, dt)
    transfer = np.exp(-0.5 * np.log(2) * (freq / cutoff_hz)**2)
    filtered = np.fft.irfft(np.fft.rfft(extended, nfft) * transfer, nfft)
    return filtered[pad:pad + n]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('wfm', type=Path, help='Original Tektronix .wfm file')
    parser.add_argument('--cutoff-mhz', type=float, default=117)
    parser.add_argument('--window-ns', type=float, default=20,
                        help='Show +/- this many ns around the main peak')
    parser.add_argument('--output', type=Path, default=Path('single_bunch_117MHz.png'))
    args = parser.parse_args()

    t, v = read_wfm(args.wfm)
    if len(t) < 10 or not np.all(np.isfinite(t)) or not np.all(np.isfinite(v)):
        raise ValueError('Invalid waveform data')
    dt = float(np.median(np.diff(t)))
    if dt <= 0 or not np.allclose(np.diff(t), dt, rtol=1e-3, atol=1e-14):
        raise ValueError('Waveform must be uniformly sampled')

    # Remove DC baseline before filtering. Use outer 10% of full acquisition.
    edge = max(1, len(v) // 10)
    baseline = float(np.median(np.concatenate((v[:edge], v[-edge:]))))
    input_signal = v - baseline

    # Filter the FULL acquisition, then crop for plotting: avoids edge artifacts.
    filtered = gaussian_lowpass(input_signal, dt, args.cutoff_mhz * 1e6)
    peak_idx = int(np.argmax(np.abs(input_signal)))
    peak_t = t[peak_idx]
    relative_ns = (t - peak_t) * 1e9
    select = np.abs(relative_ns) <= args.window_ns

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 8), sharex=True)
    ax1.plot(relative_ns[select], input_signal[select], lw=1.3)
    ax1.set_title('Original Tektronix BPM waveform (baseline subtracted)')
    ax1.set_ylabel('Voltage (V)')
    ax1.grid(True, alpha=0.3)

    ax2.plot(relative_ns[select], filtered[select], lw=1.6)
    ax2.set_title(f'Ideal Gaussian low-pass filtered waveform ({args.cutoff_mhz:g} MHz, -3 dB)')
    ax2.set_xlabel('Time relative to main peak (ns)')
    ax2.set_ylabel('Voltage (V)')
    ax2.grid(True, alpha=0.3)
    for ax in (ax1, ax2):
        ax.axvline(0, color='gray', ls='--', alpha=0.7)
        ax.set_xlim(-args.window_ns, args.window_ns)

    fig.tight_layout()
    fig.savefig(args.output, dpi=180)
    plt.show()

    print(f'Samples: {len(v):,}, sampling rate: {1/dt/1e9:.3f} GS/s')
    print(f'Main peak: {input_signal[peak_idx]:.4f} V at t={peak_t*1e9:.4f} ns')
    print(f'Filtered range in plotted window: {filtered[select].min()*1e3:.2f} to '
          f'{filtered[select].max()*1e3:.2f} mV')
    print(f'Saved plot: {args.output}')


if __name__ == '__main__':
    main()
