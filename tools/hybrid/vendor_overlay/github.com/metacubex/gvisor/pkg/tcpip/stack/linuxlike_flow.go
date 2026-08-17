// SPDX-License-Identifier: Apache-2.0

package stack

import (
	"crypto/sha256"
	"encoding/binary"
	"math/bits"

	"github.com/metacubex/gvisor/pkg/tcpip"
)

// LinuxLikeIPv6FlowLabel models Linux's wire-visible automatic IPv6 label:
// one salted flow hash shared by TCP and UDP in this stack, rotate-left by 16,
// keep 20 bits, then set the stateless-range flag. The private stack seed keeps
// different WireGuard outbounds isolated.
func (s *Stack) LinuxLikeIPv6FlowLabel(localAddr, remoteAddr tcpip.Address, localPort, remotePort uint16, protocol tcpip.TransportProtocolNumber) uint32 {
	h := sha256.New()
	var secret [8]byte
	binary.BigEndian.PutUint32(secret[0:4], s.seed)
	binary.BigEndian.PutUint32(secret[4:8], s.tsOffsetSecret)
	_, _ = h.Write(secret[:])
	_, _ = h.Write(localAddr.AsSlice())
	_, _ = h.Write(remoteAddr.AsSlice())
	var tuple [8]byte
	binary.BigEndian.PutUint16(tuple[0:2], localPort)
	binary.BigEndian.PutUint16(tuple[2:4], remotePort)
	binary.BigEndian.PutUint32(tuple[4:8], uint32(protocol))
	_, _ = h.Write(tuple[:])
	sum := h.Sum(nil)
	flowHash := bits.RotateLeft32(binary.BigEndian.Uint32(sum[:4]), 16)
	return (flowHash & 0x0007ffff) | 0x00080000
}
