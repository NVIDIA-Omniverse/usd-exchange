# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

import argparse

import omni.repo.ci
import omni.repo.man


def main(_: argparse.Namespace):
    repo = omni.repo.man.resolve_tokens("$root/repo${shell_ext}")
    omni.repo.ci.launch([repo, "--verbose", "format", "--verify"])
