#ifndef IMAGE_DEFINES_H
#define IMAGE_DEFINES_H

#include <stdint.h>
#include <ap_int.h> // Xilinx arbitrary precision integer header

// Define a 512-bit wide type to match the hardware bus
typedef ap_uint<512> uint512_t;

// Pixel data type (8-bit unsigned)
typedef uint8_t pixel_t;

// Image Dimensions (e.g., 256x256)
#define HEIGHT 256
#define WIDTH 256
#define IMAGE_SIZE (WIDTH * HEIGHT)

// Thresholds
#define THRESH_LOW 32
#define THRESH_HIGH 96

#endif
