#!/usr/bin/env python3
"""Exercise the real app.c with mocked GPIO, events and Zigbee transport."""
from pathlib import Path
import os
import shlex
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
STUB = r'''
#ifndef CONTACT_TEST_STUB_H
#define CONTACT_TEST_STUB_H
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <stdarg.h>
#include <assert.h>
typedef unsigned sl_status_t;
typedef struct { unsigned delay; bool active; } sl_zigbee_af_event_t;
#define SL_STATUS_OK 0
#define SL_STATUS_NETWORK_UP 1
#define SL_STATUS_NETWORK_DOWN 2
#define SL_ZIGBEE_NO_NETWORK 0
#define SL_ZIGBEE_JOINED_NETWORK 1
#define SL_ZIGBEE_JOINED_NETWORK_NO_PARENT 2
#define ZCL_IAS_ZONE_CLUSTER_ID 0x500
#define ZCL_ZONE_STATUS_ATTRIBUTE_ID 2
#define ZCL_BITMAP16_ATTRIBUTE_TYPE 0x19
#define gpioPortC 2
#define gpioModeInput 0
#define cmuClock_GPIO 0
typedef unsigned sl_zigbee_af_cluster_id_t;
typedef unsigned sl_zigbee_af_attribute_id_t;
#define ZCL_ZONE_STATE_ATTRIBUTE_ID 0
#define ZCL_ZONE_ID_ATTRIBUTE_ID 17
#define CLUSTER_MASK_SERVER 1
#define SL_GPIO_INTERRUPT_UNAVAILABLE -1
#define SL_GPIO_INTERRUPT_RISING_FALLING_EDGE 4
typedef unsigned sl_gpio_port_t;
typedef struct { sl_gpio_port_t port; unsigned pin; } sl_gpio_t;
static unsigned network, gpio_level, usb_level, joins, notifications, moves;
static bool usb_power, moving;
static unsigned irq_count;
void window_contact_battery_init(void) {}
void window_contact_battery_request(void) {}
void window_contact_power_init(void) {}
void window_contact_power_set_usb(bool on) { usb_power = on; }
bool window_contact_power_usb_present(void) { return usb_power; }
static void sl_zigbee_af_isr_event_init(sl_zigbee_af_event_t *ev, void (*h)(sl_zigbee_af_event_t *)) { (void)h; ev->active = false; }
static void sl_zigbee_af_event_set_active(sl_zigbee_af_event_t *ev) { ev->active = true; ev->delay = 0; }
static bool sl_zigbee_af_event_is_scheduled(sl_zigbee_af_event_t *ev) { return ev->active; }
bool sl_zigbee_af_move_in_progress_cb(void) { return moving; }
bool sl_zigbee_af_end_device_support_pre_network_move_cb(void);
static bool sl_zigbee_af_start_move_cb(void) { if (sl_zigbee_af_end_device_support_pre_network_move_cb()) return false; moves++; moving = true; return true; }
static unsigned sl_gpio_configure_external_interrupt(const sl_gpio_t *p, int32_t *irq, unsigned flags, void (*cb)(uint8_t,void*), void *ctx) { assert(p->port == 2 && flags == 4 && cb != NULL && ctx == NULL); *irq = (int32_t)irq_count++; return 0; }
static sl_status_t join_result;
static bool enrolled;
static uint16_t zone_status;
static void sl_zigbee_app_debug_println(const char *fmt, ...) { (void)fmt; }
static unsigned sl_zigbee_af_network_state(void) { return network; }
static bool sl_zigbee_af_ias_zone_cluster_am_i_enrolled(unsigned ep)
{ assert(ep == 1); return enrolled; }
static sl_status_t sl_zigbee_af_network_steering_start(void)
{ joins++; return join_result; }
static void sl_zigbee_af_event_init(sl_zigbee_af_event_t *ev,
                                  void (*handler)(sl_zigbee_af_event_t *))
{ (void)handler; ev->active = false; }
static void sl_zigbee_af_event_set_delay_ms(sl_zigbee_af_event_t *ev, unsigned ms)
{ ev->active = true; ev->delay = ms; }
static void sl_zigbee_af_event_set_inactive(sl_zigbee_af_event_t *ev)
{ ev->active = false; }
static unsigned GPIO_PinInGet(unsigned port, unsigned pin)
{ assert(port == 2 && pin < 2); return pin ? usb_level : gpio_level; }
static void GPIO_PinModeSet(unsigned port, unsigned pin, unsigned mode, unsigned v)
{ assert(port == 2 && pin < 2 && mode == 0 && v == 0); }
static void CMU_ClockEnable(unsigned clock, bool on) { (void)clock; assert(on); }
static void sl_mac_calibrate_current_channel(void) {}
static unsigned sl_zigbee_af_read_server_attribute(unsigned ep, unsigned cluster,
                                   unsigned attr, uint8_t *data, unsigned size)
{ assert(ep == 1 && cluster == 0x500 && attr == 2 && size == 2);
  *(uint16_t *)data = zone_status; return 0; }
static unsigned sl_zigbee_af_write_server_attribute(unsigned ep, unsigned cluster,
                                   unsigned attr, uint8_t *data, unsigned type)
{ assert(ep == 1 && cluster == 0x500 && attr == 2 && type == 0x19);
  zone_status = *(uint16_t *)data; return 0; }
static sl_status_t sl_zigbee_af_ias_zone_server_update_zone_status(
                                   unsigned ep, uint16_t status, unsigned delay)
{ assert(ep == 1 && delay == 0); notifications++; zone_status = status; return 0; }
#endif
'''
HARNESS = r'''
#include "app.c"
static void edge(unsigned level) {
  gpio_level = level;
  contact_irq(0, NULL);
  assert(edge_event.active);
  edge_handler(&edge_event);
  assert(!edge_event.active && sample_event.active && sample_event.delay == 60);
}
int main(void) {
  gpio_level = 1;
  sl_zigbee_af_main_init_cb();
  assert(!usb_power && sample_event.delay == 250 && join_event.delay == 250);
  sample_handler(&sample_event);
  assert(have_sample && !stable_closed && zone_status == 1 && notifications == 0);
  assert(!sample_event.active); // No recurring sensor timer while idle.
  join_result = 7; join_handler(&join_event);
  assert(joins == 1 && join_event.delay == 30000);
  join_handler(&join_event); assert(join_event.delay == 60000);
  for (unsigned i=0; i<12; i++) join_handler(&join_event);
  assert(join_event.delay == 900000 && retry_ms == 900000);
  join_result = 0; join_handler(&join_event); assert(!join_event.active);
  network = SL_ZIGBEE_JOINED_NETWORK;
  sl_zigbee_af_stack_status_cb(SL_STATUS_NETWORK_UP);
  assert(retry_ms == 30000);
  sync_handler(&sync_event); assert(notifications == 0);
  enrolled = true;
  sl_zigbee_af_post_attribute_change_cb(1, 0x500, 0, 1, 0, 0, 0, NULL);
  assert(sync_event.active);
  sync_handler(&sync_event); assert(notifications == 1 && zone_status == 1);
  edge(0); edge(1); sample_handler(&sample_event);
  assert(!sample_event.active && notifications == 1 && !stable_closed);
  zone_status |= 4;
  edge(0); sample_handler(&sample_event);
  assert(stable_closed && zone_status == 4 && notifications == 2);
  edge(1); sample_handler(&sample_event);
  assert(zone_status == 5 && notifications == 3);
  heartbeat_handler(&heartbeat_event);
  assert(notifications == 4 && heartbeat_event.delay == 1800000);
  network = SL_ZIGBEE_JOINED_NETWORK_NO_PARENT;
  sl_zigbee_af_stack_status_cb(SL_STATUS_NETWORK_DOWN);
  assert(sl_zigbee_af_end_device_support_pre_network_move_cb());
  assert(moves == 0 && join_event.active);
  join_handler(&join_event); assert(moves == 1 && moving && join_event.active);
  join_handler(&join_event); assert(moves == 1); // No overlapping recovery.
  edge(0); sample_handler(&sample_event);
  assert(zone_status == 4 && notifications == 4);
  moving = false; network = SL_ZIGBEE_JOINED_NETWORK;
  sl_zigbee_af_stack_status_cb(SL_STATUS_NETWORK_UP);
  sync_handler(&sync_event); assert(notifications == 5 && zone_status == 4);
  assert(!sample_event.active && !edge_event.active);
#if WINDOW_CONTACT_USB_SENSE_ENABLED
  assert(irq_count == 2);
  usb_level = 1; usb_irq(1, NULL); usb_edge_handler(&usb_edge_event);
  assert(usb_sample_event.delay == 100);
  usb_sample_handler(&usb_sample_event);
  assert(usb_power && retry_ms == 30000);
  join_result = 7; network = SL_ZIGBEE_NO_NETWORK;
  join_handler(&join_event); join_handler(&join_event);
  assert(join_event.delay == 30000 && retry_ms == 30000);
  usb_level = 0; usb_irq(1,NULL); usb_edge_handler(&usb_edge_event);
  usb_sample_handler(&usb_sample_event); assert(!usb_power);
#else
  assert(irq_count == 1);
#endif
  return 0;
}
'''

with tempfile.TemporaryDirectory(prefix="window-contact-test-") as directory:
    tmp = Path(directory)
    for name in ("app/framework/include/af.h", "network-steering.h",
                 "ias-zone-server.h", "em_gpio.h", "em_cmu.h", "sl_gpio.h"):
        header = tmp / name
        header.parent.mkdir(parents=True, exist_ok=True)
        header.write_text('#include "stub.h"\n')
    (tmp / "stub.h").write_text(STUB)
    (tmp / "test.c").write_text(HARNESS)
    for usb_sense in (0, 1):
        subprocess.run(shlex.split(os.environ.get("CC", "cc")) + ["-std=c99", "-Wall", "-Wextra", "-Werror",
                        f"-DWINDOW_CONTACT_USB_SENSE_ENABLED={usb_sense}",
                        "-I", str(tmp), "-I", str(ROOT), "-I", str(ROOT / "config"),
                        str(tmp / "test.c"), "-o", str(tmp / "test")], check=True)
        subprocess.run([str(tmp / "test")], check=True)
print("PASS: interrupt debounce, idle timers, enrollment, backoff, parent recovery and USB transitions")
