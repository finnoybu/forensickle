import logging
from dataclasses import dataclass, field
from typing import List
from psutil import net_if_addrs, AF_LINK
from socket import AF_INET, AF_INET6


@dataclass
class NetworkInterface:
    """
    Represents a network interface with associated addresses.

    Attributes:
        name (str): Name of the network interface.
        mac (List[str]): List of MAC addresses of the network interface.
        ipv4 (List[str]): List of IPv4 addresses associated with the interface.
        ipv6 (List[str]): List of IPv6 addresses associated with the interface.
    """

    name: str = None
    mac: List[str] = field(default_factory=list)
    ipv4: List[str] = field(default_factory=list)
    ipv6: List[str] = field(default_factory=list)


def get_network_interfaces():
    network_interfaces = []
    loopback_prefixes = ("127", "::1")

    try:
        interfaces = net_if_addrs()
        for interface, snicaddrs in interfaces.items():
            loopback = any(
                addr.address.startswith(prefix)
                for prefix in loopback_prefixes
                for addr in snicaddrs
            )

            network_interface = NetworkInterface(
                name=interface,
                mac=[addr.address for addr in snicaddrs if addr.family == AF_LINK],
                ipv4=[addr.address for addr in snicaddrs if addr.family == AF_INET],
                ipv6=[addr.address for addr in snicaddrs if addr.family == AF_INET6],
            )

            if not loopback:
                network_interfaces.append(network_interface)

        return network_interfaces

    except Exception as e:
        # Log the error and return None to indicate an error occurred
        logging.error(f"Error occurred while retrieving network interfaces: {e}")
        return None


if __name__ == "__main__":
    interfaces = get_network_interfaces()
    if interfaces is not None:
        print(interfaces)
    else:
        print(
            "Error occurred while retrieving network interfaces. Check logs for details."
        )
