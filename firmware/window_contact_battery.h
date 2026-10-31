#ifndef WINDOW_CONTACT_BATTERY_H
#define WINDOW_CONTACT_BATTERY_H
#include <stdint.h>
// Returns ZCL half-percent units (0..200), or 0xFF for an implausible voltage.
uint8_t window_contact_battery_percent(uint16_t millivolts);
// Enables PD3 only for settling + ADC sampling, then shuts ADC and divider off.
// Returns zero on timeout or implausible result; no claim of battery presence.
uint16_t window_contact_battery_measure_mv(void);
void window_contact_battery_init(void);
void window_contact_battery_request(void);
#endif
