# Flashing and pairing — XIAO MG24

This firmware targets **Seeed Studio XIAO MG24 / EFR32MG24B220F1536IM48** and an
SM353LT on D0. Do not flash it onto a different board or a Zigbee USB coordinator.
The `.hex` and `.s37` files contain addresses; prefer these over a raw `.bin`.
No bootloader image or manufacturing tokens are included. Use the board's
existing working programming/bootloader setup.

## Program via USB

1. Extract the firmware ZIP and verify its checksum, then `SHA256SUMS` inside.
2. Install the CMSIS-DAP-capable OpenOCD distribution and appropriate USB rules.
   The XIAO should enumerate as USB `2886:0062` (Seeed CMSIS-DAP).
3. With OpenOCD and its scripts available, run the command below, replacing
   `<firmware.hex>` with the HEX file from the release.
4. Confirm `Verified OK`. Enable joining on the coordinator, then reset the XIAO.

```sh
openocd -f interface/cmsis-dap.cfg -f target/efm32s2_g23.cfg \
  -c 'adapter speed 1000' -c 'program "<firmware.hex>" verify reset exit'
```

If OpenOCD cannot find its configuration files, add
`-s /path/to/openocd/share/openocd/scripts`. On Linux, install the repository's
`tools/60-xiao-mg24.rules`, reload udev rules, and reconnect USB. The user must
have the applicable `plugdev` group/local-session permission.

The VS Code OpenOCD extension can flash the project build directly when the
`firmware/` workspace is open. It selects a single HEX automatically; no board
selection prompt appears.

`unable to find a matching CMSIS-DAP device` means the USB debugger was not
accessible: check cable, USB enumeration and permissions. `cannot read IDR`
means the USB debugger was found but could not access the MCU. EM2 debug
retention is disabled for low power, so reset/power-cycle the board while
connecting if necessary. Do not use mass erase as a first troubleshooting step.

## Power and wiring

- Sensor supply 3V3, ground GND, push-pull output D0/PC00.
- Magnet present means closed. Alarm1 = 0 closed, 1 open.
- Use a protected single-cell 3.7 V LiPo on the battery pads with correct polarity.
- Default policy is battery mode, including on USB: UART is shut down.
- Optional automatic USB sensing needs two 100k, 1% resistors:
  `VBUS -- 100k -- D1 -- 100k -- GND`, plus
  `WINDOW_CONTACT_USB_SENSE_ENABLED=1` and a rebuild. Never connect 5V directly
  to a GPIO. D1 must otherwise be unused.
- The yellow user LED is off (PA7 high). The red charge LED is hardware-controlled.

## Home Assistant

The device exposes IAS Zone and Power Configuration on endpoint 1. Battery
voltage is in 0.1 V units; percentage uses 0.5% units (191 = 95.5%). The estimate
comes from LiPo voltage, not a fuel gauge. During charging or with no battery
attached, the voltage may not represent usable charge accurately. Invalid ADC
measurements are reported as unknown (`255`).

For ZHA, set the binary sensor's **Show as** setting to **Window**. Raw states
remain off/on for closed/open. A battery entity is normally diagnostic. After
adding the battery cluster, re-interview or re-pair to discover it, then bind/
configure Power Configuration if necessary. Move the magnet during configuration
to wake the sleepy device.

If ZHA sees MAC capability flags `140` (`0x8C`), it still considers the device
mains-powered and always listening; this suppresses the native battery entity.
The intended sleepy capabilities are `128` (`0x80`). A normal leave and fresh
pairing can clear old device/network metadata. Reset alone preserves credentials.
A normal coordinator removal should deliver a leave before re-pairing. The build
has no dedicated factory-reset button or Zigbee OTA update support.

Zigbee2MQTT or another coordinator may require a custom device definition.
Reading battery attributes successfully does not prove automatic reporting is
configured. Coordinator reporting settings can increase the report interval.
