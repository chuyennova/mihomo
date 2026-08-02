# Source locks — hybrid v1

- Mihomo: `v1.19.29`
- Baseline ZIP SHA-256: `c9c47c922c2595a83bf204ffd7aebbc33b86f6b145a890c58a1c434a8c34aff4`
- `github.com/metacubex/sing-wireguard`: `v0.0.0-20260520151737-7e7c7c1b854c`
- `github.com/metacubex/gvisor`: `v0.0.0-20251227095601-261ec1326fe8`
- `github.com/metacubex/wireguard-go`: `v0.0.0-20250820062549-a6cecdd7f57f`
- Patch revision: `hybrid-4profiles-v1`

`apply_hybrid.py` uses exact-match transformations. A dependency/API change must stop the build rather than silently generating a partially patched executable.
