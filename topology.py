from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.topo import Topo
from mininet.log import setLogLevel
from mininet.cli import CLI

class AccessControlTopo(Topo):
    def build(self):
        s1 = self.addSwitch('s1')
        h1 = self.addHost('h1', mac='00:00:00:00:00:01', ip='10.0.0.1/24')
        h2 = self.addHost('h2', mac='00:00:00:00:00:02', ip='10.0.0.2/24')
        h3 = self.addHost('h3', mac='00:00:00:00:00:03', ip='10.0.0.3/24')
        self.addLink(h1, s1)
        self.addLink(h2, s1)
        self.addLink(h3, s1)

def run():
    setLogLevel('info')
    topo = AccessControlTopo()
    net = Mininet(
        topo=topo,
        controller=RemoteController('c0', ip='127.0.0.1', port=6653)
    )
    net.start()
    print("""
  ════════════════════════════════════════════════════
               TOPOLOGY READY
  ════════════════════════════════════════════════════
  Switch : s1
  Hosts  : h1  h2  h3

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
  ════════════════════════════════════════════════════
""")
    CLI(net)
    net.stop()

if __name__ == '__main__':
    run()
