#ifndef WINDOW_CONTACT_CONFIG_H
#define WINDOW_CONTACT_CONFIG_H

// XIAO MG24 D0 / PC00; Honeywell SM353LT push-pull, active LOW.
#define WINDOW_CONTACT_PORT                 gpioPortC
#define WINDOW_CONTACT_PIN                  0U
#define WINDOW_CONTACT_CLOSED_LEVEL         0U
#define WINDOW_CONTACT_ENDPOINT             1U
#define WINDOW_CONTACT_DEBOUNCE_MS           60U
#define WINDOW_CONTACT_STARTUP_MS           250U
#define WINDOW_CONTACT_JOIN_RETRY_MS         30000U
#define WINDOW_CONTACT_MAX_RETRY_MS          900000U
#define WINDOW_CONTACT_HEARTBEAT_MS          1800000U

// ADC voltage trim: measured voltage / reported voltage * 1000.
#define WINDOW_CONTACT_BATTERY_CALIBRATION_PERMILLE 1000U

// Enable ONLY after fitting USB VBUS sensing: USB 5V -- 100k -- D1 -- 100k -- GND.
// D1 must otherwise be unused. Never connect USB 5V directly to a GPIO.
// Without this circuit the safe default is battery mode, even on USB.
#ifndef WINDOW_CONTACT_USB_SENSE_ENABLED
#define WINDOW_CONTACT_USB_SENSE_ENABLED     0
#endif
#define WINDOW_CONTACT_USB_PORT              gpioPortC
#define WINDOW_CONTACT_USB_PIN               1U
#define WINDOW_CONTACT_USB_DEBOUNCE_MS       100U

#endif
