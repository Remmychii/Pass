# パス Pass

Move files between your Windows PC and your phone over home Wi-Fi with a QR code. Both ways. No app on the phone, no cloud, no account, no compression: files arrive byte for byte.

![How to use Pass](docs/how-to.png)

## Get it
Download `Pass-windows.zip` from [Releases](../../releases), unzip it anywhere, run `Setup.cmd` once, then open `Pass.exe`.

Pass isn't code-signed, so Windows SmartScreen may say "Windows protected your PC". Click **More info → Run anyway**. Prefer to check first? Read `pass_app.py` and build it yourself (below).

## Use

**Send (PC → phone)**
1. Drop files on the window (or click to pick, or right-click files → Send to → **Pass to phone**).
2. Scan the QR with the phone camera and tap **Download**.
3. iPhone: **Files › Downloads** → tap the file → **Share** → **Save Video** / **Save Image** to put it in Photos.

**Receive (phone → PC)**
1. Switch to **Receive** and scan the QR.
2. Tap **Choose photos, videos or files**, pick them, tap **Upload**.
3. Files land in **Downloads › From Phone** (**Open folder** jumps there). Same names get ` (1)`, ` (2)` added; nothing is overwritten.

Keep Safari open and the screen on until a transfer finishes (an interrupted download resumes).

Picking from the iPhone Photos picker can turn HEIC into JPG. For the untouched original, pick through **Files**, or set Settings › Camera › Formats to **Most Compatible**.

## Ports and safety
- **Ports are open only while you share.** Send and Receive each open one port (from 3000 up) and the footer shows which. **Closing Pass closes them all**, and so do **Stop** and 20 minutes with no transfers.
- Only your home network: nothing goes through the internet. `Setup.cmd` allows Pass on **Private** networks only, never Public.
- Every share gets a random link; anything else gets a 404.
- Send serves only the files you picked. Receive writes only into its one folder, with cleaned file names, and never overwrites.

## Setup details
- `Setup.cmd` (asks for admin once): adds a Windows Firewall rule "Pass" (inbound TCP, Private only) and the right-click Send to entry. Safe to run again.
- `Add to Send to.cmd` adds only the Send to entry. To remove it, delete `Pass to phone` from `shell:sendto`.
- Remove the firewall rule: `netsh advfirewall firewall delete rule name="Pass"` (admin).
- PC and phone must be on the same Wi-Fi (not guest Wi-Fi).

## Build from source
Windows, Python 3.12:
```
pip install pywebview segno pyinstaller
build.cmd
```
`python pass_app.py` runs it without building. `python pass_app.py --no-gui <file>` or `--no-gui --receive [folder]` runs headless and prints the link. `release.cmd` builds and zips a release.

## Credits
Made by **レム** (Rem) · [github.com/Remmychii](https://github.com/Remmychii)

MIT license. Fonts: [Inter Tight](https://github.com/rsms/inter-tight) and [Zen Old Mincho](https://github.com/googlefonts/zen-oldmincho), SIL Open Font License 1.1.
