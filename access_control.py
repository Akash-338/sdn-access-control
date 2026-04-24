from pox.core import core
from pox.lib.revent import *
from pox.lib.util import dpidToStr
import pox.openflow.libopenflow_01 as of
from pox.lib.addresses import EthAddr
import datetime

log = core.getLogger()

WHITELIST = [
    ('00:00:00:00:00:01', '00:00:00:00:00:02'),
    ('00:00:00:00:00:02', '00:00:00:00:00:01'),
]

ALLOWED_PAIRS = set()
for src, dst in WHITELIST:
    ALLOWED_PAIRS.add((EthAddr(src), EthAddr(dst)))
    ALLOWED_PAIRS.add((EthAddr(dst), EthAddr(src)))

HOST_NAMES = {
    '00:00:00:00:00:01': 'h1',
    '00:00:00:00:00:02': 'h2',
    '00:00:00:00:00:03': 'h3',
}

def get_name(mac):
    return HOST_NAMES.get(str(mac), str(mac))

def print_banner():
    w = 68
    print("\n" + "=" * w)
    print("  SDN-BASED ACCESS CONTROL SYSTEM".center(w))
    print("=" * w)
    print(f"  Started   : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Controller: POX  |  Protocol: OpenFlow 1.0")
    print("=" * w)
    print("""
  ALLOWED COMMUNICATION PAIRS
  ─────────────────────────────────────────────
  FROM    TO      PATH
  ─────────────────────────────────────────────
  h1      h2      Direct        (bidirectional)
  ─────────────────────────────────────────────

  BLOCKED HOST
  ─────────────────────────────
  h3  —  No communication allowed
  ─────────────────────────────

  Waiting for switch connection...
""")

def print_table_header():
    print("\n  " + "─" * 72)
    print("  │ {:<10} │ {:<10} │ {:<6} │ {:<6} │ {:<8} │ {:<12} │".format(
        "TIME", "STATUS", "FROM", "TO", "PORT", "ACTION"))
    print("  " + "─" * 72)

def print_event(status, src, dst, port=None):
    time = datetime.datetime.now().strftime('%H:%M:%S')
    src_name = get_name(src)
    dst_name = get_name(dst)

    if status == "ALLOWED":
        status_str = "✔ ALLOWED"
        action = "FORWARD"
        port_str = str(port) if port and port < 65000 else "FLOOD"
    elif status == "BLOCKED":
        status_str = "✘ BLOCKED"
        action = "DROP"
        port_str = "—"
    else:
        status_str = "~ ARP"
        action = "FLOOD"
        port_str = str(port) if port and port < 65000 else "FLOOD"

    print("  │ {:<10} │ {:<10} │ {:<6} │ {:<6} │ {:<8} │ {:<12} │".format(
        time, status_str, src_name, dst_name, port_str, action))

class AccessControl(EventMixin):
    def __init__(self):
        self.listenTo(core.openflow)
        self.mac_to_port = {}
        print_banner()

    def _handle_ConnectionUp(self, event):
        self.mac_to_port[event.dpid] = {}
        print("  " + "=" * 68)
        print("  ✔  Switch connected : {}".format(dpidToStr(event.dpid)))
        print("  ✔  Access control rules are now ACTIVE")
        print("  " + "=" * 68)
        print_table_header()

    def is_allowed(self, src, dst):
        return (src, dst) in ALLOWED_PAIRS

    def _handle_PacketIn(self, event):
        pkt = event.parsed
        if not pkt.parsed:
            return

        dpid = event.dpid
        in_port = event.port
        src = pkt.src
        dst = pkt.dst

        if str(dst).startswith('33:33') or str(dst).startswith('01:00'):
            return

        self.mac_to_port.setdefault(dpid, {})
        self.mac_to_port[dpid][src] = in_port

        if pkt.type == pkt.ARP_TYPE:
            out_port = self.mac_to_port[dpid].get(dst, of.OFPP_FLOOD)
            print_event("ARP", src, dst, out_port)
            msg = of.ofp_packet_out()
            msg.data = event.ofp
            msg.in_port = in_port
            msg.actions.append(of.ofp_action_output(port=out_port))
            event.connection.send(msg)
            return

        if not self.is_allowed(src, dst):
            print_event("BLOCKED", src, dst)
            msg = of.ofp_flow_mod()
            msg.match.dl_src = src
            msg.match.dl_dst = dst
            msg.priority = 10
            msg.idle_timeout = 30
            event.connection.send(msg)
            return

        out_port = self.mac_to_port[dpid].get(dst, of.OFPP_FLOOD)
        print_event("ALLOWED", src, dst, out_port)

        if out_port != of.OFPP_FLOOD:
            msg = of.ofp_flow_mod()
            msg.match.in_port = in_port
            msg.match.dl_src = src
            msg.match.dl_dst = dst
            msg.priority = 5
            msg.idle_timeout = 60
            msg.hard_timeout = 0
            msg.actions.append(of.ofp_action_output(port=out_port))
            event.connection.send(msg)

        msg = of.ofp_packet_out()
        msg.data = event.ofp
        msg.in_port = in_port
        msg.actions.append(of.ofp_action_output(port=out_port))
        event.connection.send(msg)

def launch():
    core.registerNew(AccessControl)
