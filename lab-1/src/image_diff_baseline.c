/**
* @file image_diff_baseline.c
* @brief Baseline implementation of image difference with posterization
*
* This module implements a pixel-wise absolute difference operation between
* two grayscale images, followed by a three-level posterization for
* visualization of difference magnitudes.
*/

#include "image_defines.h"

/**
* @brief Computes posterized absolute difference between two images
*
* Calculates the absolute difference D = |A - B| for each pixel and applies
* three-level posterization to classify differences as small (black),
* medium (gray), or large (white).
*
* Posterization mapping:
*   - D < THRESH_LOW :     		   Output = 0   (Black - minimal difference)
*   - THRESH_LOW <= D < THRESH_HIGH : Output = 128 (Gray - moderate difference)
*   - D >= THRESH_HIGH :      		   Output = 255 (White - significant difference)
*
* @param[in]  A  Input image A (grayscale, WIDTH x HEIGHT pixels)
* @param[in]  B  Input image B (grayscale, WIDTH x HEIGHT pixels)
* @param[out] C  Output posterized difference image
*
* @note Uses int16_t intermediate values to prevent overflow during subtraction
* @note Processes images in row-major order as linearized arrays
*/
void IMAGE_DIFF_POSTERIZE(pixel_t A[IMAGE_SIZE], pixel_t B[IMAGE_SIZE], pixel_t C[IMAGE_SIZE])
{

// Loop over all image pixels
Loop_Image:
   for (int i = 0; i < IMAGE_SIZE; i++)
   {
       // Compute signed difference using wider type to prevent underflow
       const int16_t diff = (int16_t)A[i] - (int16_t)B[i];

       // Calculate absolute difference D(i,j) = |A(i,j) - B(i,j)|
       const pixel_t abs_diff = (pixel_t)( (diff < 0) ? -diff : diff );

       // Apply posterization thresholding and store result
       C[i] = (abs_diff < THRESH_LOW) ? 0 : (abs_diff < THRESH_HIGH) ? 128 : 255;
   }
}
