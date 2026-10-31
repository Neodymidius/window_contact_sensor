#include "window_contact_battery.h"
#include "window_contact_config.h"
#include "app/framework/include/af.h"
#include "ias-zone-server.h"

static sl_zigbee_af_event_t battery_event;

uint8_t window_contact_battery_percent(uint16_t mv)
{
  // Approximate resting-voltage curve for a single 4.2V LiPo cell. Units are
  // 0.5%, as required by ZCL, not integer percent. This is not a fuel gauge.
  static const struct { uint16_t mv; uint8_t half_percent; } curve[] = {
    { 3000, 0 }, { 3300, 4 }, { 3500, 10 }, { 3600, 20 },
    { 3700, 40 }, { 3750, 60 }, { 3800, 80 }, { 3850, 100 },
    { 3900, 120 }, { 4000, 160 }, { 4100, 180 }, { 4200, 200 }
  };
  if (mv < 2500 || mv > 4350) {
    return 0xFF;
  }
  if (mv <= curve[0].mv) {
    return 0;
  }
  for (unsigned i = 1; i < sizeof(curve) / sizeof(curve[0]); i++) {
    if (mv < curve[i].mv) {
      uint32_t span = curve[i].mv - curve[i-1].mv;
      return curve[i-1].half_percent
             + ((mv - curve[i-1].mv) * (curve[i].half_percent - curve[i-1].half_percent)
                + span / 2) / span;
    }
  }
  return 200;
}

static void ensure_binding(void)
{
  // IAS enrollment identifies the actual CIE endpoint. Reuse it for battery
  // reports if the coordinator has not already bound Power Configuration.
  sl_zigbee_binding_table_entry_t cie;
  bool found = false;
  uint8_t free_slot = 0xFF;
  for (uint8_t i = 0; i < SL_ZIGBEE_BINDING_TABLE_SIZE; i++) {
    sl_zigbee_binding_table_entry_t entry;
    if (sl_zigbee_get_binding(i, &entry) != SL_STATUS_OK) {
      continue;
    }
    if (entry.type == SL_ZIGBEE_UNUSED_BINDING && free_slot == 0xFF) {
      free_slot = i;
    }
    if (entry.local != WINDOW_CONTACT_ENDPOINT || entry.type != SL_ZIGBEE_UNICAST_BINDING) {
      continue;
    }
    if (entry.clusterId == ZCL_POWER_CONFIG_CLUSTER_ID) {
      return; // Respect an existing coordinator-configured destination.
    }
    if (entry.clusterId == ZCL_IAS_ZONE_CLUSTER_ID) {
      cie = entry;
      found = true;
    }
  }
  if (found && free_slot != 0xFF) {
    cie.clusterId = ZCL_POWER_CONFIG_CLUSTER_ID;
    (void)sl_zigbee_set_binding(free_slot, &cie);
  }
}

static void battery_handler(sl_zigbee_af_event_t *event)
{
  uint16_t mv = window_contact_battery_measure_mv();
  uint8_t voltage = mv ? (uint8_t)((mv + 50U) / 100U) : 0xFF;
  uint8_t percentage = window_contact_battery_percent(mv);
  if (sl_zigbee_af_network_state() == SL_ZIGBEE_JOINED_NETWORK
      && sl_zigbee_af_ias_zone_cluster_am_i_enrolled(WINDOW_CONTACT_ENDPOINT)) {
    ensure_binding();
  }
  // The SDK reporting component handles configured intervals, changes and
  // bound destinations. Invalid samples explicitly replace stale readings.
  (void)sl_zigbee_af_write_server_attribute(WINDOW_CONTACT_ENDPOINT,
    ZCL_POWER_CONFIG_CLUSTER_ID, ZCL_BATTERY_VOLTAGE_ATTRIBUTE_ID,
    &voltage, ZCL_INT8U_ATTRIBUTE_TYPE);
  (void)sl_zigbee_af_write_server_attribute(WINDOW_CONTACT_ENDPOINT,
    ZCL_POWER_CONFIG_CLUSTER_ID, ZCL_BATTERY_PERCENTAGE_REMAINING_ATTRIBUTE_ID,
    &percentage, ZCL_INT8U_ATTRIBUTE_TYPE);
  sl_zigbee_af_event_set_delay_ms(event, WINDOW_CONTACT_HEARTBEAT_MS);
}

void window_contact_battery_request(void)
{
  sl_zigbee_af_event_set_delay_ms(&battery_event, 1000);
}

void window_contact_battery_init(void)
{
  sl_zigbee_af_event_init(&battery_event, battery_handler);
  window_contact_battery_request();
}
