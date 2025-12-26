/**
 * @file accelerated_v1.cpp
 * @brief V1 - HW-accelerated image difference + posterization + sharpen filter.
 *
 * ============================================================================
 * ARCHITECTURE OVERVIEW
 * ============================================================================
 * This implementation uses a SEQUENTIAL THREE-STAGE PIPELINE:
 *   Stage 1: Read input images A/B, compute absolute difference, posterize -> C_tmp
 *   Stage 2: Apply 3x3 sharpen filter on C_tmp -> C_filt
 *   Stage 3: Pack C_filt into 512-bit words and write to output C
 *
 * KEY DESIGN CHOICE: Full-frame local buffers (no streaming)
 * - Simpler to implement and debug
 * - Requires more BRAM resources
 * - Stages execute sequentially (not overlapped)
 *
 * ============================================================================
 * MEMORY ACCESS PATTERN
 * ============================================================================
 * Uses 512-bit wide AXI master interfaces for efficient DDR access.
 * Each 512-bit word contains 64 pixels (64 x 8-bit = 512-bit).
 *
 * Sharpen kernel (Laplacian-based):
 *   [ 0 -1  0 ]
 *   [-1  5 -1 ]    -> Enhances edges by subtracting neighbors from center
 *   [ 0 -1  0 ]
 */

#include "../../inc/image_defines.h"

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

/**
 * @brief Posterize a pixel value into 3 discrete levels.
 */
static inline uint8_t posterize(uint8_t abs_diff)
{
#pragma HLS INLINE
    return (uint8_t)((abs_diff < THRESH_LOW) ? 0 : (abs_diff < THRESH_HIGH) ? 128 : 255);
}

/**
 * @brief Clip an integer value to valid 8-bit unsigned range [0, 255].
 */
static inline uint8_t clip_u8(int x)
{
#pragma HLS INLINE
    return (uint8_t)(x < 0 ? 0 : (x > 255 ? 255 : x));
}

extern "C" {

/**
 * @brief Top-level HLS kernel for image difference, posterization, and sharpening.
 *
 * @param A Input image A as array of 512-bit words (64 pixels per word)
 * @param B Input image B as array of 512-bit words (64 pixels per word)
 * @param C Output image as array of 512-bit words (64 pixels per word)
 */
void IMAGE_DIFF_POSTERIZE(const uint512_t *A, const uint512_t *B, uint512_t *C)
{
    // ========================================================================
    // AXI INTERFACE PRAGMAS
    // ========================================================================
#pragma HLS INTERFACE m_axi port=A offset=slave bundle=gmemA depth=TOTAL_CHUNKS
#pragma HLS INTERFACE m_axi port=B offset=slave bundle=gmemB depth=TOTAL_CHUNKS
#pragma HLS INTERFACE m_axi port=C offset=slave bundle=gmemC depth=TOTAL_CHUNKS
#pragma HLS INTERFACE s_axilite port=A bundle=control
#pragma HLS INTERFACE s_axilite port=B bundle=control
#pragma HLS INTERFACE s_axilite port=C bundle=control
#pragma HLS INTERFACE s_axilite port=return bundle=control

    // ========================================================================
    // LOCAL BUFFERS (BRAM)
    // ========================================================================
    static pixel_t C_tmp[HEIGHT][PADDED_WIDTH ];
    static pixel_t C_filt[HEIGHT][PADDED_WIDTH ];

    // ARRAY PARTITIONING for filter stage
#pragma HLS ARRAY_PARTITION variable=C_tmp cyclic factor=3 dim=1
#pragma HLS ARRAY_PARTITION variable=C_tmp cyclic factor=PIXELS_PER_CHUNK dim=2
#pragma HLS ARRAY_PARTITION variable=C_filt cyclic factor=PIXELS_PER_CHUNK dim=2

    // ========================================================================
    // STAGE 1: POSTERIZED ABSOLUTE DIFFERENCE
    // ========================================================================
Posterize_Main_Loop:
    for (int chunk_idx = 0; chunk_idx < TOTAL_CHUNKS; chunk_idx++)
    {
#pragma HLS PIPELINE II=1
#pragma HLS LOOP_TRIPCOUNT min=TOTAL_CHUNKS max=TOTAL_CHUNKS

        const uint512_t chunk_A = A[chunk_idx];
        const uint512_t chunk_B = B[chunk_idx];

    Posterize_Process_Loop:
        for (int k = 0; k < PIXELS_PER_CHUNK; k++)
        {
#pragma HLS UNROLL

            const pixel_t pA = chunk_A.range((k * 8) + 7, k * 8);
            const pixel_t pB = chunk_B.range((k * 8) + 7, k * 8);

            const pixel_t abs_diff = (pA > pB) ? (pA - pB) : (pB - pA);
            const pixel_t post = posterize(abs_diff);

            const int row = chunk_idx / CHUNKS_PER_ROW;
            const int col = (chunk_idx % CHUNKS_PER_ROW) * PIXELS_PER_CHUNK + k;

            C_tmp[row][col] = post;
        }
    }

    // ========================================================================
    // STAGE 2: 3×3 SHARPEN FILTER
    // ========================================================================
Filter_Row:
    for (int i = 0; i < HEIGHT; i++)
    {
#pragma HLS LOOP_TRIPCOUNT min=HEIGHT max=HEIGHT
    Filter_Col:
        for (int j = 0; j < WIDTH; j++)
        {
#pragma HLS PIPELINE II=1
#pragma HLS LOOP_TRIPCOUNT min=WIDTH max=WIDTH

            if (i == 0 || j == 0 || i == HEIGHT - 1 || j == WIDTH - 1)
            {
                C_filt[i][j] = 0;
            }
            else
            {
                const int center = (int)C_tmp[i][j];
                const int north  = (int)C_tmp[i - 1][j];
                const int south  = (int)C_tmp[i + 1][j];
                const int west   = (int)C_tmp[i][j - 1];
                const int east   = (int)C_tmp[i][j + 1];

                const int s = 5 * center - north - south - west - east;
                C_filt[i][j] = clip_u8(s);
            }
        }
    }

    // ========================================================================
    // STAGE 3: PACK AND WRITE OUTPUT
    // ========================================================================
Pack_Main_Loop:
    for (int chunk_idx = 0; chunk_idx < TOTAL_CHUNKS; chunk_idx++)
    {
#pragma HLS PIPELINE II=1
#pragma HLS LOOP_TRIPCOUNT min=TOTAL_CHUNKS max=TOTAL_CHUNKS

        uint512_t chunk_C = 0;

        const int row = chunk_idx / CHUNKS_PER_ROW;
        const int col_base = (chunk_idx % CHUNKS_PER_ROW) * PIXELS_PER_CHUNK;

    Pack_Process_Loop:
        for (int k = 0; k < PIXELS_PER_CHUNK; k++)
        {
#pragma HLS UNROLL

            const int col = col_base + k;
            const pixel_t v = C_filt[row][col];

            chunk_C.range((k * 8) + 7, k * 8) = v;
        }

        C[chunk_idx] = chunk_C;
    }
}

} // extern "C"
