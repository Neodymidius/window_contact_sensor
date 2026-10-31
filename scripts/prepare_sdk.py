#!/usr/bin/env python3
"""Populate the ignored SDK subset from an installed, checksum-matched SDK."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk-root', type=Path, default=os.environ.get('SISDK_ROOT'))
    parser.add_argument('--openocd-root', type=Path)
    args = parser.parse_args()
    if not args.sdk_root:
        parser.error('supply --sdk-root or set SISDK_ROOT to Simplicity SDK 2026.6.2')
    sdk = Path(args.sdk_root).expanduser().resolve()
    manifest = json.loads((ROOT/'scripts/sdk-files.json').read_text())
    target = ROOT/'firmware'/('simplicity_sdk_'+manifest['sdk_version'])
    # Validate the complete input before modifying any dependency files.
    for relative, expected in manifest['files'].items():
        source = sdk/relative
        if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest() != expected:
            parser.error(f'SDK mismatch: {relative}; install exact SDK {manifest["sdk_version"]}')
    for relative, expected in manifest['files'].items():
        source, dest = sdk/relative, target/relative
        if dest.is_file() and hashlib.sha256(dest.read_bytes()).hexdigest() == expected:
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest)
    # Optional Studio/ZAP regeneration data; generated application build needs
    # only the pinned files above. These directories stay ignored too.
    for relative in ('zigbee/app/zcl', 'zigbee/app/framework/gen-template'):
        if (sdk/relative).is_dir():
            shutil.copytree(sdk/relative, target/relative, dirs_exist_ok=True)
    if args.openocd_root:
        openocd = args.openocd_root.expanduser().resolve()
        if not (openocd/'bin/openocd').is_file():
            parser.error('OpenOCD root must contain bin/openocd')
        settings = ROOT/'firmware/.vscode/settings.json'
        settings.parent.mkdir(exist_ok=True)
        values = json.loads(settings.read_text()) if settings.exists() else {}
        values.update({
            'silabsopenocdflasher.openocdRootFolder': str(openocd),
            'silabsopenocdflasher.interfaceConfigFile': 'interface/cmsis-dap.cfg',
            'silabsopenocdflasher.targetConfigFile': 'target/efm32s2_g23.cfg',
            'silabsopenocdflasher.adapterSpeed': 1000,
        })
        settings.write_text(json.dumps(values, indent=2)+'\n')
    print(f'Prepared {len(manifest["files"])} verified SDK files in {target}')
if __name__ == '__main__':
    main()
