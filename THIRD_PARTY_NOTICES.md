# Third-party notices

The root MIT license is the existing license for original project contributions.
It does not replace the notices or licenses in Silicon Labs-derived files.

`firmware/app.c`, generated files in `firmware/autogen/`, and many configuration
headers retain Silicon Labs notices. `firmware/main.c` and other SDK-derived
files may use the Zlib license where marked. Keep the file-level notices.
The SDK's licensing overview is reproduced in `LICENSES/Simplicity-SDK.txt`.
The Silicon Labs MSLA is linked there and remains applicable where specified.

Silicon Labs SDK source and libraries are not bundled in the Git source tree.
The setup script copies a checksum-verified subset from the user's separately
installed Simplicity SDK 2026.6.2. The compiled firmware links Silicon Labs
Zigbee/RAIL and other SDK components under their respective terms.

OpenOCD binaries are not bundled with the repository or firmware release ZIP.
Obtain OpenOCD separately under its own GPL license and accompanying notices.
GitHub Actions checkout is also an external dependency with its own license.

This project does not claim Zigbee certification. The battery percentage is an
estimate and is not a substitute for hardware battery protection.
