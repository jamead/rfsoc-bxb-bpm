# Bunch-by-Bunch Resolution Measurement

## Overview

The goal of this experiment is to measure the resolution of the **bunch-by-bunch beam position measurement** using the available button signals in the hutch.

Initial testing will be performed with a **single bunch** to minimize the effects of cable reflections on the measured signal.

## Experimental Setup

- Two button signals are available in the hutch for the measurements.
- The system can be tuned during regular machine operations using the **camshaft bunch**.
- A **500 MHz RF reference signal** is available for synchronization of the **Libera Digit 500**.
- During the tests, the button signal will be passed through a **Gaussian filter** to stretch the pulse and improve sampling of the waveform.
- A new **RFSoC prototype board** will be used for the tests to avoid disrupting normal NSLS-II operations.

## RFSoC Data Acquisition Requirements

For the RFSoC measurements:

- Capture window: **30 ns**
- Samples per channel: **150 ADC samples**
- Number of consecutive turns: **100–1000 turns**

The captured data will be used to evaluate the bunch-by-bunch measurement resolution.

## Signal-Level Measurements

Joe Mead will provide measurements of the expected button signal levels in the hutch. These measurements will be used to determine the appropriate input range, gain, filtering, and ADC configuration for the test setup.

## Beam Time and Operations

Beam time for the experiment will require coordination with Beam Operations.

An **MoU (Memorandum of Understanding)** should be completed, and an account should be provided for charging the required beam time.

## Action Items

- **Joe Mead:** Provide button signal-level measurements from the hutch.
- Prepare the new RFSoC prototype board for testing.
- Configure the Gaussian filter for pulse stretching.
- Configure RFSoC acquisition for 150 samples/channel over 100–1000 consecutive turns.
- Verify synchronization using the available 500 MHz RF reference.
- Complete the required MoU and establish the beam-time charging account.
