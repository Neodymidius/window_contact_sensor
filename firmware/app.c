/***************************************************************************//**
 * @file app.c
 * @brief Callbacks implementation and application specific code.
 *******************************************************************************
 * # License
 * <b>Copyright 2021 Silicon Laboratories Inc. www.silabs.com</b>
 *******************************************************************************
 *
 * The licensor of this software is Silicon Laboratories Inc. Your use of this
 * software is governed by the terms of Silicon Labs Master Software License
 * Agreement (MSLA) available at
 * www.silabs.com/about-us/legal/master-software-license-agreement. This
 * software is distributed to you in Source Code format and is governed by the
 * sections of the MSLA applicable to Source Code.
 *
 ******************************************************************************/

// Sleepy IAS Zone contact sensor for XIAO MG24 / SM353LT.
#include "app/framework/include/af.h"
#include "network-steering.h"
#include "ias-zone-server.h"
#include "em_cmu.h"
#include "em_gpio.h"
#include "sl_gpio.h"
#include <assert.h>
#include "window_contact_config.h"
#include "window_contact_power.h"
#include "window_contact_battery.h"

// SDK end-device-support exports this callback without a public declaration.
extern bool sl_zigbee_af_move_in_progress_cb(void);

#define CONTACT_ALARM1 0x0001U
static sl_zigbee_af_event_t edge_event;
static sl_zigbee_af_event_t sample_event;
static sl_zigbee_af_event_t sync_event;
static sl_zigbee_af_event_t join_event;
static sl_zigbee_af_event_t heartbeat_event;
#if WINDOW_CONTACT_USB_SENSE_ENABLED
static sl_zigbee_af_event_t usb_edge_event;
static sl_zigbee_af_event_t usb_sample_event;
#endif
static bool candidate_closed;
static bool stable_closed;
static bool have_sample;
static bool events_ready;
static bool permit_move;
static uint32_t retry_ms = WINDOW_CONTACT_JOIN_RETRY_MS;

static bool read_closed(void)
{
  return GPIO_PinInGet(WINDOW_CONTACT_PORT, WINDOW_CONTACT_PIN)
         == WINDOW_CONTACT_CLOSED_LEVEL;
}

static void publish_contact(void)
{
  uint16_t status = 0;
  (void)sl_zigbee_af_read_server_attribute(WINDOW_CONTACT_ENDPOINT,
                                         ZCL_IAS_ZONE_CLUSTER_ID,
                                         ZCL_ZONE_STATUS_ATTRIBUTE_ID,
                                         (uint8_t *)&status, sizeof(status));
  status = (status & ~CONTACT_ALARM1) | (stable_closed ? 0 : CONTACT_ALARM1);
  if (sl_zigbee_af_network_state() == SL_ZIGBEE_JOINED_NETWORK
      && sl_zigbee_af_ias_zone_cluster_am_i_enrolled(WINDOW_CONTACT_ENDPOINT)) {
    sl_status_t result = sl_zigbee_af_ias_zone_server_update_zone_status(
      WINDOW_CONTACT_ENDPOINT, status, 0);
    sl_zigbee_app_debug_println("Contact %s, IAS send: 0x%04X",
                               stable_closed ? "closed" : "open", result);
  } else {
    (void)sl_zigbee_af_write_server_attribute(WINDOW_CONTACT_ENDPOINT,
                                            ZCL_IAS_ZONE_CLUSTER_ID,
                                            ZCL_ZONE_STATUS_ATTRIBUTE_ID,
                                            (uint8_t *)&status,
                                            ZCL_BITMAP16_ATTRIBUTE_TYPE);
  }
}

static void sample_handler(sl_zigbee_af_event_t *event)
{
  sl_zigbee_af_event_set_inactive(event);
  bool closed = read_closed();
  if (closed != candidate_closed) {
    candidate_closed = closed;
    sl_zigbee_af_event_set_delay_ms(event, WINDOW_CONTACT_DEBOUNCE_MS);
  } else if (!have_sample || stable_closed != closed) {
    stable_closed = closed;
    have_sample = true;
    publish_contact();
  }
}

static void edge_handler(sl_zigbee_af_event_t *event)
{
  sl_zigbee_af_event_set_inactive(event);
  candidate_closed = read_closed();
  sl_zigbee_af_event_set_delay_ms(&sample_event, WINDOW_CONTACT_DEBOUNCE_MS);
}

static void contact_irq(uint8_t int_no, void *context)
{
  (void)int_no;
  (void)context;
  // Only schedule an ISR-safe event. GPIO reads/debounce/Zigbee stay in task context.
  sl_zigbee_af_event_set_active(&edge_event);
}

static void sync_handler(sl_zigbee_af_event_t *event)
{
  window_contact_battery_request();
  sl_zigbee_af_event_set_inactive(event);
  if (have_sample) {
    publish_contact();
  }
}

static void schedule_retry(void)
{
  sl_zigbee_af_event_set_delay_ms(&join_event, retry_ms);
  if (!window_contact_power_usb_present()) {
    retry_ms = (retry_ms >= WINDOW_CONTACT_MAX_RETRY_MS / 2)
               ? WINDOW_CONTACT_MAX_RETRY_MS : retry_ms * 2;
  }
}

static void join_handler(sl_zigbee_af_event_t *event)
{
  sl_zigbee_af_event_set_inactive(event);
  if (sl_zigbee_af_network_state() == SL_ZIGBEE_NO_NETWORK) {
    if (sl_zigbee_af_network_steering_start() != SL_STATUS_OK) {
      schedule_retry();
    }
  } else if (sl_zigbee_af_network_state() == SL_ZIGBEE_JOINED_NETWORK_NO_PARENT) {
    if (!sl_zigbee_af_move_in_progress_cb()) {
      permit_move = true;
      (void)sl_zigbee_af_start_move_cb();
      permit_move = false;
    }
    schedule_retry();
  }
}

// Rate-limit parent recovery sequences as well as initial joining. The SDK
// still owns each bounded sequence of secure rejoin attempts.
bool sl_zigbee_af_end_device_support_pre_network_move_cb(void)
{
  if (permit_move) {
    return false;
  }
  if (events_ready && !sl_zigbee_af_event_is_scheduled(&join_event)) {
    schedule_retry();
  }
  return true;
}

static void heartbeat_handler(sl_zigbee_af_event_t *event)
{
  if (have_sample) {
    publish_contact();
  }
  sl_zigbee_af_event_set_delay_ms(event, WINDOW_CONTACT_HEARTBEAT_MS);
}

#if WINDOW_CONTACT_USB_SENSE_ENABLED
static void usb_sample_handler(sl_zigbee_af_event_t *event)
{
  sl_zigbee_af_event_set_inactive(event);
  bool usb = GPIO_PinInGet(WINDOW_CONTACT_USB_PORT, WINDOW_CONTACT_USB_PIN) != 0;
  window_contact_power_set_usb(usb);
  if (usb) {
    retry_ms = WINDOW_CONTACT_JOIN_RETRY_MS;
    sl_zigbee_af_event_set_delay_ms(&join_event, WINDOW_CONTACT_STARTUP_MS);
  }
}

static void usb_edge_handler(sl_zigbee_af_event_t *event)
{
  sl_zigbee_af_event_set_inactive(event);
  sl_zigbee_af_event_set_delay_ms(&usb_sample_event, WINDOW_CONTACT_USB_DEBOUNCE_MS);
}

static void usb_irq(uint8_t int_no, void *context)
{
  (void)int_no;
  (void)context;
  sl_zigbee_af_event_set_active(&usb_edge_event);
}
#endif

void sl_zigbee_af_main_init_cb(void)
{
  CMU_ClockEnable(cmuClock_GPIO, true);
  window_contact_power_init();
  sl_zigbee_af_isr_event_init(&edge_event, edge_handler);
  sl_zigbee_af_event_init(&sample_event, sample_handler);
  sl_zigbee_af_event_init(&sync_event, sync_handler);
  sl_zigbee_af_event_init(&join_event, join_handler);
  sl_zigbee_af_event_init(&heartbeat_event, heartbeat_handler);
  GPIO_PinModeSet(WINDOW_CONTACT_PORT, WINDOW_CONTACT_PIN, gpioModeInput, 0);
  const sl_gpio_t contact = { .port = (sl_gpio_port_t)WINDOW_CONTACT_PORT,
                              .pin = WINDOW_CONTACT_PIN };
  int32_t irq = SL_GPIO_INTERRUPT_UNAVAILABLE;
  sl_status_t irq_status = sl_gpio_configure_external_interrupt(&contact, &irq,
             SL_GPIO_INTERRUPT_RISING_FALLING_EDGE, contact_irq, NULL);
  assert(irq_status == SL_STATUS_OK);
  (void)irq_status;
  candidate_closed = read_closed();
#if WINDOW_CONTACT_USB_SENSE_ENABLED
  sl_zigbee_af_isr_event_init(&usb_edge_event, usb_edge_handler);
  sl_zigbee_af_event_init(&usb_sample_event, usb_sample_handler);
  GPIO_PinModeSet(WINDOW_CONTACT_USB_PORT, WINDOW_CONTACT_USB_PIN, gpioModeInput, 0);
  const sl_gpio_t usb = { .port = (sl_gpio_port_t)WINDOW_CONTACT_USB_PORT,
                          .pin = WINDOW_CONTACT_USB_PIN };
  irq = SL_GPIO_INTERRUPT_UNAVAILABLE;
  irq_status = sl_gpio_configure_external_interrupt(&usb, &irq,
             SL_GPIO_INTERRUPT_RISING_FALLING_EDGE, usb_irq, NULL);
  assert(irq_status == SL_STATUS_OK);
  window_contact_power_set_usb(GPIO_PinInGet(WINDOW_CONTACT_USB_PORT,
                                           WINDOW_CONTACT_USB_PIN) != 0);
#else
  window_contact_power_set_usb(false);
#endif
  window_contact_battery_init();
  events_ready = true;
  sl_zigbee_af_event_set_delay_ms(&sample_event, WINDOW_CONTACT_STARTUP_MS);
  sl_zigbee_af_event_set_delay_ms(&join_event, WINDOW_CONTACT_STARTUP_MS);
  sl_zigbee_af_event_set_delay_ms(&heartbeat_event, WINDOW_CONTACT_HEARTBEAT_MS);
}

void sl_zigbee_af_stack_status_cb(sl_status_t status)
{
  if (!events_ready) {
    return;
  }
  if (status == SL_STATUS_NETWORK_UP) {
    retry_ms = WINDOW_CONTACT_JOIN_RETRY_MS;
    sl_zigbee_af_event_set_inactive(&join_event);
    sl_zigbee_af_event_set_delay_ms(&sync_event, WINDOW_CONTACT_DEBOUNCE_MS);
  } else if (status == SL_STATUS_NETWORK_DOWN
             && !sl_zigbee_af_event_is_scheduled(&join_event)) {
    schedule_retry();
  }
}

void sl_zigbee_af_post_attribute_change_cb(uint8_t endpoint,
                                          sl_zigbee_af_cluster_id_t cluster,
                                          sl_zigbee_af_attribute_id_t attribute,
                                          uint8_t mask, uint16_t manufacturer,
                                          uint8_t type, uint8_t size, uint8_t *value)
{
  (void)manufacturer; (void)type; (void)size; (void)value;
  // Enrollment updates multiple attributes; allow the SDK to finish binding
  // and assigning the zone ID before sending our current physical state.
  if (events_ready && endpoint == WINDOW_CONTACT_ENDPOINT
      && cluster == ZCL_IAS_ZONE_CLUSTER_ID && (mask & CLUSTER_MASK_SERVER)
      && (attribute == ZCL_ZONE_STATE_ATTRIBUTE_ID || attribute == ZCL_ZONE_ID_ATTRIBUTE_ID)) {
    sl_zigbee_af_event_set_delay_ms(&sync_event, WINDOW_CONTACT_DEBOUNCE_MS);
  }
}

void sl_zigbee_af_network_steering_complete_cb(sl_status_t status,
                                             uint8_t totalBeacons,
                                             uint8_t joinAttempts,
                                             uint8_t finalState)
{
  (void)totalBeacons; (void)joinAttempts; (void)finalState;
  if (status != SL_STATUS_OK) {
    schedule_retry();
  }
}

void sl_zigbee_af_radio_needs_calibrating_cb(void)
{
  sl_mac_calibrate_current_channel();
}
