#ifndef IMAGE_DEFINES_H
#define IMAGE_DEFINES_H

#include <stdint.h>
#include <ap_int.h>

typedef ap_uint<512> uint512_t;
typedef uint8_t pixel_t;

// Image dimensions
#define HEIGHT 256
#define WIDTH  256 
#define IMAGE_SIZE (HEIGHT * WIDTH)

// Data width and pixel size for memory calculations
#define DATA_WIDTH_BITS     512                                 // Width of memory bus in bits
#define PIXEL_SIZE_BITS     8                                   // Size of each pixel in bits
#define PIXELS_PER_CHUNK    (DATA_WIDTH_BITS / PIXEL_SIZE_BITS) // 512/8 = 64 pixels per chunk

// Calculate padded width for memory allocation
// Number of 512-bit chunks per row
#define CHUNKS_PER_ROW ((WIDTH + PIXELS_PER_CHUNK - 1) / PIXELS_PER_CHUNK) // equivalent to ceil(WIDTH / PIXELS_PER_CHUNK)
// Padded stride in pixels
#define PADDED_WIDTH  (CHUNKS_PER_ROW * PIXELS_PER_CHUNK)
// Padded image size in pixels
#define PADDED_IMAGE_SIZE (HEIGHT * PADDED_WIDTH )
// Total chunks including padding
#define TOTAL_CHUNKS (CHUNKS_PER_ROW * HEIGHT)
// Buffer size for padded data
#define BUFFER_SIZE_BYTES (TOTAL_CHUNKS * PIXELS_PER_CHUNK)

// Threshold values
#define THRESH_LOW 32
#define THRESH_HIGH 96

#endif
