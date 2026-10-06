#!/usr/bin/env python3

import argparse
import numpy as np
import matplotlib.pyplot as plt


def main():
    parser = argparse.ArgumentParser(
        description="Plot 4 RFDFE ADC waveform channels"
    )
    parser.add_argument("filename", help="Input waveform text file")
    args = parser.parse_args()

    # Skip the first line because it contains the PV names.
    # np.loadtxt handles tabs or spaces automatically.
    data = np.loadtxt(args.filename, comments="#")

    if data.ndim != 2 or data.shape[1] < 4:
        raise ValueError(
            f"Expected at least 4 columns, but found shape {data.shape}"
        )

    adc_a = data[:, 0]
    adc_b = data[:, 1]
    adc_c = data[:, 2]
    adc_d = data[:, 3]

    sample = np.arange(len(data))

    fig, axes = plt.subplots(
        4, 1,
        figsize=(12, 9),
        sharex=True
    )

    axes[0].plot(sample, adc_a)
    axes[0].set_ylabel("ADC A")
    axes[0].grid(True)

    axes[1].plot(sample, adc_b)
    axes[1].set_ylabel("ADC B")
    axes[1].grid(True)

    axes[2].plot(sample, adc_c)
    axes[2].set_ylabel("ADC C")
    axes[2].grid(True)

    axes[3].plot(sample, adc_d)
    axes[3].set_ylabel("ADC D")
    axes[3].set_xlabel("Sample")
    axes[3].grid(True)

    fig.suptitle("RFSoC ADC Waveforms")

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
