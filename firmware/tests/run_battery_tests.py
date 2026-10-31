#!/usr/bin/env python3
"""Test the real ADC cleanup, LiPo mapping, ZCL units and binding behavior."""
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
ROOT=Path(__file__).resolve().parents[1]
STUB=r'''
#ifndef BATTERY_STUB_H
#define BATTERY_STUB_H
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#define gpioPortD 3
#define gpioModeDisabled 0
#define gpioModePushPull 1
#define cmuClock_GPIO 0
#define cmuClock_IADC0 1
#define cmuClock_IADCCLK 2
#define cmuSelect_FSRCO 1
#define GPIO_CDBUSALLOC_CDEVEN0_ADC0 1
#define _GPIO_CDBUSALLOC_CDEVEN0_MASK 15
#define iadcWarmupNormal 0
#define iadcCfgReferenceInt1V2 1
#define iadcCfgAnalogGain0P5x 1
#define iadcCfgModeNormal 0
#define iadcPosInputPortDPin4 4
#define iadcNegInputGnd 0
#define iadcCmdStartSingle 1
#define IADC_INIT_DEFAULT {0}
#define IADC_ALLCONFIGS_DEFAULT {0}
#define IADC_INITSINGLE_DEFAULT {0}
#define IADC_SINGLEINPUT_DEFAULT {0}
typedef struct { unsigned srcClkPrescale,warmup; } IADC_Init_t;
typedef struct { struct {unsigned reference,vRef,analogGain,adcClkPrescale;} configs[1]; } IADC_AllConfigs_t;
typedef unsigned IADC_InitSingle_t;
typedef struct {unsigned posInput,negInput;} IADC_SingleInput_t;
typedef struct {uint32_t data;} IADC_Result_t;
static struct {uint32_t CDBUSALLOC;} gpio_regs;
#define GPIO (&gpio_regs)
#define IADC0 ((void*)1)
static bool divider,adc_clock,timeout;
static unsigned commands,pulls,raw=3215;
static void CMU_ClockEnable(unsigned clock,bool on) {if(clock==1)adc_clock=on;}
static void CMU_ClockSelectSet(unsigned clock,unsigned source){assert(clock==2&&source==1);}
static void GPIO_PinModeSet(unsigned port,unsigned pin,unsigned mode,unsigned level){assert(port==3);if(pin==3){assert(mode==1);divider=level;}else assert(pin==4&&mode==0);}
static void GPIO_PinOutClear(unsigned port,unsigned pin){assert(port==3&&pin==3);divider=false;}
static void sl_udelay_wait(unsigned us){(void)us;}
static void IADC_reset(void *adc){assert(adc==IADC0&&adc_clock);}
static unsigned IADC_calcSrcClkPrescale(void *adc,unsigned freq,unsigned src){(void)adc;(void)src;assert(freq==2000000);return 9;}
static unsigned IADC_calcAdcClkPrescale(void *adc,unsigned f,unsigned s,unsigned m,unsigned p){(void)adc;(void)f;(void)s;(void)m;(void)p;return 1;}
static void IADC_init(void *adc,const IADC_Init_t *init,const IADC_AllConfigs_t *cfg){(void)adc;assert(init->srcClkPrescale==9&&cfg->configs[0].vRef==1210&&cfg->configs[0].analogGain==1);}
static void IADC_initSingle(void *adc,const IADC_InitSingle_t *s,const IADC_SingleInput_t *in){(void)adc;(void)s;assert(in->posInput==4&&in->negInput==0);}
static void IADC_command(void *adc,unsigned cmd){(void)adc;assert(cmd==1&&divider&&adc_clock);commands++;}
static unsigned IADC_getSingleFifoCnt(void *adc){(void)adc;return timeout?0:1;}
static IADC_Result_t IADC_pullSingleFifoResult(void *adc){(void)adc;pulls++;IADC_Result_t r={pulls%9==1?4095:raw};return r;}
#define SL_STATUS_OK 0
#define SL_ZIGBEE_JOINED_NETWORK 1
#define SL_ZIGBEE_BINDING_TABLE_SIZE 3
#define SL_ZIGBEE_UNUSED_BINDING 0
#define SL_ZIGBEE_UNICAST_BINDING 1
#define ZCL_POWER_CONFIG_CLUSTER_ID 1
#define ZCL_IAS_ZONE_CLUSTER_ID 0x500
#define ZCL_BATTERY_VOLTAGE_ATTRIBUTE_ID 0x20
#define ZCL_BATTERY_PERCENTAGE_REMAINING_ATTRIBUTE_ID 0x21
#define ZCL_INT8U_ATTRIBUTE_TYPE 0x20
typedef struct {bool active;unsigned delay;} sl_zigbee_af_event_t;
typedef struct {unsigned type,local,remote,clusterId;uint8_t identifier[8];} sl_zigbee_binding_table_entry_t;
static sl_zigbee_binding_table_entry_t bindings[3];
static bool enrolled=true;
static unsigned network=1,writes;
static uint8_t voltage,percent;
static unsigned sl_zigbee_get_binding(unsigned i,sl_zigbee_binding_table_entry_t *out){*out=bindings[i];return 0;}
static unsigned sl_zigbee_set_binding(unsigned i,const sl_zigbee_binding_table_entry_t *in){bindings[i]=*in;writes++;return 0;}
static unsigned sl_zigbee_af_network_state(void){return network;}
static bool sl_zigbee_af_ias_zone_cluster_am_i_enrolled(unsigned ep){assert(ep==1);return enrolled;}
static void sl_zigbee_af_event_init(sl_zigbee_af_event_t *ev,void(*cb)(sl_zigbee_af_event_t*)){(void)cb;ev->active=false;}
static void sl_zigbee_af_event_set_delay_ms(sl_zigbee_af_event_t *ev,unsigned ms){ev->active=true;ev->delay=ms;}
static unsigned sl_zigbee_af_write_server_attribute(unsigned ep,unsigned cluster,unsigned attr,uint8_t *data,unsigned type){assert(ep==1&&cluster==1&&type==0x20);if(attr==0x20)voltage=*data;else {assert(attr==0x21);percent=*data;}return 0;}
#endif
'''
HARNESS=r'''
#include "window_contact_battery_adc.c"
#include "window_contact_battery.c"
int main(void){
 gpio_regs.CDBUSALLOC=0xAA000002;
 uint16_t mv=window_contact_battery_measure_mv();
 assert(mv>=3798&&mv<=3801&&commands==9&&pulls==9);
 assert(!divider&&!adc_clock&&gpio_regs.CDBUSALLOC==0xAA000002);
 timeout=true;assert(window_contact_battery_measure_mv()==0);
 assert(!divider&&!adc_clock&&gpio_regs.CDBUSALLOC==0xAA000002);
 timeout=false;raw=0;assert(window_contact_battery_measure_mv()==0);
 assert(!divider&&!adc_clock);
 assert(window_contact_battery_percent(0)==255);
 assert(window_contact_battery_percent(2499)==255);
 assert(window_contact_battery_percent(3000)==0);
 assert(window_contact_battery_percent(3800)==80);
 assert(window_contact_battery_percent(3850)==100);
 assert(window_contact_battery_percent(4200)==200);
 assert(window_contact_battery_percent(4350)==200);
 assert(window_contact_battery_percent(4351)==255);
 unsigned previous=0;
 for(unsigned v=2500;v<=4350;v++){unsigned p=window_contact_battery_percent(v);assert(p>=previous&&p<=200);previous=p;}
 raw=3215;
 bindings[0].type=1;bindings[0].local=1;bindings[0].remote=2;bindings[0].clusterId=0x500;
 bindings[0].identifier[0]=42;
 window_contact_battery_init();assert(battery_event.delay==1000);
 battery_handler(&battery_event);
 assert(voltage==38&&percent>=79&&percent<=80&&battery_event.delay==1800000);
 assert(writes==1&&bindings[1].clusterId==1&&bindings[1].remote==2&&bindings[1].identifier[0]==42);
 battery_handler(&battery_event);assert(writes==1);
 timeout=true;battery_handler(&battery_event);assert(voltage==255&&percent==255);
 assert(!divider&&!adc_clock);
 // Never overwrite a full binding table or manufacture a CIE destination.
 timeout=false;memset(bindings,0,sizeof(bindings));writes=0;
 ensure_binding();assert(writes==0);
 bindings[0].type=bindings[1].type=bindings[2].type=1;
 bindings[0].local=1;bindings[0].clusterId=0x500;
 ensure_binding();assert(writes==0);
 return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='window-battery-test-') as directory:
    tmp=Path(directory)
    for name in ('app/framework/include/af.h','em_cmu.h','em_gpio.h','em_iadc.h','sl_udelay.h','ias-zone-server.h'):
        header=tmp/name;header.parent.mkdir(parents=True,exist_ok=True);header.write_text('#include "stub.h"\n')
    (tmp/'stub.h').write_text(STUB);(tmp/'test.c').write_text(HARNESS)
    subprocess.run(shlex.split(os.environ.get('CC','cc'))+['-std=c99','-Wall','-Wextra','-Werror','-I',str(tmp),'-I',str(ROOT),'-I',str(ROOT/'config'),str(tmp/'test.c'),'-o',str(tmp/'test')],check=True)
    subprocess.run([str(tmp/'test')],check=True)
print('PASS: ADC averaging/timeout cleanup, percentage bounds, ZCL units, unknown values and binding preservation')
