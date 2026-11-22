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
COMPILER = REPO_ROOT / "toolchain/MyLangCompiler/mlc"
RUNTIME = [
    KIT_ROOT / "runtime/abi.unsafe.mln",
    KIT_ROOT / "runtime/testkit.unsafe.mln",
    KIT_ROOT / "runtime/verdict.unsafe.mln",
    KIT_ROOT / "runtime/matcher.unsafe.mln",
    KIT_ROOT / "runtime/return_sequence.unsafe.mln",
    KIT_ROOT / "runtime/history.unsafe.mln",
    KIT_ROOT / "platform/mycomputer/verdict.unsafe.mln",
]


def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    """Run from the workspace root, capturing stdout and stderr together."""
    return subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def run_fixture(name: str, marker: str) -> None:
    source = KIT_ROOT / "tests" / f"{name}.unsafe.mln"
    with tempfile.TemporaryDirectory(prefix=f"mylang-testkit-{name}-") as temp:
        temp_dir = Path(temp)
        image = temp_dir / f"{name}.mbin"
        build = run_command(
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
            ]
        )
        if build.returncode != 0:
            raise RuntimeError(f"{name}: build failed\n{build.stdout}")

        emulator = run_command(
            [str(EMU), "-i", str(image), "--headless", "--step", "100000"]
        )
        if emulator.returncode != 0:
            raise RuntimeError(f"{name}: emulator exited {emulator.returncode}\n{emulator.stdout}")
        if marker not in emulator.stdout:
            raise RuntimeError(
                f"{name}: expected {marker!r}, got\n{emulator.stdout}"
            )


def run_redirect_fixture() -> None:
    """Exercise the compiler, runner, linker and facade as one test build."""
    build_tester = run_command(["make", "-C", str(TESTER_ROOT), "all"])
    if build_tester.returncode != 0:
        raise RuntimeError(f"facade_redirect: mytest build failed\n{build_tester.stdout}")

    test = KIT_ROOT / "tests/facade_redirect.unsafe.test.mln"
    result = run_command([str(TESTER), str(test)])
    required = ("[PASS] spy_redirect", "[PASS] mock_sequences", "[PASS] callback_redirect",
                "[PASS] spy callback delegates to original", "[PASS] void spy callback delegates to original",
                "[PASS] aggregate mock callback forwards hidden result buffer",
                "[PASS] aggregate spy falls back to original",
                "[PASS] aggregate spy fake delegates to original",
                "[PASS] nested mock restores outer call original target",
                "[PASS] predicate matchers and verify helpers",
                "[PASS] later rule takes precedence",
                "[PASS] ret replaces configured fake",
                "[PASS] final return repeats",
                "[PASS] context provider isolates return cursors")
    if result.returncode != 0 or not all(marker in result.stdout for marker in required):
        raise RuntimeError(f"facade_redirect: expected annotated tests to pass\n{result.stdout}")


def run_callback_signature_failures() -> None:
    """Reject incompatible fakes, including a target from a package import."""
    cases = (
        ("callback_signature_arity_fail", "has 1 parameters but target 'device_read' has 2"),
        ("callback_signature_type_fail", "parameter 2 does not match target 'device_read'"),
        ("callback_signature_return_fail", "return type does not match target 'device_read'"),
        ("callback_aggregate_return_fail", "E0104", "cannot return aggregate target 'make_pair'; use .call(fake)"),
        ("callback_void_return_fail", "E0105", "cannot configure void target 'notify'; use .call(fake)"),
        ("callback_argument_limit_fail", "E0105", "mock .when(...) supports at most six arguments"),
        ("callback_imported_result_return_fail", "E0104", "cannot return aggregate target 'fs_create'; use .call(fake)"),
    )
    with tempfile.TemporaryDirectory(prefix="mylang-testkit-callback-signature-") as temp:
        temp_dir = Path(temp)
        for case in cases:
            if len(case) == 2:
                name, message = case
                expected_code = "E0103"
            else:
                name, expected_code, message = case
            result = run_command(
                [str(COMPILER), str(KIT_ROOT / f"tests/{name}.unsafe.mln"), str(temp_dir / f"{name}.masm")]
            )
            if result.returncode == 0 or f"error[{expected_code}]" not in result.stdout or message not in result.stdout:
                raise RuntimeError(f"{name}: expected signature error\n{result.stdout}")


def run_unexpected_mock_diagnostic() -> None:
    """An unmatched Mock reports its target instead of a generic no-verdict."""
    test = KIT_ROOT / "tests/unexpected_mock.unsafe.test.mln"
    result = run_command([str(TESTER), str(test)])
    if result.returncode == 0 or "TEST_FAIL:mock.unexpected:unconfigured_target" not in result.stdout:
        raise RuntimeError(f"unexpected_mock: expected target diagnostic\n{result.stdout}")


def run_capacity_diagnostics() -> None:
    """Each exhausted facade capacity, and misuse, fails with its own reason."""
    test = KIT_ROOT / "tests/facade_capacity_fail.unsafe.test.mln"
    result = run_command([str(TESTER), str(test)])
    expected = ("rule capacity: TEST_FAIL:mock.rule_capacity",
                "return capacity: TEST_FAIL:mock.return_capacity",
                "matcher capacity: TEST_FAIL:mock.matcher_capacity",
                "nesting capacity: TEST_FAIL:mock.nesting_capacity",
                "context capacity: TEST_FAIL:mock.context_capacity",
                "call original outside fake: TEST_FAIL:mock.call_original.outside_fake",
                "call capacity: TEST_FAIL:mock.call_capacity")
    if result.returncode == 0 or not all(f"[FAIL] {line}" in result.stdout for line in expected):
        raise RuntimeError(f"facade_capacity_fail: expected capacity diagnostics\n{result.stdout}")


def main() -> int:
    run_fixture("verdict_test", "TEST_PASS:verdict_test")
    run_fixture("assert_fail_test", "TEST_FAIL:expected assertion failure")
    run_fixture("mock_core_test", "TEST_PASS:mock_core_test")
    run_fixture("pointer_method_chain_test", "TEST_PASS:pointer_method_chain_test")
    run_fixture("mock_engine_test", "TEST_PASS:mock_engine_test")
    run_redirect_fixture()
    run_callback_signature_failures()
    run_unexpected_mock_diagnostic()
    run_capacity_diagnostics()
    print("[PASS] MyLangTestKit ABI v1")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as error:
        print(f"[FAIL] {error}", file=sys.stderr)
        raise SystemExit(1)
