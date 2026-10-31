# XIAO MG24 window contact sensor — low-power version

Zigbee 3.0 IAS Zone contact sensor for the Seeed Studio XIAO MG24
(EFR32MG24B220F1536IM48), using a Honeywell SM353LT on D0.

This version is a **sleepy Zigbee end device** using EM2 between contact events
and radio transactions. It uses the Silicon Labs PRO leaf stack, Zigbee 3.0
network steering, IAS Zone server, NVM3 storage, and end-device parent recovery.
It does not form its own network. Battery voltage and estimated state of charge are exposed through the standard
Power Configuration cluster. The battery divider is enabled only for measurements.

## Wiring

| SM353LT connection | XIAO MG24 |
| --- | --- |
| Supply | 3V3 |
| Ground | GND |
| Output | D0 / PC00 |

Use the SM353LT datasheet's package drawing to identify its leads; do not infer
lead numbering from a generic SOT-23 footprint. Power the sensor from 3.3 V so
its push-pull output matches the MCU input voltage. No pull-up is needed.
Magnet present gives LOW = closed; magnet absent gives HIGH = open.

PB4 selects the PCB antenna. PB5 powers its RF switch while awake; the power
manager switches it off for EM2 and restores it before radio activity. This
sequence still needs on-board RF/current validation.

UART diagnostics use PA08 TX / PA09 RX, separate from Arduino's D6/D7 serial
pins. UART is deinitialized and these pins become high impedance on battery,
preventing back-powering of the USB debugger. Debugging through EM2 is disabled;
connecting a debugger may require resetting the target. There is no firmware
pairing button or status LED requirement.

## USB/battery switching

**Default: battery policy at all times, including when USB is connected.**
The stock board has no dedicated VBUS-present input on the MG24. Automatic
switching requires the following additional sensing circuit (D1 must be free):

```text
USB 5V/VBUS pin --- 100 kΩ, 1% ---+--- D1 / PC01
                                |
                            100 kΩ, 1%
                                |
                               GND
```

This produces about 2.5 V at D1 with nominal 5 V USB and draws about 25 µA
from USB, not the battery. Never wire VBUS directly to a GPIO. Use a protected
3.7 V LiPo on the battery pads, not on D1 or the 3V3 pin.

After fitting the divider, set `WINDOW_CONTACT_USB_SENSE_ENABLED` to `1` in
`config/window_contact_config.h`, rebuild and flash. Both USB edges trigger an
interrupt followed by 100 ms settling. USB enables the UART and keeps the MCU
in EM0/EM1 for diagnostics; unplugging shuts the UART down and permits EM2.
The device remains a sleepy Zigbee end device in both modes; no network-role
change or deliberate leave occurs when switching power sources.

Battery mode turns off the LED, microphone/IMU supplies and battery-measurement
switch, and sends the external P25Q32SH flash its B9 deep-power-down command.
The battery divider is briefly re-enabled for ADC measurements every 30 minutes.
The board power module owns PA0, PA6, PA7, PA8, PA9, PB0, PB1, PB5, PC8, PD3
and PD5; do not reuse these without reviewing `window_contact_power.c`.
It assumes the published XIAO MG24 board wiring. Sleep current and battery life
have not been measured; the earlier 1–3 year estimate remains a target.

## Zigbee interface

- Endpoint 1; Home Automation profile `0x0104`; IAS Zone device `0x0402`.
- Basic server `0x0000`, Power Configuration server `0x0001`, Identify
  server/client `0x0003`, IAS Zone server `0x0500`.
- Manufacturer `DIY`; model `XIAO-MG24-Contact`; version `1.0.0`.
- IAS zone type `0x0015` (contact switch).
- Zone Status bit 0 (Alarm1): 1 = open, 0 = closed.
- CIE address, zone ID, enrollment state and zone type persist in flash.
- The SDK handles CIE address writes, enrollment requests/responses, binding,
  status-change notifications and queued delivery retries (10 entries, RAM).
- D0 uses both-edge interrupts and 60 ms debounce, with no periodic sensor
  sampling. Initial reading occurs after 250 ms. The SM353LT's own internal
  sampling interval also contributes to physical detection latency.
- Parent polling uses a five-second idle interval; the SDK fast-polls while
  transactions are pending. No EM4/reset-style sleep is used.
- Current state is sent after enrollment, after reconnection, on changes and
  every 30 minutes. Before enrollment, Zone Status remains readable locally.
  Transient changes while disconnected are not a durable event history.

## Battery reporting

Endpoint 1 exposes standard Power Configuration (`0x0001`) attributes:

| Attribute | Meaning | Zigbee representation |
| --- | --- | --- |
| `0x0020` BatteryVoltage | Measured battery voltage | 0.1 V units; e.g. 38 = 3.8 V |
| `0x0021` BatteryPercentageRemaining | Estimated charge | 0.5% units; e.g. 100 = 50% |

Both use `0xFF` for unknown. Sampling starts one second after initialization
and is requested again after network-up/IAS enrollment; otherwise it occurs
every 30 minutes. The native reporting component supports Read Attributes,
Configure Reporting, and bound reports. Defaults are a 60-second minimum,
1800-second maximum, and change thresholds of 0.1 V / 1%. Coordinator reporting
configuration takes precedence. If no Power Configuration binding exists,
firmware copies the enrolled IAS CIE destination to a free binding slot; it
never overwrites an existing binding. A full binding table needs coordinator
configuration before automatic reports can be delivered.

The on-board PD3 load switch enables the 10k/10k battery divider; IADC0 measures
PD4 using its internal reference and 0.5x gain. Firmware allows 2 ms settling,
discards the first conversion, averages eight more and then switches both ADC
and divider off. Conversion waits are bounded and cleanup also runs on timeout.
The module owns IADC0. The optional voltage calibration factor is
`WINDOW_CONTACT_BATTERY_CALIBRATION_PERMILLE` (default 1000). Compare the reported
voltage with a multimeter before relying on the estimate.

Percentage uses an approximate single-cell 4.2 V LiPo resting-voltage curve,
not a coulomb counter. It is affected by cell chemistry, load, temperature and
charging; do not use it as battery protection. Implausible measurements below
2.5 V or above 4.35 V become unknown. Without a battery attached, the charger
may still produce a plausible voltage at the battery pads: this hardware cannot
reliably detect battery presence from voltage alone. No charging-state flag is
reported.

After upgrading, re-interview/reconfigure the device (or remove/re-pair it) so
the coordinator discovers the added cluster and battery entities. Integration
support varies, especially for an otherwise unsupported custom model.

## Build and pair

1. Open this project in Simplicity Studio with Simplicity SDK 2026.6.2.
2. Build the `cmake_gcc` / `default_config` configuration. Generated firmware is
   in `cmake_gcc/build/base/ZigbeeWindowContactSensor.{hex,s37,bin,out}`.
3. Flash the HEX or S37 with your usual MG24 debugger/programmer setup.
   Flashing and bootloader compatibility must be checked for your board setup.
4. Enable joining on the coordinator, then power/reset the sensor. Without saved
   credentials, it tries network steering automatically and retries failed joins
   with 30, 60, 120, 240, 480, then 900-second delays in battery mode.
   Parent-loss recovery is similarly rate-limited around the SDK's bounded
   rejoin sequences. USB mode uses 30-second application retries. Reboot restores
   saved network credentials.
5. If upgrading a device already joined with the original always-awake firmware,
   leave and re-pair it once so its parent recognizes the sleepy-device settings.
   Do this before unplugging UART access, or fit/enable USB sensing first.
6. The coordinator must write its IEEE address to IAS CIE Address (`0x0010`),
   and complete IAS enrollment. Then move the magnet and verify open/closed.
   Automatic contact-entity discovery depends on the coordinator integration;
   a model-specific definition may be needed.
7. To move to another network, issue `network leave` through the Zigbee CLI,
   enable joining on the intended coordinator, and let automatic joining retry.
   Leave handling clears IAS enrollment through the SDK. Reset alone does not
   clear saved network state.

The endpoint and attributes are defined in `config/zcl/zcl_config.zap`.
Application pin/timing settings are in `config/window_contact_config.h`.
The CMake root include-directory addition is required because the SDK's IAS
Zone token header includes `config/ias-zone-server-config.h`.

To regenerate ZCL tables, use Studio's ZAP configuration tool. Its SDK paths
are recorded in `config/zcl/slc_args.json`; update these when moving machines.
Keep the `.slcp` component selection, configuration headers and ZAP file together.

## Verification

Run application behavior tests on a machine with a native C compiler:

```sh
python3 tests/run_host_tests.py
python3 tests/run_power_tests.py
python3 tests/run_battery_tests.py
# Or select a compiler with CC, e.g. CC=clang python3 tests/run_host_tests.py
```

These tests compile the actual `app.c` against mocked GPIO, Zigbee and event
APIs. They cover polarity, startup state, debounce/glitch rejection, enrollment,
status-bit preservation, capped exponential retry backoff, heartbeat, parent
loss/reconnect and USB transitions (sensing enabled and disabled). The power
tests check the flash command, UART lifecycle, balanced power requirements,
peripheral shutdown and RF-switch restoration. Battery tests cover ADC cleanup
on timeout, averaging, half-percent encoding, invalid readings and bindings.
They do not exercise the radio or establish Zigbee certification/compliance.

On hardware, measure current at the battery pads with USB physically removed,
including idle, transmit and coordinator-loss periods. Verify USB insert/remove
transitions with the sensing circuit fitted. Verify joining and IAS enrollment,
magnet
transitions in both directions, a power cycle while open and while closed,
coordinator loss/recovery, and leaving/rejoining another network. The new low-power firmware
has not yet been flashed or tested over the air in this workspace.

The GCC link currently emits neighbor-table bounds warnings from the supplied
Silicon Labs stack library under LTO. The build succeeds; those SDK warnings
remain unresolved and require review before production use.

Hardware references:
- [Seeed XIAO MG24 pin map](https://wiki.seeedstudio.com/xiao_mg24_getting_started/)
- [Honeywell SM353LT product family](https://automation.honeywell.com/us/en/products/sensing-solutions/sensors/magnetic-sensors/nanopower-series-magnetoresistive-sensor-ic)

Flash power-down command reference:
[Puya P25Q32SH datasheet](https://www.puyasemi.com/download_path/%E6%95%B0%E6%8D%AE%E6%89%8B%E5%86%8C/Flash/P25Q32SH_Datasheet_V2.0.pdf).
