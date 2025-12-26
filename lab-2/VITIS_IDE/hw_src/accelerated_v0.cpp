/**
 * @file accelerated_v0.cpp
 * @brief V0 (safe) HW-accelerated image difference + posterization + sharpen filter.
 *
 * No streams. Uses full-frame local buffers.
 *
 * Border policy (must match SW/TB):
 *   FINAL output border pixels are set to 0.
 *
 * Sharpen kernel:
 *   [ 0 -1  0
 *    -1  5 -1
 *     0 -1  0 ]
 *
 * Stages:
 *   1) Read A/B in 512-bit chunks, abs diff + posterize -> C_tmp
 *   2) Full-frame 3x3 sharpen on C_tmp -> C_filt with clipping
 *   3) Pack C_filt into 512-bit words -> write C
 */

#include "../../inc/image_defines.h"

// Number of 512-bit chunks (for non-padded layout)
#define CHUNK_COUNT (IMAGE_SIZE / PIXELS_PER_CHUNK)

static inline uint8_t posterize(uint8_t abs_diff)
{
    #pragma HLS INLINE
    return (uint8_t) ((abs_diff < THRESH_LOW) ? 0 : (abs_diff < THRESH_HIGH) ? 128 : 255);
}

static inline uint8_t clip_u8(int x)
{
    #pragma HLS INLINE
    return (uint8_t) (x < 0 ? 0 : (x > 255 ? 255 : x));
}

extern "C" {

void IMAGE_DIFF_POSTERIZE(
    const uint512_t *A,  // Read-Only Image A
    const uint512_t *B,  // Read-Only Image B
    uint512_t *C         // Output Result
)
{
// AXI Master interfaces for memory access (each array from different bundle)
#pragma HLS INTERFACE m_axi port=A offset=slave bundle=gmemA depth=CHUNK_COUNT
#pragma HLS INTERFACE m_axi port=B offset=slave bundle=gmemB depth=CHUNK_COUNT
#pragma HLS INTERFACE m_axi port=C offset=slave bundle=gmemC depth=CHUNK_COUNT

// AXI Lite interface for control
#pragma HLS INTERFACE s_axilite port=A bundle=control
#pragma HLS INTERFACE s_axilite port=B bundle=control
#pragma HLS INTERFACE s_axilite port=C bundle=control
#pragma HLS INTERFACE s_axilite port=return bundle=control

    // Full-frame local buffers
    static uint8_t C_tmp[IMAGE_SIZE];
    static uint8_t C_filt[IMAGE_SIZE];

    // Storage binding for BRAM
#pragma HLS bind_storage variable=C_tmp  type=ram_2p impl=bram
#pragma HLS bind_storage variable=C_filt type=ram_2p impl=bram

    // ------------------------------------------------------------
    // Stage 1: posterized absolute difference -> C_tmp
    // ------------------------------------------------------------
    Posterize_Main_Loop:
    for (int chunk_idx = 0; chunk_idx < CHUNK_COUNT; chunk_idx++)
    {
#pragma HLS PIPELINE II=1
#pragma HLS LOOP_TRIPCOUNT min=CHUNK_COUNT max=CHUNK_COUNT

        const uint512_t chunk_A = A[chunk_idx];
        const uint512_t chunk_B = B[chunk_idx];

        Posterize_Process_Loop:
        for (int k = 0; k < PIXELS_PER_CHUNK; k++)
        {
#pragma HLS UNROLL

            const uint8_t pA = chunk_A.range((k * 8) + 7, k * 8);
            const uint8_t pB = chunk_B.range((k * 8) + 7, k * 8);

            const uint8_t abs_diff = (pA > pB) ? (pA - pB) : (pB - pA);
            const uint8_t post = posterize(abs_diff);

            const int idx = (chunk_idx * PIXELS_PER_CHUNK) + k;
            C_tmp[idx] = post;
        }
    }

    // ------------------------------------------------------------
    // Stage 2: 3x3 sharpen filter -> C_filt
    // ------------------------------------------------------------
    Filter_Row:
    for (int i = 0; i < HEIGHT; i++)
    {
#pragma HLS LOOP_TRIPCOUNT min=HEIGHT max=HEIGHT
        Filter_Col:
        for (int j = 0; j < WIDTH; j++)
        {
#pragma HLS LOOP_TRIPCOUNT min=WIDTH max=WIDTH

            const int idx = i * WIDTH + j;

            // Border policy: Zero
            if (i == 0 || j == 0 || i == HEIGHT - 1 || j == WIDTH - 1)
            {
                C_filt[idx] = 0;
            }
            else
            {
                const uint8_t center = C_tmp[idx];
                const uint8_t north  = C_tmp[idx - WIDTH];
                const uint8_t south  = C_tmp[idx + WIDTH];
                const uint8_t west   = C_tmp[idx - 1];
                const uint8_t east   = C_tmp[idx + 1];

                const int s = 5 * center - north - south - west - east;
                C_filt[idx] = clip_u8(s);
            }
        }
    }

    // ------------------------------------------------------------
    // Stage 3: pack C_filt into 512-bit output
    // ------------------------------------------------------------
    Pack_Main_Loop:
    for (int chunk_idx = 0; chunk_idx < CHUNK_COUNT; chunk_idx++)
    {
#pragma HLS PIPELINE II=1
#pragma HLS LOOP_TRIPCOUNT min=CHUNK_COUNT max=CHUNK_COUNT

        uint512_t chunk_C = 0;

        Pack_Process_Loop:
        for (int k = 0; k < PIXELS_PER_CHUNK; k++)
        {
#pragma HLS UNROLL

            const int idx = (chunk_idx * PIXELS_PER_CHUNK) + k;
            const uint8_t v = C_filt[idx];

            chunk_C.range((k * 8) + 7, k * 8) = v;
        }

        C[chunk_idx] = chunk_C;
    }
}

} // extern "C"

// ============================================================================
// WHY USE INTERMEDIATE BUFFERS INSTEAD OF WRITING DIRECTLY TO ARRAY C?
//
// The output pointer C represents external DDR memory accessed via AXI master
// interface (m_axi). DDR access requires 512-bit burst transactions (64 pixels
// at a time) - you CANNOT write individual pixels directly to C.
//
// The sharpen filter (Stage 2) computes ONE PIXEL AT A TIME. If we tried to
// write directly to C, we'd need expensive read-modify-write cycles for each
// pixel, destroying memory bandwidth and causing data hazards.
//
// SOLUTION: Buffer-Then-Pack Strategy
//   - C_tmp/C_filt are on-chip BRAM -> fast random-access, single-pixel writes
//   - Stage 3 packs 64 pixels into 512-bit chunks for efficient DDR bursts
//
// This transforms random single-pixel writes into sequential 512-bit writes.
// ============================================================================
