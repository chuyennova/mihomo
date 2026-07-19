//go:build !windows

package outbound

import (
	"net/netip"

	wireguard "github.com/metacubex/sing-wireguard"
)

func newWireGuardTunDevice(_ WireGuardOption, localPrefixes []netip.Prefix, mtu uint32) (wireguard.Device, error) {
	return wireguard.NewStackDevice(localPrefixes, mtu)
}
