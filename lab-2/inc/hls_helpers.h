/**
 * @file hls_helpers.h
 * @brief Common helper functions for HLS image processing kernels.
 */

#ifndef HLS_HELPERS_H
#define HLS_HELPERS_H

#include "image_defines.h"

/**
 * @brief Posterize a pixel value into 3 discrete levels.
 *
 * Maps continuous grayscale values to discrete bins:
 *   - [0, THRESH_LOW)        -> 0   (black)
 *   - [THRESH_LOW, THRESH_HIGH) -> 128 (gray)
 *   - [THRESH_HIGH, 255]     -> 255 (white)
 *
 * @param abs_diff The absolute difference value to posterize
 * @return Posterized pixel value (0, 128, or 255)
 */
static inline uint8_t posterize(uint8_t abs_diff)
{
#pragma HLS INLINE
    return (uint8_t) ((abs_diff < THRESH_LOW) ? 0 : (abs_diff < THRESH_HIGH) ? 128 : 255);
}

/**
 * @brief Clip an integer value to valid 8-bit unsigned range [0, 255].
 *
 * Essential after filter operations that can produce values outside [0, 255].
 *
 * @param x Input integer (may be negative or > 255)
 * @return Clipped value in range [0, 255]
 */
static inline uint8_t clip_u8(int x)
{
#pragma HLS INLINE
    return (uint8_t) (x < 0 ? 0 : (x > 255 ? 255 : x));
}

#endif // HLS_HELPERS_H
