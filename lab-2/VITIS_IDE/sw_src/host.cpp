/**
 * @file host.cpp
 * @brief Host application for IMAGE_DIFF_POSTERIZE kernel (Row-padded layout)
 *
 * This host application:
 *   1. Allocates aligned memory for images (ROW-PADDED for 512-bit chunks)
 *   2. Generates compact test images (HEIGHT x WIDTH)
 *   3. Pads compact images into ROW-PADDED device layout
 *   4. Computes software reference on compact images
 *   5. Loads XCLBIN and programs FPGA
 *   6. Transfers padded data to device
 *   7. Executes kernel
 *   8. Transfers padded results back
 *   9. Unpads results back to compact layout
 *  10. Verifies correctness on the compact (real) region only
 *
 * Converted from VITIS_HLS/tb_image_diff.cpp
 */

#include "xcl2.hpp"
#include "event_timer.hpp"
#include "../../inc/image_defines.h"
#include <vector>
#include <cstdlib>
#include <cstdint>
#include <cstring>
#include <iostream>

// =============================================================================
// Helper: Pad pixels from WIDTHxHEIGHT to PADDED_WIDTH xHEIGHT
// =============================================================================
void pad_pixels(const uint8_t *image_data, uint8_t *hw_buffer)
{
    // Zero entire destination first
    std::memset(hw_buffer, 0, BUFFER_SIZE_BYTES);

    // Copy each row, leaving padding columns as zero
    for (int r = 0; r < HEIGHT; r++)
    {
        std::memcpy(hw_buffer + r * PADDED_WIDTH , image_data + r * WIDTH, WIDTH);
    }
}

// =============================================================================
// Helper: Unpad pixels from PADDED_WIDTH xHEIGHT to WIDTHxHEIGHT
// =============================================================================
void unpad_pixels(const uint8_t *hw_buffer, uint8_t *image_data)
{
    for (int r = 0; r < HEIGHT; r++)
    {
        std::memcpy(image_data + r * WIDTH, hw_buffer + r * PADDED_WIDTH , WIDTH);
    }
}

// =============================================================================
// Software Reference Implementation (operates on original image size)
// =============================================================================
void sw_reference(const uint8_t *A, const uint8_t *B, uint8_t *C_ref)
{
    // Intermediate buffer for posterized difference
    static uint8_t C_post[IMAGE_SIZE];

    // Stage 1: Absolute difference + posterization
    for (int i = 0; i < IMAGE_SIZE; i++)
    {
        int diff = (int)A[i] - (int)B[i];
        if (diff < 0) diff = -diff;
        C_post[i] = (diff < THRESH_LOW) ? 0 : (diff < THRESH_HIGH) ? 128 : 255;
    }

    // Stage 2: 3x3 Sharpen filter
    for (int r = 0; r < HEIGHT; r++)
    {
        for (int c = 0; c < WIDTH; c++)
        {
            int idx = r * WIDTH + c;
            if (r == 0 || r == HEIGHT - 1 || c == 0 || c == WIDTH - 1)
            {
                C_ref[idx] = 0; // Border policy: zero
            }
            else
            {
                int16_t val = 5 * C_post[idx] - C_post[idx - WIDTH] - C_post[idx + WIDTH] - C_post[idx - 1] - C_post[idx + 1];
                C_ref[idx] = (uint8_t)((val < 0) ? 0 : (val > 255) ? 255 : val);
            }
        }
    }
}

// =============================================================================
// Main Host Application
// =============================================================================
int main(int argc, char **argv)
{
    if (argc != 2)
    {
        std::cout << "Usage: " << argv[0] << " <XCLBIN File>" << std::endl;
        return EXIT_FAILURE;
    }

    // Print configuration
    std::cout << "====== Image Configuration ======" << std::endl;
    std::cout << "Original:  " << WIDTH << " x " << HEIGHT << " = " << IMAGE_SIZE << " pixels" << std::endl;
    std::cout << "Padded:    " << PADDED_WIDTH  << " x " << HEIGHT << " = " << PADDED_IMAGE_SIZE << " pixels" << std::endl;
    std::cout << "Chunks:    " << CHUNKS_PER_ROW << " per row, " << TOTAL_CHUNKS << " total" << std::endl;
    std::cout << "===============================" << std::endl << std::endl;

    EventTimer et;
    std::string binaryFile = argv[1];
    cl_int err;
    cl::Context context;
    cl::Kernel krnl_image_diff;
    cl::CommandQueue q;

    // =========================================================================
    // Step 1: Allocate memory
    // =========================================================================
    et.add("Allocate Memory");

    // Original images (unpadded)
    std::vector<uint8_t> image_A(IMAGE_SIZE);
    std::vector<uint8_t> image_B(IMAGE_SIZE);
    std::vector<uint8_t> sw_result(IMAGE_SIZE);
    std::vector<uint8_t> hw_result_unpadded(IMAGE_SIZE);

    // Padded images for kernel (aligned)
    std::vector<uint8_t, aligned_allocator<uint8_t>> padded_A(BUFFER_SIZE_BYTES);
    std::vector<uint8_t, aligned_allocator<uint8_t>> padded_B(BUFFER_SIZE_BYTES);
    std::vector<uint8_t, aligned_allocator<uint8_t>> padded_C(BUFFER_SIZE_BYTES);

    et.finish();

    // =========================================================================
    // Step 2: Generate test data
    // =========================================================================
    et.add("Generate Test Data");

    srand(42);
    for (int i = 0; i < IMAGE_SIZE; i++)
    {
        image_A[i] = rand() % 256;
        int noise = (rand() % 200) - 100; // Random noise between -100 and 100
        int temp = image_A[i] + noise;
        image_B[i] = (uint8_t)((temp < 0) ? 0 : (temp > 255) ? 255 : temp);
    }

    et.finish();

    // =========================================================================
    // Step 3: Compute software reference (on original images)
    // =========================================================================
    et.add("Software Reference Computation");

    sw_reference(image_A.data(), image_B.data(), sw_result.data());

    et.finish();

    // =========================================================================
    // Step 4: PAD input images for kernel
    // =========================================================================
    et.add("Pad Input Images");

    pad_pixels(image_A.data(), padded_A.data());
    pad_pixels(image_B.data(), padded_B.data());

    et.finish();

    // =========================================================================
    // Step 5: OpenCL Setup
    // =========================================================================
    et.add("OpenCL Host Code Setup");

    auto devices = xcl::get_xil_devices();

    et.finish();

    et.add("Load Binary File to FPGA");

    auto fileBuf = xcl::read_binary_file(binaryFile);
    cl::Program::Binaries bins{{fileBuf.data(), fileBuf.size()}};

    bool valid_device = false;
    for (unsigned int i = 0; i < devices.size(); i++)
    {
        auto device = devices[i];
        OCL_CHECK(err, context = cl::Context(device, nullptr, nullptr, nullptr, &err));
        OCL_CHECK(err, q = cl::CommandQueue(context, device, CL_QUEUE_PROFILING_ENABLE, &err));

        std::cout << "Trying to program device[" << i << "]: " << device.getInfo<CL_DEVICE_NAME>() << std::endl;

        cl::Program program(context, {device}, bins, nullptr, &err);
        if (err != CL_SUCCESS)
        {
            std::cout << "Failed to program device[" << i << "]!\n";
        }
        else
        {
            std::cout << "Device[" << i << "]: program successful!\n";
            OCL_CHECK(err, krnl_image_diff = cl::Kernel(program, "IMAGE_DIFF_POSTERIZE", &err));
            valid_device = true;
            break;
        }
    }

    if (!valid_device)
    {
        std::cout << "Failed to program any device, exit!\n";
        return EXIT_FAILURE;
    }

    et.finish();

    // =========================================================================
    // Step 6: Allocate device buffers (PADDED size)
    // =========================================================================
    et.add("Allocate Device Buffers");

    OCL_CHECK(err, cl::Buffer buffer_A(context, CL_MEM_USE_HOST_PTR | CL_MEM_READ_ONLY,
                                        (size_t)BUFFER_SIZE_BYTES, padded_A.data(), &err));
    OCL_CHECK(err, cl::Buffer buffer_B(context, CL_MEM_USE_HOST_PTR | CL_MEM_READ_ONLY,
                                        (size_t)BUFFER_SIZE_BYTES, padded_B.data(), &err));
    OCL_CHECK(err, cl::Buffer buffer_C(context, CL_MEM_USE_HOST_PTR | CL_MEM_WRITE_ONLY,
                                        (size_t)BUFFER_SIZE_BYTES, padded_C.data(), &err));

    et.finish();

    // =========================================================================
    // Step 7: Set kernel arguments
    // =========================================================================
    et.add("Set Kernel Arguments");

    OCL_CHECK(err, err = krnl_image_diff.setArg(0, buffer_A));
    OCL_CHECK(err, err = krnl_image_diff.setArg(1, buffer_B));
    OCL_CHECK(err, err = krnl_image_diff.setArg(2, buffer_C));

    et.finish();

    // =========================================================================
    // Step 8: Transfer padded input to device
    // =========================================================================
    et.add("Copy Padded Input to Device");

    OCL_CHECK(err, err = q.enqueueMigrateMemObjects({buffer_A, buffer_B}, 0));

    et.finish();

    // =========================================================================
    // Step 9: Launch kernel
    // =========================================================================
    et.add("Launch Kernel");

    OCL_CHECK(err, err = q.enqueueTask(krnl_image_diff));

    et.finish();

    // =========================================================================
    // Step 10: Transfer padded results back
    // =========================================================================
    et.add("Copy Padded Results from Device");

    OCL_CHECK(err, err = q.enqueueMigrateMemObjects({buffer_C}, CL_MIGRATE_MEM_OBJECT_HOST));
    OCL_CHECK(err, err = q.finish());

    et.finish();

    // =========================================================================
    // Step 11: UNPAD output
    // =========================================================================
    et.add("Unpad Output");

    unpad_pixels(padded_C.data(), hw_result_unpadded.data());

    et.finish();

    // =========================================================================
    // Step 12: Verify results
    // =========================================================================
    et.add("Verify Results");

    int error_count = 0;
    for (int i = 0; i < IMAGE_SIZE; i++)
    {
        if (hw_result_unpadded[i] != sw_result[i])
        {
            if (error_count < 10)
            {
                int row = i / WIDTH;
                int col = i % WIDTH;
                std::cout << "Error at [" << row << "," << col << "]: "
                          << "HW=" << (int)hw_result_unpadded[i]
                          << " SW=" << (int)sw_result[i] << std::endl;
            }
            error_count++;
        }
    }

    et.finish();

    // =========================================================================
    // Print timing summary
    // =========================================================================
    std::cout << "\n----------------- Key Execution Times -----------------" << std::endl;
    et.print();

    if (error_count == 0)
    {
        std::cout << "\nTEST PASSED\n" << std::endl;
        return EXIT_SUCCESS;
    }
    else
    {
        std::cout << "\nTEST FAILED (" << error_count << " errors)\n" << std::endl;
        return EXIT_FAILURE;
    }
}
