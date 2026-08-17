//go:build with_gvisor

package outbound

import (
	"fmt"
	"net/netip"

	"github.com/metacubex/mihomo/log"
	wireguard "github.com/metacubex/sing-wireguard"
)

func newGVisorNetworkProfileDevice(option WireGuardOption, localPrefixes []netip.Prefix, mtu uint32) (wireguardDevice, error) {
	var profile wireguard.NetworkProfile
	switch option.NetworkProfile {
	case wireGuardProfileMacOS:
		profile = wireguard.NetworkProfileMacOS
	case wireGuardProfileLinux:
		profile = wireguard.NetworkProfileLinux
	case wireGuardProfileAndroid:
		profile = wireguard.NetworkProfileAndroid
	default:
		return nil, fmt.Errorf("network-profile %q is not a gVisor hybrid profile", option.NetworkProfile)
	}
	device, err := wireguard.NewStackDeviceWithProfile(localPrefixes, mtu, profile)
	if err != nil {
		return nil, err
	}
	log.Warnln("[WG](%s) Using %s userspace network profile: mtu=%d", option.Name, option.NetworkProfile, mtu)
	return device, nil
}
