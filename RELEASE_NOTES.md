# v0.1.0 — first public release (experimental)

Targets Seeed Studio XIAO MG24 (EFR32MG24B220F1536IM48) with SM353LT on D0.

- Zigbee sleepy end device with standard IAS Zone contact state.
- Battery voltage and estimated percentage via Power Configuration.
- Interrupt debounce, EM2 sleep, peripheral shutdown and retry backoff.
- Optional USB power sensing; disabled in the default release build.
- Host tests, portable SDK setup and release packaging scripts.
- Existing FreeCAD enclosure design retained in the repository.

Flash with USB/CMSIS-DAP/OpenOCD; Zigbee OTA is not implemented. The release
build reports software build ID `0.1.0`. Read FLASHING.md before programming.
Firmware images contain no device-specific network credentials or provisioning
backup. Flashing the application normally preserves existing network tokens.

Validation: portable clean-directory CMake/GCC build, mocked host tests, SDK
file checksums, and archive checksums. The user reported successful operation of
the preceding workspace firmware; this release packaging build has not itself
been flashed. Battery lifetime and current consumption are not measured.
Existing vendor stack neighbor-table LTO warnings remain unresolved.

Home Assistant may require re-interview/re-pairing after earlier firmware.
Battery percentages are approximate and can be misleading during charging or
without a battery connected. See docs/firmware.md in the source distribution.
