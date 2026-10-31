// Board power policy for Seeed Studio XIAO MG24 (EFR32MG24).
#include "window_contact_power.h"
#include "em_gpio.h"
#include "sl_assert.h"
#include <assert.h>
#include "sl_iostream.h"
#include "sl_iostream_uart.h"
#include "sl_iostream_init_eusart_instances.h"
#include "sl_power_manager.h"
#include "sl_udelay.h"

static bool usb_power;
static bool initialized;
static sl_power_manager_em_transition_event_handle_t power_handle;

static sl_status_t discard_write(void *context, const void *data, size_t length)
{
  (void)context; (void)data; (void)length;
  return SL_STATUS_OK;
}

static sl_status_t empty_read(void *context, void *data, size_t length, size_t *count)
{
  (void)context; (void)data; (void)length;
  if (count != NULL) {
    *count = 0;
  }
  return SL_STATUS_EMPTY;
}

static void flash_sleep(void)
{
  // P25Q32SH SPI: PA6 CS, PA0 CLK, PB0 MOSI, PB1 MISO. No SPI owner in this app.
  GPIO_PinModeSet(gpioPortA, 6, gpioModePushPull, 1);
  GPIO_PinModeSet(gpioPortA, 0, gpioModePushPull, 0);
  GPIO_PinModeSet(gpioPortB, 0, gpioModePushPull, 0);
  GPIO_PinModeSet(gpioPortB, 1, gpioModeDisabled, 0);
  GPIO_PinOutClear(gpioPortA, 6);
  for (unsigned bit = 0; bit < 8; bit++) {
    if (0xB9U & (0x80U >> bit)) {
      GPIO_PinOutSet(gpioPortB, 0);
    } else {
      GPIO_PinOutClear(gpioPortB, 0);
    }
    sl_udelay_wait(1);
    GPIO_PinOutSet(gpioPortA, 0);
    sl_udelay_wait(1);
    GPIO_PinOutClear(gpioPortA, 0);
  }
  GPIO_PinOutSet(gpioPortA, 6);
  GPIO_PinOutClear(gpioPortB, 0);
  sl_udelay_wait(10);
}

static void power_transition(sl_power_manager_em_t from, sl_power_manager_em_t to)
{
  // EM2 is entered only after RAIL releases its radio power requirement.
  // Restore the antenna switch on exit before the stack can use the radio.
  if (to == SL_POWER_MANAGER_EM2) {
    GPIO_PinOutClear(gpioPortB, 5);
  } else if (from == SL_POWER_MANAGER_EM2) {
    GPIO_PinOutSet(gpioPortB, 5);
    sl_udelay_wait(1);
  }
}

static const sl_power_manager_em_transition_event_info_t power_events = {
  .event_mask = SL_POWER_MANAGER_EVENT_TRANSITION_ENTERING_EM2
                | SL_POWER_MANAGER_EVENT_TRANSITION_LEAVING_EM2,
  .on_event = power_transition,
};

void window_contact_power_set_usb(bool present)
{
  if (initialized && present == usb_power) {
    return;
  }
  if (present) {
    // Use the instance initializer, not the all-instances initializer: the
    // latter would register the generated power notification a second time.
    if (sl_iostream_vcom_handle->context == NULL) {
      sl_status_t status = sl_iostream_instance_vcom_info.init();
      assert(status == SL_STATUS_OK);
      (void)status;
    }
    sl_iostream_set_system_default(sl_iostream_vcom_handle);
    sl_iostream_uart_set_rx_energy_mode_restriction(sl_iostream_uart_vcom_handle, true);
    sl_power_manager_add_em_requirement(SL_POWER_MANAGER_EM1);
  } else {
    if (initialized && usb_power) {
      sl_power_manager_remove_em_requirement(SL_POWER_MANAGER_EM1);
    }
    if (sl_iostream_vcom_handle->context != NULL) {
      sl_status_t status = sl_iostream_uart_deinit(sl_iostream_uart_vcom_handle);
      assert(status == SL_STATUS_OK);
      (void)status;
    }
    // CLI and stack logging still reference this stream. Leave a null context
    // (generated sleep hooks check it) and harmless no-op stream operations.
    sl_iostream_vcom_handle->write = discard_write;
    sl_iostream_vcom_handle->write_async = NULL;
    sl_iostream_vcom_handle->read = empty_read;
    sl_iostream_set_system_default(sl_iostream_vcom_handle);
    GPIO_PinModeSet(gpioPortA, 8, gpioModeDisabled, 0);
    GPIO_PinModeSet(gpioPortA, 9, gpioModeDisabled, 0);
  }
  usb_power = present;
  initialized = true;
}

bool window_contact_power_usb_present(void)
{
  return usb_power;
}

void window_contact_power_init(void)
{
  // User LED is active LOW (anode at 3V3): drive HIGH to turn it off.
  // Battery-divider load switch, microphone and IMU remain off.
  GPIO_PinModeSet(gpioPortA, 7, gpioModePushPull, 1);
  GPIO_PinModeSet(gpioPortD, 3, gpioModePushPull, 0);
  GPIO_PinModeSet(gpioPortC, 8, gpioModePushPull, 0);
  GPIO_PinModeSet(gpioPortD, 5, gpioModePushPull, 0);
  flash_sleep();
  sl_power_manager_subscribe_em_transition_event(&power_handle, &power_events);
}
