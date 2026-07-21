# OSC → OSC Device-Prefix Routing — Design

Date: 2026-07-21
Status: Approved

## Goal

Allow a connection whose source **and** destination are both OSC. The connection's
`address_pattern` acts as a **device prefix**: an incoming OSC message whose address
starts with the pattern is forwarded to the destination IP:port with the prefix
stripped from the address.

Example: connection pattern `/wled` → destination `192.168.1.63:9000`.
Incoming `/wled/state/on` with args `[1]` → forwards `/state/on` with args `[1]`.

## Behavior

- **Prefix match**: incoming address starts with `pattern + "/"`. The forwarded
  address is the incoming address with the pattern removed. OSC arguments are
  passed through unchanged.
- **Exact match** (incoming address equals the pattern, no sub-address): the
  optional `to.address` fallback field ("OSC Address") is used as the forwarded
  address if set; otherwise the message is dropped with a WARNING log.
- The `values` mapping does not apply to OSC destinations (args stay a
  positional list). The UI hides the Values field for OSC → OSC connections and
  the saved config omits `values` in that case.
- First matching route wins (existing behavior — connection order matters).
- Prefix matching applies **only** when the destination protocol is `osc`;
  matching for all other destination types stays strictly exact.
- Logs: `[OSC→OSC] /wled/state/on → forwarded as /state/on to 192.168.1.63:9000`.

## Config shape

No new fields. An OSC → OSC connection reuses the existing shape:

```json
{
  "name": "OSC to WLED device",
  "from": { "protocol": "osc", "address_pattern": "/wled" },
  "to": { "protocol": "osc", "ip": "192.168.1.63", "port": 9000, "address": "/optional/fallback" }
}
```

## Implementation

### Backend (`mini_osc.py`)

`handle_osc_in_message()`:
- Restructure the route-matching loop: resolve the target first, then match
  exactly, or by prefix when the target type is `osc`.
- Add an `osc` branch to the dispatch: `send_osc_message(ip, port, sub_address, list(args))`.
- Skip the `values` → dict mapping when the target type is `osc`.

No changes needed in `expand_connections()` (OSC targets and `to.address` are
already expanded).

### Frontend (`index.html`) — documented in English

- Static help panel (`#osc-osc-help`) shown between the form columns and the
  preview when source = OSC and destination = OSC, explaining device-prefix
  routing with a concrete example.
- Contextual help under "Address Pattern" (`#pattern-prefix-help`) shown in the
  same case.
- Values field (`#from-values-field`) hidden for OSC → OSC; `buildConnectionFromForm`
  omits `values` when the destination is OSC.
- Request preview shows the OSC → OSC transformation
  (`/wled/command … → /command …`) instead of being hidden.
- All toggles live in `updateRequestPreview()`, which already runs on every
  form input/change and after `editConnection()`.

### Docs

- README: new "OSC to OSC (device-prefix routing)" section.
- CLAUDE.md: short note in the routing-flow section.

## Verification

Manual test with `testing-scripts/`: send `/dev/cmd/a/b` to the OSC server and
verify a local OSC listener receives `/cmd/a/b` with identical args; verify the
exact-match fallback and the no-fallback warning path in the logs.
