#!/usr/bin/env python3
"""Build and execute the MyLangTestKit ABI-v1 fixtures."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
KIT_ROOT = Path(__file__).resolve().parents[1]
BUILD = REPO_ROOT / "qa/runners/build_toolchain.py"
EMU = REPO_ROOT / "runtime/MyEmulator/target/release/myemu"
TESTER_ROOT = REPO_ROOT / "toolchain/MyLangTester"
TESTER = TESTER_ROOT / "build/mytest"
RUNTIME = [
    KIT_ROOT / "runtime/abi.mln",
    KIT_ROOT / "runtime/verdict.mln",
    KIT_ROOT / "runtime/matcher.mln",
    KIT_ROOT / "runtime/return_sequence.mln",
    KIT_ROOT / "runtime/history.mln",
    KIT_ROOT / "platform/mycomputer/verdict.mln",
]


def run_fixture(name: str, marker: str) -> None:
    source = KIT_ROOT / "tests" / f"{name}.mln"
    with tempfile.TemporaryDirectory(prefix=f"mylang-testkit-{name}-") as temp:
        temp_dir = Path(temp)
        image = temp_dir / f"{name}.mbin"
        build = subprocess.run(
            [
                sys.executable,
                str(BUILD),
                str(source),
                *(str(path) for path in RUNTIME),
                "-o",
                str(image),
                "--build-dir",
                str(temp_dir / "build"),
                "--entry",
                "kernel_main",
            ],
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        if build.returncode != 0:
            raise RuntimeError(f"{name}: build failed\n{build.stdout}")

        emulator = subprocess.run(
            [str(EMU), "-i", str(image), "--headless", "--step", "100000"],
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        if emulator.returncode != 0:
            raise RuntimeError(f"{name}: emulator exited {emulator.returncode}\n{emulator.stdout}")
        if marker not in emulator.stdout:
            raise RuntimeError(
                f"{name}: expected {marker!r}, got\n{emulator.stdout}"
            )


def run_redirect_fixture() -> None:
    """Exercise the compiler, runner, linker and facade as one test build."""
    build_tester = subprocess.run(
        ["make", "-C", str(TESTER_ROOT), "all"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if build_tester.returncode != 0:
        raise RuntimeError(f"facade_redirect: mytest build failed\n{build_tester.stdout}")

    test = KIT_ROOT / "tests/facade_redirect.test.mln"
    result = subprocess.run(
        [str(TESTER), str(test)],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.returncode != 0 or "[PASS] facade_redirect" not in result.stdout:
        raise RuntimeError(f"facade_redirect: expected test to pass\n{result.stdout}")


def main() -> int:
    run_fixture("verdict_test", "TEST_PASS:verdict_test")
    run_fixture("assert_fail_test", "TEST_FAIL:expected assertion failure")
    run_fixture("mock_core_test", "TEST_PASS:mock_core_test")
    run_fixture("pointer_method_chain_test", "TEST_PASS:pointer_method_chain_test")
    run_fixture("mock_engine_test", "TEST_PASS:mock_engine_test")
    run_redirect_fixture()
    print("[PASS] MyLangTestKit ABI v1")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as error:
        print(f"[FAIL] {error}", file=sys.stderr)
        raise SystemExit(1)
