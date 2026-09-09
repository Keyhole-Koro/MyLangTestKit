# MyLangTestKit

MyLangTestKit is the guest-side runtime used by `mytest`.  It is linked only
into MyLang test builds; production binaries do not include it.

The first ABI provides the verdict bridge required by `MyStdLib/assert.mln`:

- `assert_fail(char*)` emits `TEST_FAIL:<reason>` and halts.
- `testkit_pass(char*)` emits `TEST_PASS:<name>` and halts.
- `__mlt_require_abi_v1()` is a link-time ABI marker for compiler-generated
  test support.

`runtime/` is platform-neutral and delegates output/halt to the selected
platform adapter.  The initial `platform/mycomputer/` adapter targets the
MyKernel serial console and CPU halt instruction.

## Mock core

The compiler-facing generic core is available now:

- `mock.Matcher<T>` and `any<T>()`, `eq<T>(value)`, `ne<T>(value)`,
  `matches<T>(matcher, value)`.
- `mock.ReturnSequence<T>`, which supplies configured return values in order
  and repeats its final value after the sequence is exhausted.
- `mock.CallHistory<Args, Ret>`, which records packed arguments before
  dispatch and marks the call complete with its path and return value later;
  generated glue owns the bounded backing storage.
- `mock.Mock<Args, Ret>` and `Rule<Args, Ret>`, an allocation-free rule
  engine with eight rules and eight return values per rule. `when().ret(...)`
  and `then_ret(...)` form a fluent sequence; the last configured return is
  repeated. `clear_calls()` preserves configured rules and return cursors,
  while `reset()` disables the target and removes every rule.
- Mock mode (`1`) and Spy mode (`2`). A generated facade performs argument
  matching and chooses the original fallback for an unmatched Spy call; the
  shared runtime owns configured-return dispatch and history.

These are runtime building blocks, not the public testing syntax. The public
`mock.of(target).when(...).ret(...)` / `mock.spy(target)` DSL is lowered by
MyLangCompiler into typed calls to this core. Keeping target-specific argument
packing and dispatch generation in the compiler means test authors do not
define an `Args` struct or a target-specific `Mock` struct.

The linker provides the complementary test-build primitive
`--redirect <original>=<entry>`. It redirects only direct-call relocations;
the object defining `<entry>` keeps calls to `<original>` intact, allowing a
Spy entry to invoke the original function without recursion. Runtime mode and
rules change inside one linked test binary, so test cases do not relink when
switching configured behavior.

## Verify

From the MyComputer workspace root:

```bash
python3 toolchain/MyLangTestKit/tests/run_integration_tests.py
```
