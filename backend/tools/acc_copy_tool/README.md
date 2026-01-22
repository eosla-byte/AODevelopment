# ACC Batch Copy Tool

This tool allows for recursive copying of folders within Autodesk Construction Cloud (ACC) or BIM 360, bypassing the Desktop Connector for faster, server-side operations.

## Prerequisites

1.  **Python 3.x** installed.
2.  **Dependencies**: `pip install requests`
3.  **ACC Configuration (CRITICAL)**:
    -   You must add the Client ID (`RH8eojry...`) to your ACC/BIM 360 Account Admin.
    -   Go to **Account Admin** > **Custom Integrations** (or BIM 360 Admin > Settings > Custom Integrations).
    -   Click **Add Custom Integration**.
    -   Select **Access**: Document Management (Read/Write).
    -   Enter the Client ID provided in `config.py`.
    -   This authorizes the "Bot" to see your projects.

## Usage

Run the script from the terminal:

```bash
python backend/tools/acc_copy_tool/main.py
```

## Workflow

1.  The script authenticates using the Client ID/Secret.
2.  You select the **Hub** (Account).
3.  You select the **Project**.
4.  You navigate to select the **SOURCE Folder** (the one you want to copy).
5.  You navigate to select the **TARGET PARENT Folder** (where you want to paste it).
6.  The script will recursively create folders and copy files server-side.
