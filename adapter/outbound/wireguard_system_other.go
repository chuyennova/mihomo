//go:build !windows

package outbound

import (
	"fmt"
	"net/netip"

	wireguard "github.com/metacubex/sing-wireguard"
)

func newWireGuardTunDevice(option WireGuardOption, localPrefixes []netip.Prefix, mtu uint32) (wireguard.Device, error) {
	switch option.NetworkProfile {
	case wireGuardProfileMacOS:
		return wireguard.NewStackDeviceWithProfile(localPrefixes, mtu, wireguard.NetworkProfileMacOS)
	case wireGuardProfileLinux:
		return wireguard.NewStackDeviceWithProfile(localPrefixes, mtu, wireguard.NetworkProfileLinux)
	case wireGuardProfileAndroid:
		return wireguard.NewStackDeviceWithProfile(localPrefixes, mtu, wireguard.NetworkProfileAndroid)
	case wireGuardProfileWindows:
		return wireguard.NewStackDevice(localPrefixes, mtu)
	default:
		return nil, fmt.Errorf("unsupported WireGuard network profile %q", option.NetworkProfile)
	}
}
