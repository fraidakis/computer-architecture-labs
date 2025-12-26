#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h> // Required for memcpy
#include "../inc/image_defines.h"

// Declaration of top-level HW function
extern "C" void IMAGE_DIFF_POSTERIZE(const uint512_t *A, const uint512_t *B, uint512_t *C);

// -----------------------------------------------------------------------------
// Fast Data Movement (Replaces slow loops with memcpy)
// -----------------------------------------------------------------------------

// Pack pixels: Copies valid rows from 'logical' buffer to 'padded' 512-bit chunks
static void pack_pixels_fast(const pixel_t *logical_pixels, uint512_t *hw_chunks)
{
    // 1. Cast the HW buffer to bytes for easy addressing
    pixel_t *raw_hw_ptr = (pixel_t*)hw_chunks;

    // 2. Zero out the entire buffer first (handles all padding automatically)
    //    sizeof(uint512_t) is 64 bytes
    memset(raw_hw_ptr, 0, TOTAL_CHUNKS * PIXELS_PER_CHUNK);

    // 3. Copy row-by-row
    for (int r = 0; r < HEIGHT; r++)
    {
        // Source: Logical buffer (packed, no stride)
        const pixel_t *src_row = &logical_pixels[r * WIDTH];
        
        // Dest: HW buffer (strided)
        pixel_t *dst_row = &raw_hw_ptr[r * PADDED_WIDTH ];

        // Fast block copy
        memcpy(dst_row, src_row, WIDTH);
    }
}

// Unpack pixels: Copies valid rows from 'padded' 512-bit chunks to 'logical' buffer
static void unpack_pixels_fast(const uint512_t *hw_chunks, pixel_t *logical_pixels)
{
    const pixel_t *raw_hw_ptr = (const pixel_t*)hw_chunks;

    for (int r = 0; r < HEIGHT; r++)
    {
        // Source: HW buffer (strided)
        const pixel_t *src_row = &raw_hw_ptr[r * PADDED_WIDTH ];

        // Dest: Logical buffer
        pixel_t *dst_row = &logical_pixels[r * WIDTH];

        memcpy(dst_row, src_row, WIDTH);
    }
}

// -----------------------------------------------------------------------------
// Software reference
// -----------------------------------------------------------------------------

// Simplified SW Reference acting on Logical Buffers (Faster/Cleaner)
void sw_reference_logical(const pixel_t *A, const pixel_t *B, pixel_t *C_ref)
{
    // Intermediate buffer
    static pixel_t P[WIDTH * HEIGHT];

    for (int i = 0; i < WIDTH * HEIGHT; i++) {
        int diff = (int)A[i] - (int)B[i];
        if (diff < 0) diff = -diff;
        P[i] = (diff < THRESH_LOW) ? 0 : (diff < THRESH_HIGH) ? 128 : 255;
    }

    for (int r = 0; r < HEIGHT; r++) {
        for (int c = 0; c < WIDTH; c++) {
            int idx = r * WIDTH + c;
            if (r == 0 || r == HEIGHT-1 || c == 0 || c == WIDTH-1) {
                C_ref[idx] = 0;
            } else {
                int val = 5 * P[idx] 
                        - P[idx - WIDTH] - P[idx + WIDTH] 
                        - P[idx - 1]     - P[idx + 1];
                if (val < 0) val = 0;
                if (val > 255) val = 255;
                C_ref[idx] = (pixel_t)val;
            }
        }
    }
}

int main()
{
    // 1. Static Allocation
    static pixel_t img_A[WIDTH * HEIGHT];
    static pixel_t img_B[WIDTH * HEIGHT];
    static pixel_t img_C_SW[WIDTH * HEIGHT];
    static pixel_t img_C_HW_Unpacked[WIDTH * HEIGHT]; // Logical result from HW

    static uint512_t hw_A[TOTAL_CHUNKS];
    static uint512_t hw_B[TOTAL_CHUNKS];
    static uint512_t hw_C[TOTAL_CHUNKS];

    printf("Starting Fast Testbench (Size: %dx%d)\n", WIDTH, HEIGHT);

    // 2. Input Generation (Logical)
    srand(42);
    for (int i = 0; i < WIDTH * HEIGHT; i++) {
        img_A[i] = rand() % 256;
        int noise = (rand() % 200) - 100;
        int temp = img_A[i] + noise;
        if (temp < 0) temp = 0; else if (temp > 255) temp = 255;
        img_B[i] = (pixel_t)temp;
    }

    // 3. SW Reference (Logical)
    sw_reference_logical(img_A, img_B, img_C_SW);

    // 4. Pack HW Inputs (Fast)
    pack_pixels_fast(img_A, hw_A);
    pack_pixels_fast(img_B, hw_B);

    // 5. Run HW
    IMAGE_DIFF_POSTERIZE(hw_A, hw_B, hw_C);

    // 6. Unpack HW Output (Fast)
    unpack_pixels_fast(hw_C, img_C_HW_Unpacked);

    // 7. Verify (Logical)
    int error_count = 0;
    for (int i = 0; i < WIDTH * HEIGHT; i++) {
        if (img_C_HW_Unpacked[i] != img_C_SW[i]) {
            printf("Error at pixel %d: HW=%d SW=%d\n", i, img_C_HW_Unpacked[i], img_C_SW[i]);
            error_count++;
            if (error_count > 10) break;
        }
    }

    if (error_count == 0) printf("TEST PASSED.\n");
    else printf("TEST FAILED.\n");

    return (error_count == 0) ? 0 : 1;
}
