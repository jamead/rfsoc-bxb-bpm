#!/usr/bin/env python3

import argparse
import numpy as np
import matplotlib.pyplot as plt

SAMPLES_PER_TURN = 240
KX_MM = 10.0

# All sample indices are zero-based.
BASELINE_START = 0
BASELINE_STOP = 100     # Exclusive: samples 0–99

SIGNAL_START = 110
SIGNAL_STOP = 151       # Exclusive: samples 110–150


def main():
    parser = argparse.ArgumentParser(
        description="Calculate TbT position noise from ADC columns A B C D."
    )
    parser.add_argument("filename", help="Input text file with four columns")
    args = parser.parse_args()

    data = np.loadtxt(args.filename, ndmin=2)

    if data.shape[1] != 4:
        raise ValueError("Expected four columns: A B C D.")

    if data.shape[0] % SAMPLES_PER_TURN:
        raise ValueError("Sample count must be a multiple of 240.")

    if not np.isfinite(data).all():
        raise ValueError("Input contains invalid numeric values.")

    # Shape: turns × samples per turn × channels.
    turns = data.reshape(-1, SAMPLES_PER_TURN, 4)
    nturns = len(turns)

    if nturns < 3:
        raise ValueError("At least three turns are required.")

    # Subtract a separate baseline for each turn and channel.
    baseline = turns[:, BASELINE_START:BASELINE_STOP, :].mean(
        axis=1, keepdims=True
    )
    corrected = turns - baseline

    # Root-sum-square amplitude over samples 110–150 inclusive.
    pulse = corrected[:, SIGNAL_START:SIGNAL_STOP, :]
    amplitudes = np.sqrt(np.sum(pulse**2, axis=1))
    a, b, c, d = amplitudes.T

    total = a + b + c + d
    if np.any(total <= 0):
        raise ValueError("One or more turns have zero total amplitude.")

    # Horizontal position. No channel gain correction.
    x_mm = KX_MM * ((a + d) - (b + c)) / total
    x_um = x_mm * 1000.0
    deviation_um = x_um - x_um.mean()

    # Standard deviation about the mean, with no detrending.
    noise_um = np.std(x_um, ddof=1)
    adjacent_noise_um = np.std(np.diff(x_um), ddof=1) / np.sqrt(2)

    print(f"File:                   {args.filename}")
    print(f"Turns:                  {nturns}")
    print(
        f"Baseline window:        "
        f"{BASELINE_START}–{BASELINE_STOP - 1} inclusive"
    )
    print(
        f"RSS window:             "
        f"{SIGNAL_START}–{SIGNAL_STOP - 1} inclusive"
    )
    print(f"Kx:                     {KX_MM:.1f} mm")
    print(f"Mean X:                 {x_mm.mean():.6f} mm")
    print(f"TbT position RMS:       {noise_um:.3f} um")
    print(f"Adjacent difference/√2: {adjacent_noise_um:.3f} um")
    print(f"Peak-to-peak X:          {np.ptp(x_um):.3f} um")

    turn_number = np.arange(1, nturns + 1)
    sample_index = np.arange(SAMPLES_PER_TURN)

    fig, axes = plt.subplots(
        3, 1, figsize=(11, 10), layout="constrained"
    )

    # Top: mean baseline-subtracted ADC waveform.
    mean_waveform = corrected.mean(axis=0)

    for channel, label in enumerate("ABCD"):
        axes[0].plot(
            sample_index,
            mean_waveform[:, channel],
            label=label,
        )

    axes[0].axvspan(
        SIGNAL_START,
        SIGNAL_STOP - 1,
        color="gray",
        alpha=0.15,
        label="RSS window",
    )
    axes[0].set(
        xlim=(90, 190),
        xlabel="Sample within turn (zero-based)",
        ylabel="ADC counts",
        title=f"Mean baseline-subtracted waveforms — {nturns} turns",
    )
    axes[0].legend(ncol=5)

    # Middle: turn-by-turn position relative to its mean.
    axes[1].plot(turn_number, deviation_um, linewidth=0.8)
    axes[1].set(
        xlabel="Turn",
        ylabel="X − mean (µm)",
        title=(
            f"TbT position — RMS = {noise_um:.2f} µm, "
            f"Kx = {KX_MM:g} mm"
        ),
    )

    # Bottom: position distribution.
    axes[2].hist(deviation_um, bins=40, edgecolor="white")
    axes[2].set(
        xlabel="X − mean (µm)",
        ylabel="Turns",
        title=(
            f"RSS window: samples {SIGNAL_START}–"
            f"{SIGNAL_STOP - 1} inclusive"
        ),
    )

    for ax in axes:
        ax.grid(alpha=0.25)

    plt.show()


if __name__ == "__main__":
    main()
