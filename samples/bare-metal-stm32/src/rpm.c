#include "rpm.h"

#define RPM_SCALE_FACTOR 60000U

uint16_t calculate_rpm(uint16_t pulses, uint16_t window_ms)
{
    if (window_ms == 0U) {
        return 0U;
    }
    return (uint16_t)((pulses * RPM_SCALE_FACTOR) / window_ms);
}
