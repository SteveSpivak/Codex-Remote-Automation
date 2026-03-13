# CRA Operator Shortcut

This is the primary iPhone Shortcut for CRA approvals. It uses fixed decision choices, keeps `request_id` hidden from manual typing, and supports an optional note that is stored only in CRA audit.

## Prerequisites

- Tailscale or VPN path from iPhone to the Mac
- SSH access from the Shortcut to the Mac
- CRA broker service running on the Mac
- Repo present at `/Users/steve.spivak/Documents/MAcosAutomation`

## Mac-Side Commands

Fetch the current pending approval payload:

```bash
bash /Users/steve.spivak/Documents/MAcosAutomation/scripts/cra_shortcut_fetch_pending.sh
```

Return the chosen decision:

```bash
bash /Users/steve.spivak/Documents/MAcosAutomation/scripts/cra_shortcut_respond.sh "<request_id>" "<decision>" "<optional_note>"
```

## Shortcut Actions

Build a Shortcut named `CRA Operator Approval` with these actions in order:

1. `Run Script Over SSH`
   Host: your Mac on Tailscale or local network
   Script:
   ```bash
   bash /Users/steve.spivak/Documents/MAcosAutomation/scripts/cra_shortcut_fetch_pending.sh
   ```

2. `Get Dictionary from Input`

3. `Get Dictionary Value`
   Key: `payload`

4. `If`
   Condition: `Provided Input` `has any value`

5. `Get Dictionary Value`
   Input: payload dictionary
   Key: `summary`

6. `Get Dictionary Value`
   Input: payload dictionary
   Key: `request_id`

7. `Choose from Menu`
   Prompt text: use the summary from step 5
   Menu items:
   - `Accept`
   - `Accept for Session`
   - `Decline`
   - `Cancel`

8. Inside each menu branch, set a text variable named `decision_value`:
   - `Accept` -> `accept`
   - `Accept for Session` -> `acceptForSession`
   - `Decline` -> `decline`
   - `Cancel` -> `cancel`

9. `Ask for Input`
   Prompt: `Optional note for CRA audit`
   Input Type: `Text`
   Default Answer: leave empty

10. `Run Script Over SSH`
    Script:
    ```bash
    bash /Users/steve.spivak/Documents/MAcosAutomation/scripts/cra_shortcut_respond.sh "<request_id>" "<decision_value>" "<note>"
    ```
    Bind:
    - `<request_id>` from step 6
    - `<decision_value>` from the menu branch variable
    - `<note>` from step 9

11. `Show Result`
    Suggested text: `CRA decision sent`

12. `Otherwise` branch of step 4:
    `Show Result` with `No pending CRA approval.`

## Notes

- The decision sent back to Codex remains one of:
  - `accept`
  - `acceptForSession`
  - `decline`
  - `cancel`
- The optional note is for CRA audit only.
- If you want a faster UX later, split step 7 into four dedicated response shortcuts that all call the same `cra_shortcut_respond.sh` wrapper.
