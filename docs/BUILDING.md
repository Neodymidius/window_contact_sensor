# Build the firmware

## Requirements

- Silicon Labs Simplicity SDK **2026.6.2** installed separately.
- Arm GNU Toolchain **14.2.rel1** (GCC 14.2.1); the SDK contains LTO libraries.
- CMake 3.25+ (validated with 3.30.2), Ninja, Python 3.
- Optional: Simplicity Studio 6 and its Silicon Labs/OpenOCD VS Code extensions.

## Build the checked-in snapshot

Run from the repository root:

```sh
python3 scripts/prepare_sdk.py --sdk-root /path/to/simplicity-sdk
export ARM_GCC_DIR=/path/to/arm-gnu-toolchain
cd firmware/cmake_gcc
cmake --preset project
cmake --build --preset default_config
```

`ARM_GCC_DIR` must contain `bin/arm-none-eabi-gcc`. Alternatively, put the
matching toolchain's `bin` directory on PATH. CMake and Ninja must also be on
PATH. The output is `firmware/cmake_gcc/build/base/ZigbeeWindowContactSensor.hex`
and the corresponding `.s37`, `.bin`, `.out` and `.map` files. Prefer HEX/S37
for flashing because they encode their load addresses.

The setup script verifies all 1004 required SDK files against a pinned manifest
before copying them into ignored `firmware/simplicity_sdk_2026.6.2/`. It also
copies ZAP data/templates for optional regeneration. A mismatched SDK is rejected.
No SDK installation, authentication state or build cache is committed.

The portable toolchain file does not depend on a particular Linux home path,
Simplicity Installer cache location, or Commander installation. The generated
source snapshot preserves the exact component selection used by this release.
It is intentional that generated C/H/LD and component CMake files are tracked.

## VS Code / flashing extension

Open `window_contact_sensor.code-workspace`. Configure the installed OpenOCD
root using:

```sh
python3 scripts/prepare_sdk.py --sdk-root /path/to/simplicity-sdk \
  --openocd-root /path/to/openocd
```

This creates ignored `firmware/.vscode/settings.json`. The extension does not
expand `${workspaceFolder}` in its OpenOCD root setting, so the script writes a
local absolute path there. No downloaded OpenOCD executable is committed.
The known-working Linux x86_64 package is listed in `tools/README.md`.

## Changing components or clusters

The project metadata is `firmware/ZigbeeWindowContactSensor.slcp`; cluster data
is `firmware/config/zcl/zcl_config.zap`. Import/open the SLCP with the installed
SDK when using Studio. Prefer the SLCP over machine-specific SLPS cache state.

A full Studio regeneration is allowed to replace the component-generated files.
Review the diff and preserve the maintained `cmake_gcc/CMakeLists.txt` changes
(root include path and conditional IADC source), portable toolchain file,
application sources, and SDK-independent presets. If the selected SDK subset
changes, update `scripts/sdk-files.json` from the matching installed SDK and
validate a fresh snapshot build again. Do not silently regenerate with a newer
SDK or commit local `slc_args.json`.

The ZAP package paths are relative to the ignored SDK subset. If regenerating
with ZAP directly, pass the installed SDK's `zigbee/app/zcl/zcl-zap.json` and
`zigbee/app/framework/gen-template/gen-templates.json` using its `-z` and `-g`
arguments. Output belongs in `firmware/autogen/`.

Full Studio re-import/regeneration on another computer has not been validated;
the portable CMake snapshot build is the supported release reproduction path.

## Known limitations

The vendor stack produces neighbor-table bounds warnings under GCC LTO. The
link succeeds, but these warnings remain unresolved. Host tests mock hardware;
passing them is not evidence of radio compliance or a measured battery life.
