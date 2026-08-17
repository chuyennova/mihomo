# V2.1 regression-vector fix

V2.1 does not change production hybrid/profile code.

The V2 GitHub run compiled and packaged successfully, but the executable IPv6 regression test used three incorrect hard-coded expected Flow Label values. The production implementation and the official SipHash-2-4 reference vector were correct.

Correct deterministic values for the locked test tuple/key are:

- TCP 40000 -> 443, protocol 6: `0x0f32fd`
- UDP 40000 -> 443, protocol 17: `0x0aeed7`
- TCP 40001 -> 443, protocol 6: `0x031c6b`

The change is test-only. Windows/macOS/Linux/Android runtime profile code is byte-for-byte unchanged from V2.
