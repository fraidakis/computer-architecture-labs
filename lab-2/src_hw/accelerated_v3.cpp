///**
//* @file accelerated_v3.cpp
//* @brief V3 (Ultra-Optimized) HW-accelerated image difference + posterization + sharpen.
//*
//* Optimization Strategy: FULL WIDTH PARALLELISM (64 pixels/cycle).
//*
//* Performance:
//* - Throughput: 64 pixels per clock cycle.
//* - Latency: ~1,050 cycles (Theoretical min for 256x256 is 1024 cycles).
//*
//* Architecture:
//* - Streams are 512-bit wide (uint512_t).
//* - Sliding window operates on 512-bit chunks.
//*/
//
//#include "../inc/hls_helpers.h"
//#include <hls_stream.h>
//
//// --------------------------------------------------------------------------
//// Stage 1: Full-Width Difference & Posterization
//// --------------------------------------------------------------------------
//static void compute_diff_wide(
//   const uint512_t *A,
//   const uint512_t *B,
//   hls::stream<uint512_t> &out_stream)
//{
//Loop_Diff_Wide:
//   for (int i = 0; i < TOTAL_CHUNKS; i++)
//   {
//#pragma HLS PIPELINE II = 1
//#pragma HLS LOOP_TRIPCOUNT min = TOTAL_CHUNKS max = TOTAL_CHUNKS
//
//       uint512_t valA = A[i];
//       uint512_t valB = B[i];
//       uint512_t valC = 0;
//   // Unroll to generate 64 parallel difference units
//   Process_64_Pixels:
//       for (int k = 0; k < PIXELS_PER_CHUNK; k++)
//       {
//#pragma HLS UNROLL
//           int lo = k * 8;
//           int hi = lo + 7;
//           pixel_t pA = valA.range(hi, lo);
//           pixel_t pB = valB.range(hi, lo);
//
//           pixel_t diff = (pA > pB) ? (pA - pB) : (pB - pA);
//           valC.range(hi, lo) = posterize(diff);
//       }
//       out_stream.write(valC);
//   }
//}
//
//// --------------------------------------------------------------------------
//// Stage 2: Full-Width Sharpen Filter (64 pixels/cycle)
//// --------------------------------------------------------------------------
//static void apply_filter_wide(
//   hls::stream<uint512_t> &in_stream,
//   hls::stream<uint512_t> &out_stream)
//{
//  // Line Buffers store full 512-bit chunks
//  uint512_t lb[2][CHUNKS_PER_ROW];
//#pragma HLS ARRAY_PARTITION variable = lb complete dim = 1
//
//  // Window of 512-bit Chunks
//  uint512_t win[3][3];
//#pragma HLS ARRAY_PARTITION variable = win complete dim = 0
//
//// Initialization
//Init_LB:
//   for (int c = 0; c < CHUNKS_PER_ROW; c++)
//   {
//#pragma HLS PIPELINE II = 1
//       lb[0][c] = 0;
//       lb[1][c] = 0;
//   }
//
//Init_Win:
//   for (int r = 0; r < 3; r++)
//   {
//#pragma HLS UNROLL
//       for (int c = 0; c < 3; c++)
//           win[r][c] = 0;
//   }
//
//   // Main Loop
//   // We need padding to flush the pipeline (approx 1 row + 1 chunk)
//   const int LOOP_LIMIT = TOTAL_CHUNKS + CHUNKS_PER_ROW + 1;
//
//Loop_Filter_Wide:
//   for (int iter = 0; iter < LOOP_LIMIT; iter++)
//   {
//#pragma HLS PIPELINE II = 1
//
//      // 1. Shift Window & Read New Data
//      uint512_t new_chunk = 0;
//      if (iter < TOTAL_CHUNKS)
//      {
//          new_chunk = in_stream.read();
//      }
//
//      // Shift Window Left
//      for (int r = 0; r < 3; r++)
//      {
//#pragma HLS UNROLL
//          win[r][0] = win[r][1];
//          win[r][1] = win[r][2];
//      }
//
//      // Update Right Column
//      int col_idx = iter % CHUNKS_PER_ROW;
//
//      if (iter < TOTAL_CHUNKS)
//      {
//          win[0][2] = lb[0][col_idx];
//          win[1][2] = lb[1][col_idx];
//          win[2][2] = new_chunk;
//
//          // Update Line Buffers
//          lb[0][col_idx] = lb[1][col_idx];
//          lb[1][col_idx] = new_chunk;
//      }
//      else
//      {
//          win[0][2] = 0;
//          win[1][2] = 0;
//          win[2][2] = 0;
//      }
//
//      // 2. Compute Output for Center Chunk (win[1][1])
//      int out_idx = iter - (CHUNKS_PER_ROW + 1);
//
//      if (out_idx >= 0 && out_idx < TOTAL_CHUNKS)
//      {
//          int r_idx = out_idx / CHUNKS_PER_ROW; // Row index 0..255
//          int c_chk = out_idx % CHUNKS_PER_ROW; // Chunk col index 0..3
//
//          uint512_t result_chunk = 0;
//
//          // Border flags for cleaner logic
//          const bool row_border = (r_idx == 0) || (r_idx == HEIGHT - 1);
//
//      // Process all 64 pixels in parallel
//      Calc_64:
//          for (int k = 0; k < PIXELS_PER_CHUNK; k++)
//          {
//#pragma HLS UNROLL
//
//              const int lo = k * 8;
//              const int hi = lo + 7;
//              const int j = (c_chk * PIXELS_PER_CHUNK) + k; // Logical column index
//
//              // Unified border check
//              const bool col_border = (j == 0) || (j == WIDTH - 1);
//
//              if (row_border || col_border)
//              {
//                  result_chunk.range(hi, lo) = 0;
//              }
//              else
//              {
//                  // Center Pixel
//                  int val = 5 * (int)win[1][1].range(hi, lo);
//
//                  // North/South
//                  val -= (int)win[0][1].range(hi, lo);
//                  val -= (int)win[2][1].range(hi, lo);
//
//                  // West Neighbor
//                  if (k > 0)
//                  {
//                       val -= (int)win[1][1].range((k - 1) * 8 + 7, (k - 1) * 8);
//                   }
//                   else
//                   {
//                       val -= (int)win[1][0].range(DATA_WIDTH_BITS - 1, DATA_WIDTH_BITS - PIXEL_SIZE_BITS);  // Last byte of left chunk
//                   }
//                   // East Neighbor
//                   if (k < PIXELS_PER_CHUNK - 1)
//                   {
//                       val -= (int)win[1][1].range((k + 1) * 8 + 7, (k + 1) * 8);
//                   }
//                   else
//                   {
//                       val -= (int)win[1][2].range(PIXEL_SIZE_BITS - 1, 0);  // First byte of right chunk
//                   }
//
//                   result_chunk.range(hi, lo) = clip_u8(val);
//               }
//           }
//           out_stream.write(result_chunk);
//       }
//   }
//}
//
//// --------------------------------------------------------------------------
//// Stage 3: Write Memory
//// --------------------------------------------------------------------------
//static void write_result_wide(
//   hls::stream<uint512_t> &in_stream,
//   uint512_t *C)
//{
//Loop_Write:
//   for (int i = 0; i < TOTAL_CHUNKS; i++)
//   {
//#pragma HLS PIPELINE II = 1
//#pragma HLS LOOP_TRIPCOUNT min = TOTAL_CHUNKS max = TOTAL_CHUNKS
//       C[i] = in_stream.read();
//   }
//}
//
//extern "C" {
//
//// --------------------------------------------------------------------------
//// Top Level
//// --------------------------------------------------------------------------
//void IMAGE_DIFF_POSTERIZE(const uint512_t *A, const uint512_t *B, uint512_t *C)
//{
//#pragma HLS INTERFACE m_axi port = A offset = slave bundle = gmemA depth = TOTAL_CHUNKS
//#pragma HLS INTERFACE m_axi port = B offset = slave bundle = gmemB depth = TOTAL_CHUNKS
//#pragma HLS INTERFACE m_axi port = C offset = slave bundle = gmemC depth = TOTAL_CHUNKS
//#pragma HLS INTERFACE s_axilite port = A bundle = control
//#pragma HLS INTERFACE s_axilite port = B bundle = control
//#pragma HLS INTERFACE s_axilite port = C bundle = control
//#pragma HLS INTERFACE s_axilite port = return bundle = control
//
//   static hls::stream<uint512_t> stream_post("s_post");
//   static hls::stream<uint512_t> stream_filt("s_filt");
//
//#pragma HLS STREAM variable = stream_post depth = 16
//#pragma HLS STREAM variable = stream_filt depth = 16
//
//#pragma HLS DATAFLOW
//
//   compute_diff_wide(A, B, stream_post);
//   apply_filter_wide(stream_post, stream_filt);
//   write_result_wide(stream_filt, C);
//}
//
//} // extern "C"
