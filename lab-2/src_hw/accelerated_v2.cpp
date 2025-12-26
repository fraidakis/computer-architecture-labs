///**
// * @file accelerated_v2.cpp
// * @brief V2 - HW-accelerated image difference + posterization + sharpen filter.
// *
// * ============================================================================
// * ARCHITECTURE OVERVIEW
// * ============================================================================
// * This implementation uses a SEQUENTIAL THREE-STAGE PIPELINE:
// *   Stage 1: Read 512-bit chunks from A/B, compute |A-B|, posterize -> C_tmp
// *   Stage 2: Apply 3x3 sharpen filter on C_tmp using line buffers -> C_filt
// *   Stage 3: Write filtered results from C_filt to output C
// *
// * KEY DESIGN FEATURES:
// * - 512-bit wide AXI interfaces (64 pixels per memory transaction)
// * - Full-width parallelism (64 pixels processed simultaneously)
// * - Sequential stage execution (stages do NOT overlap)
// * - Local BRAM buffers for intermediate storage
// *
// * ============================================================================
// * MEMORY ACCESS PATTERN
// * ============================================================================
// * Uses 512-bit wide AXI master interfaces for efficient DDR access.
// * Each 512-bit word contains 64 pixels (64 x 8-bit = 512-bit).
// *
// * Sharpen kernel (Laplacian-based):
// *   [ 0 -1  0 ]
// *   [-1  5 -1 ]    -> Enhances edges by subtracting neighbors from center
// *   [ 0 -1  0 ]
// */
//
//#include "../inc/hls_helpers.h"
//
//extern "C" {
//
///**
// * @brief Top-level HLS kernel for image difference, posterization, and sharpening.
// *
// * @param A Input image A as array of 512-bit words (64 pixels per word)
// * @param B Input image B as array of 512-bit words (64 pixels per word)
// * @param C Output image as array of 512-bit words (64 pixels per word)
// */
//void IMAGE_DIFF_POSTERIZE(const uint512_t *A, const uint512_t *B, uint512_t *C)
//{
//    // ========================================================================
//    // AXI INTERFACE PRAGMAS
//    // ========================================================================
//#pragma HLS INTERFACE m_axi port=A offset=slave bundle=gmemA depth=TOTAL_CHUNKS
//#pragma HLS INTERFACE m_axi port=B offset=slave bundle=gmemB depth=TOTAL_CHUNKS
//#pragma HLS INTERFACE m_axi port=C offset=slave bundle=gmemC depth=TOTAL_CHUNKS
//#pragma HLS INTERFACE s_axilite port=A bundle=control
//#pragma HLS INTERFACE s_axilite port=B bundle=control
//#pragma HLS INTERFACE s_axilite port=C bundle=control
//#pragma HLS INTERFACE s_axilite port=return bundle=control
//
//    // ========================================================================
//    // LOCAL BUFFERS (BRAM)
//    // ========================================================================
//    static uint512_t C_tmp[TOTAL_CHUNKS];
//    static uint512_t C_filt[TOTAL_CHUNKS];
//
//    // ========================================================================
//    // STAGE 1: POSTERIZED ABSOLUTE DIFFERENCE (64 pixels/cycle)
//    // ========================================================================
//Posterize_Loop:
//    for (int i = 0; i < TOTAL_CHUNKS; i++)
//    {
//#pragma HLS PIPELINE II=1
//#pragma HLS LOOP_TRIPCOUNT min=TOTAL_CHUNKS max=TOTAL_CHUNKS
//
//        uint512_t valA = A[i];
//        uint512_t valB = B[i];
//        uint512_t valC = 0;
//
//    Process_64_Pixels:
//        for (int k = 0; k < PIXELS_PER_CHUNK; k++)
//        {
//#pragma HLS UNROLL
//            int lo = k * 8;
//            int hi = lo + 7;
//            pixel_t pA = valA.range(hi, lo);
//            pixel_t pB = valB.range(hi, lo);
//
//            pixel_t diff = (pA > pB) ? (pA - pB) : (pB - pA);
//            valC.range(hi, lo) = posterize(diff);
//        }
//        C_tmp[i] = valC;
//    }
//
//    // ========================================================================
//    // STAGE 2: 3×3 SHARPEN FILTER (64 pixels/cycle with sliding window)
//    // ========================================================================
//    uint512_t lb[2][CHUNKS_PER_ROW];
//#pragma HLS ARRAY_PARTITION variable=lb complete dim=1
//
//    uint512_t win[3][3];
//#pragma HLS ARRAY_PARTITION variable=win complete dim=0
//
//Init_LB:
//    for (int c = 0; c < CHUNKS_PER_ROW; c++)
//    {
//#pragma HLS PIPELINE II=1
//        lb[0][c] = 0;
//        lb[1][c] = 0;
//    }
//
//Init_Win:
//    for (int r = 0; r < 3; r++)
//    {
//#pragma HLS UNROLL
//        for (int c = 0; c < 3; c++)
//            win[r][c] = 0;
//    }
//
//    const int LOOP_LIMIT = TOTAL_CHUNKS + CHUNKS_PER_ROW + 1;
//
//Filter_Loop:
//    for (int iter = 0; iter < LOOP_LIMIT; iter++)
//    {
//#pragma HLS PIPELINE II=1
//
//        uint512_t new_chunk = 0;
//        if (iter < TOTAL_CHUNKS)
//        {
//            new_chunk = C_tmp[iter];
//        }
//
//        for (int r = 0; r < 3; r++)
//        {
//#pragma HLS UNROLL
//            win[r][0] = win[r][1];
//            win[r][1] = win[r][2];
//        }
//
//        int col_idx = iter % CHUNKS_PER_ROW;
//
//        if (iter < TOTAL_CHUNKS)
//        {
//            win[0][2] = lb[0][col_idx];
//            win[1][2] = lb[1][col_idx];
//            win[2][2] = new_chunk;
//
//            lb[0][col_idx] = lb[1][col_idx];
//            lb[1][col_idx] = new_chunk;
//        }
//        else
//        {
//            win[0][2] = 0;
//            win[1][2] = 0;
//            win[2][2] = 0;
//        }
//
//        int out_idx = iter - (CHUNKS_PER_ROW + 1);
//
//        if (out_idx >= 0 && out_idx < TOTAL_CHUNKS)
//        {
//            int r_idx = out_idx / CHUNKS_PER_ROW;
//            int c_chk = out_idx % CHUNKS_PER_ROW;
//
//            uint512_t result_chunk = 0;
//
//            const bool row_border = (r_idx == 0) || (r_idx == HEIGHT - 1);
//
//        Calc_64:
//            for (int k = 0; k < PIXELS_PER_CHUNK; k++)
//            {
//#pragma HLS UNROLL
//
//                const int lo = k * 8;
//                const int hi = lo + 7;
//                const int j = (c_chk * PIXELS_PER_CHUNK) + k;
//
//                const bool col_border = (j == 0) || (j == WIDTH - 1);
//
//                if (row_border || col_border)
//                {
//                    result_chunk.range(hi, lo) = 0;
//                }
//                else
//                {
//                    int val = 5 * (int)win[1][1].range(hi, lo);
//
//                    val -= (int)win[0][1].range(hi, lo);
//                    val -= (int)win[2][1].range(hi, lo);
//
//                    if (k > 0)
//                    {
//                        val -= (int)win[1][1].range((k - 1) * 8 + 7, (k - 1) * 8);
//                    }
//                    else
//                    {
//                        val -= (int)win[1][0].range(DATA_WIDTH_BITS - 1, DATA_WIDTH_BITS - PIXEL_SIZE_BITS);
//                    }
//
//                    if (k < PIXELS_PER_CHUNK - 1)
//                    {
//                        val -= (int)win[1][1].range((k + 1) * 8 + 7, (k + 1) * 8);
//                    }
//                    else
//                    {
//                        val -= (int)win[1][2].range(PIXEL_SIZE_BITS - 1, 0);
//                    }
//
//                    result_chunk.range(hi, lo) = clip_u8(val);
//                }
//            }
//            C_filt[out_idx] = result_chunk;
//        }
//    }
//
//    // ========================================================================
//    // STAGE 3: WRITE OUTPUT TO DDR
//    // ========================================================================
//Write_Loop:
//    for (int i = 0; i < TOTAL_CHUNKS; i++)
//    {
//#pragma HLS PIPELINE II=1
//#pragma HLS LOOP_TRIPCOUNT min=TOTAL_CHUNKS max=TOTAL_CHUNKS
//        C[i] = C_filt[i];
//    }
//}
//
//} // extern "C"
