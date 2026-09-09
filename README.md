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

Mock/Spy state, matchers, and generated-dispatch support will be added on top
of this ABI.
