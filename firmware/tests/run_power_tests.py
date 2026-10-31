#!/usr/bin/env python3
"""Compile the real board power module with mocked GPIO/UART/power manager APIs."""
import os
from pathlib import Path
import shlex
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
STUB = r'''
#ifndef POWER_TEST_STUB_H
#define POWER_TEST_STUB_H
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
typedef unsigned sl_status_t;
#define SL_STATUS_OK 0
#define SL_STATUS_EMPTY 1
#define gpioPortA 0
#define gpioPortB 1
#define gpioPortC 2
#define gpioPortD 3
#define gpioModePushPull 1
#define gpioModeDisabled 0
#define SL_POWER_MANAGER_EM0 0
#define SL_POWER_MANAGER_EM1 1
#define SL_POWER_MANAGER_EM2 2
#define SL_POWER_MANAGER_EVENT_TRANSITION_ENTERING_EM2 1
#define SL_POWER_MANAGER_EVENT_TRANSITION_LEAVING_EM2 2
typedef unsigned sl_power_manager_em_t;
typedef unsigned sl_power_manager_em_transition_event_handle_t;
typedef struct { unsigned event_mask; void (*on_event)(unsigned,unsigned); } sl_power_manager_em_transition_event_info_t;
typedef struct {
 void *context;
 sl_status_t (*write)(void*, const void*, size_t);
 sl_status_t (*write_async)(void*, void*);
 sl_status_t (*read)(void*,void*,size_t,size_t*);
} sl_iostream_t;
typedef sl_iostream_t sl_iostream_uart_t;
static sl_iostream_t stream;
static sl_iostream_t *sl_iostream_vcom_handle = &stream;
static sl_iostream_uart_t *sl_iostream_uart_vcom_handle = &stream;
static unsigned modes[4][16], levels[4][16], init_calls, deinit_calls, subscriptions;
static unsigned requirements, flash_command, flash_bits;
static bool restricted;
static void GPIO_PinModeSet(unsigned port,unsigned pin,unsigned mode,unsigned value)
{ modes[port][pin]=mode; levels[port][pin]=value; }
static void GPIO_PinOutSet(unsigned port,unsigned pin)
{ if (port == 0 && pin == 0 && !levels[0][6]) { flash_command = (flash_command << 1) | levels[1][0]; flash_bits++; }
  levels[port][pin]=1; }
static void GPIO_PinOutClear(unsigned port,unsigned pin) { levels[port][pin]=0; }
static void sl_udelay_wait(unsigned us) { (void)us; }
static void sl_power_manager_subscribe_em_transition_event(sl_power_manager_em_transition_event_handle_t *handle,
 const sl_power_manager_em_transition_event_info_t *info)
{ (void)handle; assert(info->event_mask==3); subscriptions++; }
static void sl_power_manager_add_em_requirement(unsigned em) { assert(em==1); requirements++; }
static void sl_power_manager_remove_em_requirement(unsigned em) { assert(em==1 && requirements); requirements--; }
static unsigned mock_init(void) { stream.context = &stream; init_calls++; return 0; }
static struct { sl_status_t (*init)(void); } sl_iostream_instance_vcom_info = {mock_init};
static unsigned sl_iostream_uart_deinit(sl_iostream_uart_t *handle)
{ assert(handle->context); handle->context=NULL; deinit_calls++; restricted=false; return 0; }
static void sl_iostream_set_system_default(sl_iostream_t *handle) { assert(handle == &stream); }
static void sl_iostream_uart_set_rx_energy_mode_restriction(sl_iostream_uart_t *handle,bool on)
{ assert(handle->context); restricted=on; }
#endif
'''
HARNESS = r'''
#include "window_contact_power.c"
int main(void) {
  stream.context=&stream; // Generated initialization has already run.
  window_contact_power_init();
  assert(flash_bits==8 && flash_command==0xB9 && levels[0][6]);
  assert(levels[0][7] && !levels[3][3] && !levels[2][8] && !levels[3][5]);
  assert(subscriptions==1);
  window_contact_power_set_usb(false);
  assert(deinit_calls==1 && init_calls==0 && !stream.context && !requirements);
  assert(modes[0][8]==gpioModeDisabled && modes[0][9]==gpioModeDisabled);
  assert(stream.write(NULL,NULL,0)==0);
  size_t count=9; assert(stream.read(NULL,NULL,0,&count)==SL_STATUS_EMPTY && count==0);
  window_contact_power_set_usb(false); assert(deinit_calls==1);
  power_transition(0,2); assert(!levels[1][5]);
  power_transition(2,0); assert(levels[1][5]);
  window_contact_power_set_usb(true);
  assert(init_calls==1 && requirements==1 && restricted && window_contact_power_usb_present());
  window_contact_power_set_usb(true); assert(init_calls==1 && requirements==1);
  window_contact_power_set_usb(false);
  assert(deinit_calls==2 && !requirements && !restricted && !window_contact_power_usb_present());
  window_contact_power_set_usb(true);
  assert(init_calls==2 && requirements==1 && subscriptions==1);
  window_contact_power_set_usb(false); assert(!requirements);
  return 0;
}
'''
with tempfile.TemporaryDirectory(prefix="window-power-test-") as directory:
    tmp=Path(directory)
    for header in ("em_gpio.h", "sl_assert.h", "sl_iostream.h", "sl_iostream_uart.h",
                   "sl_iostream_init_eusart_instances.h", "sl_power_manager.h", "sl_udelay.h"):
        (tmp/header).write_text('#include "stub.h"\n')
    (tmp/"stub.h").write_text(STUB)
    (tmp/"test.c").write_text(HARNESS)
    subprocess.run(shlex.split(os.environ.get("CC", "cc")) + ["-std=c99", "-Wall", "-Wextra", "-Werror",
                   "-I", str(tmp), "-I", str(ROOT), str(tmp/"test.c"), "-o", str(tmp/"test")],check=True)
    subprocess.run([str(tmp/"test")],check=True)
print("PASS: flash sleep command, peripheral shutdown, UART restoration, balanced power requirements and RF switching")
