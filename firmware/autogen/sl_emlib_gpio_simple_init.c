#include "sl_emlib_gpio_simple_init.h"
#include "sl_emlib_gpio_init_rf_power_config.h"
#include "sl_emlib_gpio_init_rf_select_config.h"
#include "em_gpio.h"
#include "em_cmu.h"

void sl_emlib_gpio_simple_init(void)
{
  CMU_ClockEnable(cmuClock_GPIO, true);
  GPIO_PinModeSet(SL_EMLIB_GPIO_INIT_RF_POWER_PORT,
                  SL_EMLIB_GPIO_INIT_RF_POWER_PIN,
                  SL_EMLIB_GPIO_INIT_RF_POWER_MODE,
                  SL_EMLIB_GPIO_INIT_RF_POWER_DOUT);

  GPIO_PinModeSet(SL_EMLIB_GPIO_INIT_RF_SELECT_PORT,
                  SL_EMLIB_GPIO_INIT_RF_SELECT_PIN,
                  SL_EMLIB_GPIO_INIT_RF_SELECT_MODE,
                  SL_EMLIB_GPIO_INIT_RF_SELECT_DOUT);
}
