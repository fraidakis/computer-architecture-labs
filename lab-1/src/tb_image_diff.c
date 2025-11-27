#include <stdio.h>
#include <stdlib.h>
#include "image_defines.h"

// Declaration of top-level HW function
void IMAGE_DIFF_POSTERIZE(pixel_t A[IMAGE_SIZE], pixel_t B[IMAGE_SIZE], pixel_t C[IMAGE_SIZE]);

// Software Reference Implementation (for verification)
void sw_reference_diff_posterize(pixel_t *A, pixel_t *B, pixel_t *C_ref) {
    for (int i = 0; i < IMAGE_SIZE; i++) {
        int16_t diff = (int16_t)A[i] - (int16_t)B[i];
        if (diff < 0) diff = -diff;
        
        pixel_t abs_diff = (pixel_t)diff;
        
        if (abs_diff < THRESH_LOW) {
            C_ref[i] = 0;
        } else if (abs_diff < THRESH_HIGH) {
            C_ref[i] = 128;
        } else {
            C_ref[i] = 255;
        }
    }
}

int main() {
    // Use static to avoid stack overflow with large images
    static pixel_t img_A[IMAGE_SIZE];
    static pixel_t img_B[IMAGE_SIZE];
    static pixel_t img_C_HW[IMAGE_SIZE];  // Hardware Result
    static pixel_t img_C_SW[IMAGE_SIZE];  // Software (Reference) Result

    printf("Starting Testbench for IMAGE_DIFF_POSTERIZE...\n");
    printf("Image Size: %dx%d (%d pixels)\n", WIDTH, HEIGHT, IMAGE_SIZE);
    printf("Thresholds: THRESH_LOW=%d, THRESH_HIGH=%d\n", THRESH_LOW, THRESH_HIGH);

    // 1. Array Initialization (Input Generation)
    // Use fixed seed for reproducibility
    srand(42); 

    for (int i = 0; i < IMAGE_SIZE; i++) {
        // Random values 0-255
        img_A[i] = rand() % 256;
        
        // To verify all cases (small, medium, large difference),
        // generate B by adding a random noise/deviation to A.
        int noise = (rand() % 200) - 100; // deviation from -100 to +99
        int temp_b = img_A[i] + noise;
        
        // Clamp to 0-255 range
        if (temp_b < 0) temp_b = 0;
        if (temp_b > 255) temp_b = 255;
        
        img_B[i] = (pixel_t)temp_b;
    }

    // 2. Run Software Reference
    sw_reference_diff_posterize(img_A, img_B, img_C_SW);

    // 3. Run Hardware Accelerator (Top-Function)
    IMAGE_DIFF_POSTERIZE(img_A, img_B, img_C_HW);

    // 4. Compare Results
    int error_count = 0;
    
    // Counters for statistics
    int count_0 = 0, count_128 = 0, count_255 = 0;

    for (int j = 0; j < IMAGE_SIZE; j++) {
        // Correctness check
        if (img_C_HW[j] != img_C_SW[j]) {
            printf("ERROR at index %d: A=%d, B=%d -> HW=%d, SW=%d\n", 
                   j, img_A[j], img_B[j], img_C_HW[j], img_C_SW[j]);
            error_count++;
            // Stop after a few errors to avoid flooding the console
            if (error_count > 10) break;
        }

        // Collect statistics (from HW output)
        if (img_C_HW[j] == 0) count_0++;
        else if (img_C_HW[j] == 128) count_128++;
        else if (img_C_HW[j] == 255) count_255++;
    }

    // 5. Results Report
    printf("\n--- Validation Results ---\n");
    if (error_count == 0) {
        printf("*** Test Passed ***\n");
    } else {
        printf("!!! Test FAILED with %d errors !!!\n", error_count);
        return 1; // Return error code
    }

    printf("\n--- Statistics ---\n");
    printf("Black Pixels (0):   %d\n", count_0);
    printf("Gray Pixels (128):  %d\n", count_128);
    printf("White Pixels (255): %d\n", count_255);
    printf("Total Pixels:       %d\n", count_0 + count_128 + count_255);

    return 0;
}
