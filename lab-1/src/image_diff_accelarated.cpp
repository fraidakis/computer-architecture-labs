/**
 * @file image_diff_accelarated.cpp
 * @brief Hardware-accelerated image difference and posterization implementation
 *
 * This module implements a high-performance image difference calculation with
 * posterization using Xilinx HLS pragmas for FPGA acceleration. The algorithm
 * processes 64 pixels in parallel using 512-bit wide data paths.
 *
 */

#include "image_defines.h"

/**
 * @brief Computes absolute difference between two images with posterization
 *
 * This function performs hardware-accelerated image difference calculation:
 * 1. Reads two input images (A and B) in 512-bit chunks
 * 2. Computes absolute pixel difference for each pixel
 * 3. Applies three-level posterization based on threshold values
 * 4. Writes the posterized_value to output image C
 *
 * Memory Layout:
 * - Each chunk contains 64 pixels (8 bits per pixel)
 * - Total chunks = IMAGE_SIZE / 64
 * - IMAGE_SIZE must be a multiple of 64 for correct operation
 *
 * @param A Pointer to input image A (512-bit aligned)
 * @param B Pointer to input image B (512-bit aligned)
 * @param C Pointer to output image C (512-bit aligned)
 *
 * @note This function is designed for FPGA synthesis with Xilinx Vitis HLS
 * @note Performance target: 1 cycle per 64-pixel chunk (II=1)
 */
void IMAGE_DIFF_POSTERIZE(
    uint512_t *A,
    uint512_t *B,
    uint512_t *C)
{
/* HLS Interface Pragmas - Configure AXI interfaces for memory access:
  - m_axi: Allows the hardware kernel to initiate memory transactions of large data
  - s_axilite: AXI-Lite interface for control signals (pass arguments, start the kernel, etc) NOT large data

  - port: Specifies the function argument this interface applies to
  - offset = slave: Indicates that the base address is provided via a slave AXI-Lite interface
                    (software passes a pointer (address) when calling the accelerator)
  - bundle: HLS creates separate physical AXI ports to allow simultaneous memory access
  - depth: Specifies the size of the array for simulation (in terms of number of 512-bit words)
*/
#pragma HLS INTERFACE m_axi port=A offset=slave bundle=gmemA depth=IMAGE_SIZE / 64
#pragma HLS INTERFACE m_axi port=B offset=slave bundle=gmemB depth=IMAGE_SIZE / 64
#pragma HLS INTERFACE m_axi port=C offset=slave bundle=gmemC depth=IMAGE_SIZE / 64
#pragma HLS INTERFACE s_axilite port=return bundle=control

/**
 * Main processing loop - Iterates over 512-bit chunks (64 pixels at a time)
 * Pipeline directive ensures throughput of 1 chunk per cycle
 */
  Main_Loop:
  for (int chunk_idx = 0; chunk_idx < IMAGE_SIZE / 64; chunk_idx++)
  {
    /* Pipeline the loop to achieve II=1 (initiation interval of 1 cycle)
      This means a new loop iteration starts every clock cycle */
    #pragma HLS PIPELINE II = 1

    // Read 64 pixels (512 bits) from both input images
    const uint512_t chunk_A = A[chunk_idx];
    const uint512_t chunk_B = B[chunk_idx];
    uint512_t chunk_C = 0;

    /**
     * Pixel processing loop - Processes 64 pixels in parallel
     * UNROLL directive creates 64 parallel processing units
     */
    Process_Loop:
    for (int pixel_idx = 0; pixel_idx < 64; pixel_idx++)
    {
      // Full unroll to create parallelism for 64 pixels
      #pragma HLS UNROLL

      // Extract byte 'pixel_idx' (8 bits) from the 512-bit chunk
      const pixel_t pixel_A = chunk_A.range((pixel_idx * 8) + 7, pixel_idx * 8);
      const pixel_t pixel_B = chunk_B.range((pixel_idx * 8) + 7, pixel_idx * 8);

      // Compute absolute difference
      const int16_t diff = (int16_t)pixel_A - (int16_t)pixel_B;
      const pixel_t abs_diff = (pixel_t)((diff < 0) ? -diff : diff);

      // Apply three-level posterization based on thresholds
      const pixel_t posterized_value = (abs_diff < THRESH_LOW) ? 0 : (abs_diff < THRESH_HIGH) ? 128 : 255;

      // Pack posterized_value back into the output chunk
      chunk_C.range((pixel_idx * 8) + 7, pixel_idx * 8) = posterized_value;
    }

    // Write 64 processed pixels (512 bits) to output image in one clock cycle
    C[chunk_idx] = chunk_C;
  }
}
