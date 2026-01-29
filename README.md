# Sony UBP-X800 Home Assistant Integration

A dedicated integration for the **original Sony UBP-X800** 4K Blu-ray player. This integration allows for full control via a media player entity and individual button entities for every remote function using Sony's IP control protocol.

> [!IMPORTANT]  
> **Compatibility:** This integration is designed strictly for the **original UBP-X800**. The **UBP-X800M2** uses a different protocol and is currently **not supported**.

---

## Prerequisites

Before attempting to connect, ensure your Sony player is configured correctly:

1.  **Network Connection:** The player must be connected to your local network and reside on the **same subnet** as your Home Assistant instance.
2.  **Remote Start:** Navigate to `Setup` > `Network Settings` > `Remote Start` and set it to **On**. This allows the integration to wake the player from standby.
3.  **IP Control:** Navigate to `Setup` > `Network Settings` > `Remote Device Settings`. Ensure that registration and remote control are permitted.
4.  **Static IP:** It is highly recommended to assign a Static IP to your player via your router to ensure a persistent connection.

---

## Installation & Initial Setup

### 1. Prepare the Player
* The Sony player **must be switched on**.
* The player **must be on the HOME screen** (the pairing PIN will not appear if an app or a disc is currently running).

### 2. Configuration via UI
This integration is configured entirely via the Home Assistant user interface:

1.  In Home Assistant, go to **Settings** > **Devices & Services**.
2.  Click **Add Integration** and search for **Sony UBP-X800**.
3.  Enter the **Local IP Address** of your player.
4.  **PIN Pairing:** A **4-digit PIN number** will appear on the TV/Monitor connected to your Sony player.
5.  Enter this PIN into the Home Assistant configuration prompt to complete the registration.

Once authenticated, the integration will automatically generate all entities.

---

## Entities Created

### Media Player
* `media_player.sony_ubpx800`: Main entity for power state, playback control (Play/Pause/Stop), and status monitoring.

## Entities Created

### Media Player
* `media_player.sony_ubpx800`: Main entity for power state, playback control (Play/Pause/Stop), and status monitoring.

### Remote Button Entities
The integration generates individual button entities for every command available on the physical remote. These are named using the format `button.[command_name]` (e.g., `button.eject`).

| Category | Button Entities |
| :--- | :--- |
| **System** | `button.power`, `button.eject`, `button.home`, `button.display` |
| **Navigation** | `button.up`, `button.down`, `button.left`, `button.right`, `button.confirm`, `button.return` |
| **Menus** | `button.topmenu`, `button.popupmenu`, `button.options` |
| **Playback** | `button.play`, `button.pause`, `button.stop`, `button.next`, `button.prev`, `button.forward`, `button.rewind` |
| **Media Keys** | `button.subtitle`, `button.audio`, `button.angle`, `button.netflix` |
| **Numeric** | `button.num0` through `button.num9` |
| **Special** | `button.blue`, `button.red`, `button.green`, `button.yellow`, `button.karaoke`, `button.mode3d` |

---

## Dashboard Usage Example

You can add these buttons directly to your Lovelace dashboard to create a virtual remote. Here is an example of a button card configuration:

```yaml
type: button
entity: button.eject
name: Eject Disc
show_name: true
show_icon: true
tap_action:
  action: perform-action
  perform_action: button.press
  target:
    entity_id: button.eject
```
## Advanced Remote Usage

The `remote.sony_ubpx800` entity allows you to send raw commands. This is particularly useful for automations where you need to navigate menus.

### Remote Service Example (Action)
To send a command (or multiple commands) via a dashboard tap or script:

```yaml
type: button
name: "Skip 3 Chapters"
icon: mdi:fast-forward
tap_action:
  action: perform-action
  perform_action: remote.send_command
  target:
    entity_id: remote.sony_ubpx800
  data:
    command: 
      - Next
    num_repeats: 3
    delay_secs: 0.5
```
### Supported Commands
The following command strings can be passed to the `command` list when using the `remote.send_command` service:

* **Navigation:** `Up`, `Down`, `Left`, `Right`, `Confirm`, `Return`, `Home`, `Options`
* **Playback:** `Play`, `Pause`, `Stop`, `Next`, `Prev`, `Forward`, `Rewind`, `Replay`, `Advance`
* **Numeric:** `Num0`, `Num1`, `Num2`, `Num3`, `Num4`, `Num5`, `Num6`, `Num7`, `Num8`, `Num9`
* **Media & Apps:** `Netflix`, `Audio`, `SubTitle`, `Angle`, `Display`
* **System:** `Power`, `Eject`, `TopMenu`, `PopUpMenu`
* **Special:** `Blue`, `Red`, `Green`, `Yellow`, `Karaoke`, `Mode3d`, `Favorites`

## Troubleshooting
* **PIN not appearing:** Ensure the player is definitely on the **Home Screen**. If it still doesn't appear, power cycle the player and try again.
* **Device Disconnected:** Ensure the player hasn't changed IP addresses (check your router's DHCP leases).

---

*Developed for the Home Cinema community.*
