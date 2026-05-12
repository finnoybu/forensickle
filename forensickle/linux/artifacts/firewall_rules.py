"""Artifact: Firewall Rules — iptables-save and ufw status."""
import logging

from ..core.collector import SourceCollector
from ..core.output import ResultBuilder
from ..core.system_utils import run_command

log = logging.getLogger(__name__)
NAME = "firewall_rules"


def collect(collector: SourceCollector) -> list[dict]:
    return []


def parse(collector: SourceCollector) -> ResultBuilder:
    result = ResultBuilder(NAME)
    # iptables
    for cmd_name, cmd in [("iptables", ["iptables-save"]),
                          ("ip6tables", ["ip6tables-save"])]:
        output = run_command(cmd, timeout=10)
        if output:
            result.add_entry({"source": cmd_name, "rules_raw": output.strip()})
    # ufw
    ufw_out = run_command(["ufw", "status", "verbose"], timeout=10)
    if ufw_out:
        result.add_entry({"source": "ufw", "rules_raw": ufw_out.strip()})
    # nftables
    nft_out = run_command(["nft", "list", "ruleset"], timeout=10)
    if nft_out:
        result.add_entry({"source": "nftables", "rules_raw": nft_out.strip()})
    return result
