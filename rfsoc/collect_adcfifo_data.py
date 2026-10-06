#!/usr/bin/env python3

import os
import time
import argparse
from datetime import datetime

# Set before importing EPICS.
os.environ.setdefault("EPICS_CA_MAX_ARRAY_BYTES", "16777216")

import numpy as np
from epics import PV


def main():
    parser = argparse.ArgumentParser(
        description="Trigger RFDFE and save ADC A/B/C/D waveforms."
    )
    parser.add_argument(
        "filename",
        nargs="?",
        default=datetime.now().strftime("adc_%Y%m%d_%H%M%S.txt"),
    )
    parser.add_argument("--prefix", default="lab")
    parser.add_argument("--number", type=int, default=1)
    args = parser.parse_args()

    base = f"{args.prefix}{{RFDFE:{args.number}}}"
    trigger = PV(f"{base}Trig:Soft-SP", auto_monitor=False)

    names = [f"{base}ADC:{ch}:Buff-Wfm" for ch in "ABCD"]
    channels = [PV(name, auto_monitor=False) for name in names]

    # Connect before triggering.
    for pv in [trigger, *channels]:
        if not pv.wait_for_connection(timeout=10):
            raise RuntimeError(f"Cannot connect to {pv.pvname}")

    print(f"Triggering {trigger.pvname}")
    status = trigger.put(1, wait=True, timeout=10)
    if status != 1:
        raise RuntimeError("Trigger write failed or timed out")

    time.sleep(0.100)

    columns = []
    for pv in channels:
        values = pv.get(
            count=48000,
            as_numpy=True,
            use_monitor=False,
            timeout=10,
        )
        if values is None:
            raise RuntimeError(f"Failed to read {pv.pvname}")

        values = np.asarray(values)
        if values.ndim != 1 or values.size == 0:
            raise RuntimeError(f"Invalid waveform: {pv.pvname}")

        columns.append(values)
        print(f"{pv.pvname}: {values.size} samples")

    lengths = [len(values) for values in columns]
    if len(set(lengths)) != 1:
        raise RuntimeError(f"Channel lengths differ: {lengths}")

    formats = [
        "%d" if values.dtype.kind in "iu" else "%.17g"
        for values in columns
    ]

    # Four columns: A, B, C, D. No sample scaling or bit shifting.
    # Exclusive creation prevents overwriting an existing capture.
    with open(args.filename, "x") as output:
        np.savetxt(
            output,
            np.column_stack(columns),
            delimiter="\t",
            fmt=formats,
            header="\t".join(names),
        )

    print(f"Saved {lengths[0]} rows to {args.filename}")


if __name__ == "__main__":
    main()
