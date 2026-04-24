# SDN-Based Access Control System

A Software-Defined Networking (SDN) access control implementation using **Mininet** for network emulation and **POX** as the OpenFlow controller. This project enforces MAC-based whitelist policies at the switch level — allowed pairs get forwarded, blocked hosts get a drop rule installed directly on the switch.

---

## Architecture

```
  ┌────────────────────────────────────────┐
  │         Mininet (topology.py)          │
  │                                        │
  │   h1 (.00:01)  h2 (.00:02)            │
  │        \           /                   │
  │         \         /   ← allowed        │
  │          [ Switch s1 ]                 │
  │               |                        │
  │          h3 (.00:03) ← blocked         │
  └───────────────|────────────────────────┘
                  │ OpenFlow 1.0
  ┌───────────────▼────────────────────────┐
  │       POX Controller (access_control.py)│
  │                                        │
  │  PacketIn → ARP? → flood               │
  │           → is_allowed(src, dst)?      │
  │               yes → install fwd rule   │
  │               no  → install drop rule  │
  └────────────────────────────────────────┘
```

**Access policy (default):**

| From | To | Result |
|------|----|--------|
| h1   | h2 | ✔ Allowed (bidirectional) |
| h2   | h1 | ✔ Allowed (bidirectional) |
| h3   | *  | ✘ Blocked |
| *    | h3 | ✘ Blocked |

---

## Requirements

| Component | Version |
|-----------|---------|
| Python | 2.7 or 3.x |
| Mininet | 2.3+ |
| POX controller | `dart` or `eel` branch |
| Open vSwitch | 2.5+ |
| Linux | Ubuntu 18.04 / 20.04 / 22.04 recommended |

> **Note:** Mininet works best on native Linux or a Linux VM. It is not supported on Windows or macOS without virtualisation.

---

## Setup

### 1. Install Mininet

```bash
sudo apt-get update
sudo apt-get install -y mininet
```

Or install from source for the latest version:

```bash
git clone https://github.com/mininet/mininet.git
cd mininet
sudo ./util/install.sh -a
```

Verify the installation:

```bash
sudo mn --test pingall
```

### 2. Install POX

```bash
git clone https://github.com/noxrepo/pox.git
cd pox
git checkout eel          # recommended stable branch
```

### 3. Clone this repository

```bash
git clone https://github.com/<your-username>/sdn-access-control.git
cd sdn-access-control
```

### 4. Place the controller file

Copy `access_control.py` into the POX `ext/` directory so POX can find it as a component:

```bash
cp access_control.py /path/to/pox/ext/
```

---

## Usage

You need **two terminal windows** — one for the POX controller, one for Mininet.

### Terminal 1 — Start the POX controller

```bash
cd /path/to/pox
sudo python pox.py log.level --DEBUG ext.access_control
```

You should see the banner printed:

```
════════════════════════════════════════════════════════════════════
              SDN-BASED ACCESS CONTROL SYSTEM
════════════════════════════════════════════════════════════════════
  Started   : 2025-01-01 12:00:00
  Controller: POX  |  Protocol: OpenFlow 1.0
...
  Waiting for switch connection...
```

### Terminal 2 — Start the Mininet topology

```bash
cd /path/to/sdn-access-control
sudo python topology.py
```

Once the switch connects, the controller terminal will show the live event table:

```
  ════════════════════════════════════════════════════════════════════
  ✔  Switch connected : 00-00-00-00-00-01
  ✔  Access control rules are now ACTIVE
  ────────────────────────────────────────────────────────────────────
  │ TIME       │ STATUS     │ FROM   │ TO     │ PORT     │ ACTION       │
  ────────────────────────────────────────────────────────────────────
  │ 12:00:01   │ ~ ARP      │ h1     │ h2     │ 2        │ FLOOD        │
  │ 12:00:01   │ ✔ ALLOWED  │ h1     │ h2     │ 2        │ FORWARD      │
  │ 12:00:02   │ ✘ BLOCKED  │ h3     │ h1     │ —        │ DROP         │
```

### Testing connectivity in the Mininet CLI

After both processes are running, use the Mininet CLI in Terminal 2:

```bash
# Test allowed pair (should succeed)
mininet> h1 ping h2 -c 3

# Test blocked host (should fail)
mininet> h3 ping h1 -c 3
mininet> h1 ping h3 -c 3

# Test all pairs at once
mininet> pingall
```

Expected `pingall` output:
```
*** Ping: testing ping reachability
h1 -> h2 X
h2 -> h1 X
h3 -> X  X
*** Results: 66% dropped (2/3 received)
```

> The two successful pings are h1→h2 and h2→h1. All traffic to/from h3 is dropped.

---

## Project Structure

```
sdn-access-control/
├── topology.py          # Mininet topology — defines hosts, switch, and controller config
├── access_control.py    # POX controller — whitelist policy + flow rule installation
└── README.md
```

### `topology.py`

Defines the virtual network using Mininet's Python API:

- Creates switch `s1` and hosts `h1`, `h2`, `h3` with fixed MACs and IPs
- Connects all hosts to `s1`
- Points `s1` at a `RemoteController` on `127.0.0.1:6653`
- Launches the Mininet CLI for interactive testing

### `access_control.py`

Implements the POX `AccessControl` component:

| Method | Description |
|--------|-------------|
| `_handle_ConnectionUp` | Fires when a switch connects; initialises the MAC table |
| `_handle_PacketIn` | Handles every packet the switch cannot forward on its own |
| `is_allowed(src, dst)` | Returns `True` if the `(src, dst)` MAC pair is in `ALLOWED_PAIRS` |

**Flow rule priority:**
- Blocked traffic → `priority=10`, `idle_timeout=30s` (drop rule)
- Allowed traffic → `priority=5`, `idle_timeout=60s` (forward rule)

Drop rules are installed at higher priority so a block always beats a stale forward rule.

---

## Customising the Whitelist

Edit the `WHITELIST` at the top of `access_control.py`:

```python
WHITELIST = [
    ('00:00:00:00:00:01', '00:00:00:00:00:02'),   # h1 ↔ h2
    ('00:00:00:00:00:02', '00:00:00:00:00:01'),
    # Add more pairs here:
    # ('00:00:00:00:00:01', '00:00:00:00:00:03'),  # h1 ↔ h3
]
```

To allow h3 to communicate with h1, add the two directional entries above and restart the controller. No changes to `topology.py` are needed.

---

## Troubleshooting

**`error: [Errno 98] Address already in use` on POX startup**

Another process is using port 6653. Kill it:

```bash
sudo fuser -k 6653/tcp
```

**`Unable to contact the remote controller`**

Make sure the POX controller is running *before* you start Mininet, and that both are using port `6653`.

**`RTNETLINK answers: File exists` in Mininet**

Clean up a previous Mininet session:

```bash
sudo mn -c
```

**Pings succeed when they should be blocked**

Flow rules from a previous run may still be active on the switch. Clean Mininet state and restart both processes:

```bash
sudo mn -c
```

---

## How It Works — Key Design Decisions

**Why install a flow rule instead of just dropping the packet?**
Installing a drop rule (`ofp_flow_mod` with no actions) means the switch handles all subsequent packets from that src/dst pair without involving the controller. This keeps the controller load low and makes blocking efficient at line rate.

**Why is ARP always allowed?**
ARP is needed for hosts to resolve each other's MAC addresses before sending IP traffic. Without it, no communication is possible at all. Note that this means h3 can still *discover* h1 and h2 via ARP — only IP-level traffic is dropped. To block ARP from h3 as well, add a source-MAC check in the ARP handler.

**Why does the drop rule have higher priority than the forward rule?**
Priority 10 (block) > Priority 5 (allow) ensures that if a stale forward rule somehow exists for a now-blocked pair, the drop rule wins.

---

## License

MIT License. See `LICENSE` for details.
