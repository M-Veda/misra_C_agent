#include <stdint.h>

#include "rpm.h"

typedef uint16_t rpm_t;

static rpm_t g_last_rpm;

void app_update(uint16_t pulses, uint16_t window_ms)
{
    g_last_rpm = calculate_rpm(pulses, window_ms);
}

uint16_t app_get_last_rpm(void)
{
    return g_last_rpm;
}
