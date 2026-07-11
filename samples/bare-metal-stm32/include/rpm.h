#ifndef STM32_SAMPLE_RPM_H
#define STM32_SAMPLE_RPM_H

#include <stdint.h>

uint16_t calculate_rpm(uint16_t pulses, uint16_t window_ms);

#endif
