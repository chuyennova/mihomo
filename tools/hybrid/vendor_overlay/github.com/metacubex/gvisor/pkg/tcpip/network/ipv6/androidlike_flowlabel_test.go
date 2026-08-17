package ipv6

import (
	"encoding/binary"
	"testing"
)

func TestHybridSipHash24Reference(t *testing.T) {
	var key [16]byte
	for i := range key {
		key[i] = byte(i)
	}
	k0 := binary.LittleEndian.Uint64(key[:8])
	k1 := binary.LittleEndian.Uint64(key[8:])
	if got := sipHash24(k0, k1, nil); got != 0x726fdb47dd0e0e31 {
		t.Fatalf("got %#x", got)
	}
}
