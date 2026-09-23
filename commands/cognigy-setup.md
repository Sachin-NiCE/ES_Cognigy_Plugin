---
description: Configure or update the Cognigy API base URL and API key
---

Configure this plugin's connection to Cognigy.AI.

Steps:
1. Run `python "${CLAUDE_PLUGIN_ROOT}/scripts/configure.py" --show` to check whether credentials are already set.
2. If the user's message to this command already includes a base URL and/or API key, use those values. Otherwise ask the user for:
   - **Cognigy API base URL** (e.g. `https://api-trial.cognigy.ai`)
   - **Cognigy API key**
   Only ask for the values not already provided; if credentials already exist and the user just wants to update one of them, keep the other unchanged by omitting its flag.
3. Save the values by running:
   `python "${CLAUDE_PLUGIN_ROOT}/scripts/configure.py" --base-url "<base_url>" --api-key "<api_key>"`
4. Confirm success by running `--show` again, and remind the user this can be re-run anytime to change the URL or key.

Never print the API key back to the user or log it anywhere.
