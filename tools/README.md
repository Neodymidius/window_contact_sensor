# OpenOCD and Linux USB access

No downloaded executable is checked in. The tested Linux x86_64 OpenOCD package
comes from Silicon Labs' Arduino tool manifest:

- Manifest: https://siliconlabs.github.io/arduino/package_arduinosilabs_index.json
- Archive: https://downloads.arduino.cc/tools/openocd-0.12.0-arduino1-static-x86_64-ubuntu16.04-linux-gnu.tar.bz2
- SHA-256: `c48b4b348a68c3394e29fb7469a9eadf815a029e223b1612faff86bf4e7f053c`

Download, verify and extract it into `tools/openocd/` (strip its archive's single
parent directory) or another local directory. Follow the package's license.
Use an appropriate separately installed distribution on other platforms.

From the repository root on Linux:

```sh
sudo install -m 0644 tools/60-xiao-mg24.rules /etc/udev/rules.d/60-xiao-mg24.rules
sudo udevadm control --reload-rules
```

Reconnect USB afterward. The rule applies only to Seeed USB ID `2886:0062`.

The VS Code extension needs its installation root configured, not just the
extension itself. Run `scripts/prepare_sdk.py --sdk-root /path/to/sdk
--openocd-root /path/to/openocd` to write the ignored local workspace settings.
