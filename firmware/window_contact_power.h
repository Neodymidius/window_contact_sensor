#ifndef WINDOW_CONTACT_POWER_H
#define WINDOW_CONTACT_POWER_H
#include <stdbool.h>
void window_contact_power_init(void);
void window_contact_power_set_usb(bool usb_present);
bool window_contact_power_usb_present(void);
#endif
