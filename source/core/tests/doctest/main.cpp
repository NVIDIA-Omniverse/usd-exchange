// SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

#include <usdex/core/Diagnostics.h>

#define DOCTEST_CONFIG_IMPLEMENT // we will be supplying main()
#include <doctest/doctest.h>

int main(int argc, char** argv)
{
    doctest::Context context;
    context.applyCommandLine(argc, argv);

    // activate the delegate to affect OpenUSD diagnostic logs
    usdex::core::activateDiagnosticsDelegate();

    return context.run();
}
