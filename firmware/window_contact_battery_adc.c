// XIAO MG24 switched 10k/10k divider: PD3 enable, PD4 ADC input.
#include "window_contact_battery.h"
#include "window_contact_config.h"
#include "em_cmu.h"
#include "em_gpio.h"
#include "em_iadc.h"
#include "sl_udelay.h"

uint16_t window_contact_battery_measure_mv(void)
{
  uint32_t sum = 0;
  bool valid = true;
  CMU_ClockEnable(cmuClock_GPIO, true);
  GPIO_PinModeSet(gpioPortD, 4, gpioModeDisabled, 0);
  GPIO_PinModeSet(gpioPortD, 3, gpioModePushPull, 1);
  sl_udelay_wait(2000);
  CMU_ClockSelectSet(cmuClock_IADCCLK, cmuSelect_FSRCO);
  CMU_ClockEnable(cmuClock_IADC0, true);
  IADC_reset(IADC0);
  // This application exclusively owns IADC0; preserve other analog bus users.
  uint32_t bus = GPIO->CDBUSALLOC;
  GPIO->CDBUSALLOC = (bus & ~_GPIO_CDBUSALLOC_CDEVEN0_MASK)
                    | GPIO_CDBUSALLOC_CDEVEN0_ADC0;
  IADC_Init_t init = IADC_INIT_DEFAULT;
  IADC_AllConfigs_t configs = IADC_ALLCONFIGS_DEFAULT;
  IADC_InitSingle_t single = IADC_INITSINGLE_DEFAULT;
  IADC_SingleInput_t input = IADC_SINGLEINPUT_DEFAULT;
  init.srcClkPrescale = IADC_calcSrcClkPrescale(IADC0, 2000000, 0);
  init.warmup = iadcWarmupNormal;
  configs.configs[0].reference = iadcCfgReferenceInt1V2;
  configs.configs[0].vRef = 1210;
  configs.configs[0].analogGain = iadcCfgAnalogGain0P5x;
  configs.configs[0].adcClkPrescale = IADC_calcAdcClkPrescale(
    IADC0, 1000000, 0, iadcCfgModeNormal, init.srcClkPrescale);
  input.posInput = iadcPosInputPortDPin4;
  input.negInput = iadcNegInputGnd;
  IADC_init(IADC0, &init, &configs);
  IADC_initSingle(IADC0, &single, &input);
  // Discard the first sample; average the following eight. Bound the waits so
  // an ADC failure cannot leave the divider powered or hang normal operation.
  for (unsigned i = 0; i < 9; i++) {
    IADC_command(IADC0, iadcCmdStartSingle);
    unsigned wait;
    for (wait = 0; wait < 2000 && IADC_getSingleFifoCnt(IADC0) == 0; wait++) {
      sl_udelay_wait(1);
    }
    if (wait == 2000) {
      valid = false;
      break;
    }
    uint32_t raw = IADC_pullSingleFifoResult(IADC0).data;
    if (i != 0) {
      sum += raw;
    }
  }
  IADC_reset(IADC0);
  CMU_ClockEnable(cmuClock_IADC0, false);
  GPIO->CDBUSALLOC = bus;
  GPIO_PinOutClear(gpioPortD, 3);
  if (!valid) {
    return 0;
  }
  // Internal 1.21V reference / gain 0.5, times the board's 2:1 divider.
  uint32_t mv = (sum * 4840U + 8U * 4095U / 2U) / (8U * 4095U);
  mv = mv * WINDOW_CONTACT_BATTERY_CALIBRATION_PERMILLE / 1000U;
  return (mv >= 2500 && mv <= 4350) ? (uint16_t)mv : 0;
}
