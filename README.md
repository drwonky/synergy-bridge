# synergy-bridge
Bridge synergy to USB physical peripherals.

## CLI usage

Run the bridge with a Synergy server and screen geometry:

```bash
python3 -m synergy_bridge.cli \
  --server 192.168.1.10:24800 \
  --screen primary:1920x1080+0+0 \
  --screen laptop:2560x1440+1920+0 \
  --keyboard-path /dev/hidg0 \
  --mouse-path /dev/hidg1 \
  --absolute-mouse-path /dev/hidg2
```

Notes:

- Use `--config /path/to/config.yaml` to load a JSON-compatible layout config file.
- Use `--relative` to emit relative mouse reports.
- Health-check logging is emitted at the configured interval (`--health-interval`).

## systemd installation

1. Copy the service definition:

   ```bash
   sudo install -D -m 0644 deploy/synergy-bridge.service /etc/systemd/system/synergy-bridge.service
   ```

2. Create the configuration file:

   ```bash
   sudo install -D -m 0644 config.yaml /etc/synergy-bridge/config.yaml
   ```

3. Enable and start the service:

   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now synergy-bridge.service
   ```
