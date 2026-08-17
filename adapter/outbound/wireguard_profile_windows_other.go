//go:build !windows

package outbound

import (
	"fmt"
	"net/netip"
)

func newWindowsNetworkProfileDevice(option WireGuardOption, localPrefixes []netip.Prefix, mtu uint32) (wireguardDevice, error) {
	return nil, fmt.Errorf("network-profile %q is only available in Windows builds", wireGuardProfileWindows)
}
