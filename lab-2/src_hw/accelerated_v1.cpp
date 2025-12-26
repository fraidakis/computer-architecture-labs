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
*
*/

#include "../inc/hls_helpers.h"

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
   // m_axi: AXI4 Master interface for DDR memory access
   //   - offset=slave: Base address provided by host via AXI-Lite
   //   - bundle=gmemX: Separate memory ports for concurrent A/B/C access
   //   - depth=TOTAL_CHUNKS: Memory depth hint for co-simulation
#pragma HLS INTERFACE m_axi port = A offset = slave bundle = gmemA depth = TOTAL_CHUNKS
#pragma HLS INTERFACE m_axi port = B offset = slave bundle = gmemB depth = TOTAL_CHUNKS
#pragma HLS INTERFACE m_axi port = C offset = slave bundle = gmemC depth = TOTAL_CHUNKS

   // s_axilite: AXI4-Lite slave interface for control signals
   //   - Provides start/done/idle signals and function arguments to host
#pragma HLS INTERFACE s_axilite port = A bundle = control
#pragma HLS INTERFACE s_axilite port = B bundle = control
#pragma HLS INTERFACE s_axilite port = C bundle = control
#pragma HLS INTERFACE s_axilite port = return bundle = control

   // ========================================================================
   // LOCAL BUFFERS (BRAM)
   // ========================================================================
   // Static arrays to hold full image frames in on-chip BRAM.
   // Using PADDED_IMAGE_SIZE ensures 64-byte aligned rows for efficient access.
   //
   // C_tmp: Holds posterized difference result (Stage 1 output)
   // C_filt: Holds filtered result (Stage 2 output)
   //
   // 'static' keyword: Ensures arrays are allocated in BRAM, not registers
   // 2D ARRAYS: [row][col] layout enables row-based partitioning for filter
   static pixel_t C_tmp[HEIGHT][PADDED_WIDTH];
   static pixel_t C_filt[HEIGHT][PADDED_WIDTH];

   // -------------------------------------------------------------------------
   // ARRAY PARTITIONING FOR C_tmp (used by Filter stage)
   // -------------------------------------------------------------------------
   // The 5-point stencil filter accesses 5 pixels simultaneously:
   //   north[i-1][j], south[i+1][j], west[i][j-1], center[i][j], east[i][j+1]
   //
   // dim=1 (rows): Cyclic factor=3 places consecutive rows in different BRAM banks
   //   → Rows i-1, i, i+1 map to banks (i-1)%3, i%3, (i+1)%3 (always different)
   //   → Enables parallel read of north, center, south
#pragma HLS ARRAY_PARTITION variable=C_tmp cyclic factor=3 dim=1

   // dim=2 (cols): Cyclic factor=64 places consecutive columns in different banks
   //   → Columns j-1, j, j+1 map to different banks (since 64 > 3)
   //   → Enables parallel read of west, center, east
   //   → Also enables 64-pixel parallel access in Posterize stage
#pragma HLS ARRAY_PARTITION variable=C_tmp cyclic factor=PIXELS_PER_CHUNK dim=2

   // -------------------------------------------------------------------------
   // ARRAY PARTITIONING FOR C_filt (used by Pack stage)
   // -------------------------------------------------------------------------
   // dim=2 (cols): Cyclic factor=64 enables reading 64 consecutive pixels
   // in parallel when packing them into 512-bit output chunks
#pragma HLS ARRAY_PARTITION variable=C_filt cyclic factor=PIXELS_PER_CHUNK dim=2

   // ========================================================================
   // STAGE 1: POSTERIZED ABSOLUTE DIFFERENCE
   // ========================================================================
   // Read 512-bit chunks from DDR, compute |A-B|, posterize, store to C_tmp
   //
   // Execution: TOTAL_CHUNKS iterations, processing 64 pixels per iteration
   // Memory pattern: Sequential burst reads from DDR (efficient)
Posterize_Main_Loop:
   for (int chunk_idx = 0; chunk_idx < TOTAL_CHUNKS; chunk_idx++)
   {
       // PIPELINE II=1: Target one new 512-bit chunk per clock cycle
       // This creates a deeply pipelined loop that processes chunks continuously
#pragma HLS PIPELINE II = 1
#pragma HLS LOOP_TRIPCOUNT min = TOTAL_CHUNKS max = TOTAL_CHUNKS

       // Burst read: Load 64 pixels (512 bits) from each input image
       const uint512_t chunk_A = A[chunk_idx];
       const uint512_t chunk_B = B[chunk_idx];

       // Process all 64 pixels within this chunk
Posterize_Process_Loop:
       for (int k = 0; k < PIXELS_PER_CHUNK; k++)
       {
           // UNROLL: Replicate hardware 64x to process all pixels in parallel
           // Combined with outer PIPELINE, enables 64 pixels/cycle throughput
#pragma HLS UNROLL

           // Extract individual 8-bit pixels from 512-bit word
           // .range(high_bit, low_bit) extracts bits [high_bit:low_bit]
           // Pixel k occupies bits [k*8+7 : k*8]
           const pixel_t pA = chunk_A.range((k * 8) + 7, k * 8);
           const pixel_t pB = chunk_B.range((k * 8) + 7, k * 8);

           // Compute absolute difference
           const pixel_t abs_diff = (pA > pB) ? (pA - pB) : (pB - pA);

           // Apply posterization to quantize to 3 levels
           const pixel_t post = posterize(abs_diff);

           // Calculate 2D coordinates
           // chunk_idx maps to (row, col) and k is the offset within chunk
           const int row = chunk_idx / CHUNKS_PER_ROW;
           const int col = (chunk_idx % CHUNKS_PER_ROW) * PIXELS_PER_CHUNK + k;

           // Store to local buffer using 2D indexing
        C_tmp[row][col] = post;
       }
   }

   // ========================================================================
   // STAGE 2: 3×3 SHARPEN FILTER
   // ========================================================================
   // Apply sharpening convolution using Laplacian-based kernel:
   //   output = 5*center - north - south - west - east
Filter_Row:
   for (int i = 0; i < HEIGHT; i++)
   {
#pragma HLS LOOP_TRIPCOUNT min = HEIGHT max = HEIGHT
Filter_Col:
       for (int j = 0; j < WIDTH; j++)
       {
#pragma HLS PIPELINE II = 1
#pragma HLS LOOP_TRIPCOUNT min = WIDTH max = WIDTH

           // Border pixels (first/last row and column) are set to 0
           if (i == 0 || j == 0 || i == HEIGHT - 1 || j == WIDTH - 1)
           {
               C_filt[i][j] = 0;
           }
           else
           {
               // Fetch 5 pixels for the sharpen kernel (cross pattern)
               // Cast to int to allow negative intermediate results
               // 2D indexing enables row-based partitioning for parallel access
               const int center = (int)C_tmp[i][j];
               const int north  = (int)C_tmp[i - 1][j];  // Row above
               const int south  = (int)C_tmp[i + 1][j];  // Row below
               const int west   = (int)C_tmp[i][j - 1];  // Left
               const int east   = (int)C_tmp[i][j + 1];  // Right

               // Apply sharpen kernel: output = 5*center - north - south - west - east
               // Result can be negative (clamped to 0) or > 255 (clamped to 255)
               const int s = 5 * center - north - south - west - east;

               // Clip result to valid [0, 255] range
               C_filt[i][j] = clip_u8(s);
           }
       }
   }

   // ========================================================================
   // STAGE 3: PACK AND WRITE OUTPUT
   // ========================================================================
   // Pack filtered pixels from C_filt into 512-bit words and write to DDR
   //
   // This stage performs the inverse of Stage 1's unpacking:
// - Read 64 pixels from C_filt
// - Pack them into a single 512-bit word
// - Burst write to output memory C
Pack_Main_Loop:
   for (int chunk_idx = 0; chunk_idx < TOTAL_CHUNKS; chunk_idx++)
   {
       // PIPELINE II=1: Target one 512-bit output per clock cycle
#pragma HLS PIPELINE II = 1
#pragma HLS LOOP_TRIPCOUNT min = TOTAL_CHUNKS max = TOTAL_CHUNKS

       // Initialize output chunk to zero
       uint512_t chunk_C = 0;

       // Pack all 64 pixels into the 512-bit word
       // Calculate row once per chunk (outside inner loop for clarity)
       const int row = chunk_idx / CHUNKS_PER_ROW;
       const int col_base = (chunk_idx % CHUNKS_PER_ROW) * PIXELS_PER_CHUNK;

Pack_Process_Loop:
       for (int k = 0; k < PIXELS_PER_CHUNK; k++)
       {
           // UNROLL: Process all 64 pixels in parallel
#pragma HLS UNROLL

           // Calculate column index
           const int col = col_base + k;

           // Read filtered pixel using 2D indexing
           const pixel_t v = C_filt[row][col];

           // Pack pixel into its position in the 512-bit word
           // .range() can be used as lvalue for bit insertion
           chunk_C.range((k * 8) + 7, k * 8) = v;
       }

       // Burst write: Store complete 512-bit word to DDR
       C[chunk_idx] = chunk_C;
   }
 }
} // extern "C"
