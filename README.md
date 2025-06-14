GUI which lets you inject text into custom prompts. Hooks to DeepSeek by default.
Hacky implementation; lots of redundant widget definitions could be made with template functions.

**Features**
Columns allow quick editing / reformatting of responses; there are buttons to cycle prompts and responses.
"Enter" to send requests (or copy responses in the final row).
Changing focus to fields in the top row displays a large text field at the bottom of the screen, useful for long-term column-dependent notes. Saves automatically to promps.json.


To use:
1. Install flet, deepseek, and pyperclip
2. Replace the strings in api_keys.json with your keys; allows multiple keys for parallel requests.
3. Edit the prompts in prompts.json to your liking.
4. Run main.py.
