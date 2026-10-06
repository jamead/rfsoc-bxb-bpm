#!/usr/bin/env python3
"""Read a Tektronix analog WFM and plot calibrated samples.

Install: python -m pip install numpy matplotlib
Run:     python plot_tek_wfm.py capture.wfm
Zoom:    python plot_tek_wfm.py capture.wfm --zoom-ns -10 10
Export:  python plot_tek_wfm.py capture.wfm --csv capture.csv --no-show

Times are relative to the scope trigger; no ADC bit shifting is applied.
"""
import argparse
from pathlib import Path
import numpy as np
import struct
from types import SimpleNamespace


def unit_text(value):
    if isinstance(value, bytes):
        return value.split(b'\0', 1)[0].decode('ascii', errors='replace')
    return str(value).rstrip('\0')


def read_tek_wfm(filename):
    """Read single-record analog Tek WFM versions 1–3 directly.

    Layout: Tektronix reference manual 077-0220-05, including version
    adjustments on pages 15–16. Pre/postcharge samples are excluded.
    FastFrame, envelope, digital and waveform database records are rejected.
    File checksums and optional trailing display metadata are not interpreted.
    Returns (time_seconds, scaled_amplitude, metadata).
    """
    data = Path(filename).read_bytes()
    if len(data) < 78:
        raise ValueError('Truncated WFM header.')
    endian = {b'\x0f\x0f': '<', b'\xf0\xf0': '>'}.get(data[:2])
    if endian is None:
        raise ValueError('Unrecognized Tek WFM byte-order marker.')
    versions = {b':WFM#001': 1, b':WFM#002': 2, b':WFM#003': 3}
    version = versions.get(data[2:10])
    if version is None:
        raise ValueError(f'Unsupported WFM version: {data[2:10]!r}')

    def unpack(fmt, offset):
        if offset < 0 or offset + struct.calcsize(endian + fmt) > len(data):
            raise ValueError('Truncated WFM header or data.')
        return struct.unpack_from(endian + fmt, data, offset)

    def scalar(fmt, offset):
        return unpack(fmt, offset)[0]

    # V2 adds a two-byte summary field; V3 expands four view fields by 4 bytes.
    summary_bytes = 2 if version >= 2 else 0
    view_growth = 4 if version == 3 else 0
    explicit = 166 + summary_bytes
    implicit = 478 + summary_bytes + 2 * view_growth
    curve = 790 + summary_bytes + 4 * view_growth
    header_end = curve + 30
    if len(data) < header_end:
        raise ValueError('Truncated WFM header.')
    if scalar('I', 72) != 0 or scalar('I', 78) != 0:
        raise ValueError('FastFrame files are not supported by this reader.')
    if unpack('III', 114) != (1, 1, 2):
        raise ValueError('Expected a single analog Y-versus-time waveform.')
    if scalar('I', explicit + 76) != 0:
        raise ValueError('Only ordinary sample storage is supported (no envelopes).')

    yscale, yoffset = unpack('dd', explicit)
    dt, t0 = unpack('dd', implicit)
    yunit = data[explicit + 20:explicit + 40]
    xunit = data[implicit + 20:implicit + 40]
    if unit_text(xunit) != 's':
        raise ValueError('Expected horizontal units of seconds.')
    if not np.isfinite([yscale, yoffset, dt, t0]).all() or dt <= 0:
        raise ValueError('Invalid waveform axis scaling.')
    formats = {0: 'i2', 1: 'i4', 2: 'u4', 3: 'u8', 4: 'f4', 5: 'f8'}
    if version == 3:
        formats.update({6: 'u1', 7: 'i1'})
    fmt = scalar('I', explicit + 72)
    if fmt not in formats:
        raise ValueError(f'Unsupported sample format {fmt}.')
    dtype = np.dtype(endian + formats[fmt])
    if data[15] != dtype.itemsize:
        raise ValueError('Sample format and bytes-per-point disagree.')
    buffer_start = scalar('I', 16)
    pre, start, stop, post, end = unpack('IIIII', curve + 10)
    if not (buffer_start >= header_end and 0 <= pre <= start < stop <= post <= end
            and buffer_start + end <= len(data)):
        raise ValueError('Invalid curve offsets or truncated sample buffer.')
    if any(offset % dtype.itemsize for offset in (pre, start, stop, post, end)):
        raise ValueError('Curve offsets are not sample-aligned.')
    count = (stop - start) // dtype.itemsize
    raw = np.frombuffer(data, dtype=dtype, count=count, offset=buffer_start + start)
    y = raw.astype(np.float64) * yscale + yoffset
    t = t0 + np.arange(count, dtype=np.float64) * dt
    metadata = SimpleNamespace(x_axis_spacing=dt, y_axis_units=yunit,
                               x_axis_units=xunit, version=version,
                               y_axis_spacing=yscale, y_axis_offset=yoffset)
    return t, y, metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('filename', type=Path)
    parser.add_argument('--output', type=Path, help='PNG filename (default: input filename with .png extension)')
    parser.add_argument('--csv', type=Path, help='Export all calibrated samples to CSV')
    parser.add_argument('--zoom-ns', nargs=2, type=float, metavar=('START', 'END'), help='Zoom interval in ns relative to trigger')
    parser.add_argument('--no-show', action='store_true', help='Save without opening a GUI')
    args = parser.parse_args()
    if args.no_show:
        import matplotlib
        matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    try:
        t, y, w = read_tek_wfm(args.filename)
    except (OSError, ValueError, TypeError) as exc:
        parser.error(str(exc))
    unit = unit_text(w.y_axis_units)
    dt = float(w.x_axis_spacing)
    print(f'Samples: {len(y):,}')
    print(f'Sample interval: {dt * 1e12:g} ps; sample rate: {1 / dt / 1e9:g} GS/s')
    print(f'Time range: {t[0] * 1e6:.6f} to {t[-1] * 1e6:.6f} us')
    print(f'Amplitude range: {y.min():.6g} to {y.max():.6g} {unit}')
    if args.zoom_ns:
        lo, hi = np.asarray(args.zoom_ns) * 1e-9
        if lo >= hi:
            parser.error('--zoom-ns START must be less than END')
    else:
        # Show a 20 ns interval around the largest excursion from the median.
        peak_time = t[np.argmax(np.abs(y - np.median(y)))]
        lo, hi = peak_time - 10e-9, peak_time + 10e-9
    mask = (t >= lo) & (t <= hi)
    if np.count_nonzero(mask) < 2:
        parser.error('Zoom interval must contain at least two samples.')

    fig, axes = plt.subplots(2, 1, figsize=(12, 7), layout='constrained')
    axes[0].plot(t * 1e6, y, linewidth=0.55)
    axes[0].set(xlabel='Time relative to trigger (µs)', ylabel=f'Amplitude ({unit})', title=f'{args.filename.name} — full record')
    axes[1].plot(t[mask] * 1e9, y[mask], '.-', linewidth=0.8, markersize=2)
    axes[1].set(xlabel='Time relative to trigger (ns)', ylabel=f'Amplitude ({unit})', title='Waveform detail')
    for ax in axes:
        ax.grid(True, alpha=0.25)
    output = args.output or args.filename.with_suffix('.png')
    fig.savefig(output, dpi=180)
    print(f'Saved plot: {output}')
    if args.csv:
        np.savetxt(args.csv, np.column_stack((t, y)), delimiter=',', header=f'time_s,amplitude_{unit}', comments='', fmt='%.12g')
        print(f'Saved CSV: {args.csv}')
    if not args.no_show:
        plt.show()
    plt.close(fig)


if __name__ == '__main__':
    main()
