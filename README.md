# Zigbee window contact sensor

A battery-powered Zigbee contact sensor built with a **Seeed Studio XIAO MG24**
and **Honeywell SM353LT** magnetoresistive switch. Includes a FreeCAD enclosure.

- Standard IAS Zone contact status: **closed = 0 / off**, **open = 1 / on**.
- Battery voltage and estimated percentage through Zigbee Power Configuration.
- Sleepy end-device operation with interrupt-driven contact detection and EM2.
- Optional automatic USB/battery power policy with a VBUS sensing divider.

**First public release: v0.1.0 (experimental).** Battery life has not been
measured. This is a hobby sensor, not a certified security product.

## Use a prebuilt release

Download the XIAO MG24 firmware ZIP from this repository's GitHub Releases once
published. Read [flashing and pairing](docs/FLASHING.md) before programming.
Updates currently use USB/OpenOCD; Zigbee OTA is not implemented.

The default build uses battery power policy even when USB is connected. Automatic
USB detection requires the extra circuit and configuration described in
[hardware and firmware details](docs/firmware.md#usbbattery-switching).

## Wiring

| Component | XIAO MG24 |
| --- | --- |
| SM353LT supply | 3V3 |
| SM353LT ground | GND |
| SM353LT output | D0 / PC00 |
| Protected single-cell 3.7 V LiPo | Battery pads, correct polarity |

SM353LT output is LOW with a magnet present. No pull-up is needed. Follow the
sensor package drawing for lead identification.

## Develop and build

See [BUILDING.md](docs/BUILDING.md). A snapshot of generated configuration is
included so the checked-in firmware can be built without running Studio or ZAP.
The proprietary/vendor SDK libraries are **not** bundled: install **Simplicity
SDK 2026.6.2**, then copy the required files locally using the checksum-verified
setup script. Use **Arm GNU 14.2.rel1** with its matching LTO tools.

```sh
python3 scripts/prepare_sdk.py --sdk-root /path/to/simplicity-sdk
export ARM_GCC_DIR=/path/to/arm-gnu-toolchain
cd firmware/cmake_gcc
cmake --preset project
cmake --build --preset default_config
```

Open `window_contact_sensor.code-workspace` in VS Code to make `firmware/` the
workspace folder expected by the OpenOCD flashing extension.

## Home Assistant

With ZHA, the contact should expose an opening sensor and battery percentage.
Set the contact entity's **Show as** setting to **Window** for Open/Closed labels.
Raw Home Assistant binary states remain on/off. Native battery percentage uses
ZCL half-percent units: 191 means 95.5%.

After upgrading from an earlier always-awake build, a normal leave and fresh
pairing may be needed. Its node descriptor must not advertise mains power or an
always-on receiver. See [troubleshooting](docs/FLASHING.md#home-assistant).

## Repository layout

- `firmware/`: application, configuration, generated build snapshot and tests.
- `scripts/`: SDK setup and repeatable release packaging.
- `docs/`: build, hardware, flashing and release instructions.
- `tools/`: Linux USB permission rule; downloaded tools stay ignored.
- `Box.FCStd`: existing FreeCAD enclosure design.
- `Box.20261024-212942.FCBak`: existing enclosure backup, preserved unchanged.

## Tests

A native C compiler and Python 3 are sufficient:

```sh
python3 firmware/tests/run_host_tests.py
python3 firmware/tests/run_power_tests.py
python3 firmware/tests/run_battery_tests.py
```

GitHub Actions runs these mocked host tests. Radio behavior, battery accuracy
and power consumption still require hardware testing. Existing SDK LTO
neighbor-table bounds warnings remain unresolved.

## License

The existing [MIT license](LICENSE) applies to original project contributions.
Silicon Labs-derived files retain their own notices and terms; see
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Dependencies must be obtained
under their respective licenses.

Maintainer release steps: [RELEASING.md](docs/RELEASING.md).
