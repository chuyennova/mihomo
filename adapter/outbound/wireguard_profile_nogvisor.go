//go:build !with_gvisor

package outbound

import (
	"fmt"
	"net/netip"
)

func newGVisorNetworkProfileDevice(option WireGuardOption, localPrefixes []netip.Prefix, mtu uint32) (wireguardDevice, error) {
	return nil, fmt.Errorf("network-profile %q requires the with_gvisor build tag", option.NetworkProfile)
}
