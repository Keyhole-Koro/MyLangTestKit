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

These are runtime building blocks, not the public testing syntax.  The public
`mock.of(target).when(...).ret(...)` / `mock.spy(target)` DSL will be lowered
by MyLangCompiler into typed calls to this core.  Keeping target-specific
argument packing and dispatch generation in the compiler means test authors
do not need to define a `Mock` struct for every function signature.

## Verify

From the MyComputer workspace root:

```bash
python3 toolchain/MyLangTestKit/tests/run_integration_tests.py
```
