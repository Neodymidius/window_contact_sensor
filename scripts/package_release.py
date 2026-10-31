#!/usr/bin/env python3
"""Create a deterministic firmware ZIP and SHA-256 checksums without publishing."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', default=(ROOT/'VERSION').read_text().strip())
    parser.add_argument('--build-dir', type=Path, default=ROOT/'firmware/cmake_gcc/build/base')
    parser.add_argument('--output', type=Path, default=ROOT/'dist')
    args=parser.parse_args()
    if not re.fullmatch(r'\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?', args.version):
        parser.error('version must be a semantic version without a leading v')
    if args.version != (ROOT/'VERSION').read_text().strip():
        parser.error('update VERSION, CMake project version and ZAP sw build ID before packaging')
    source_files=[]
    for base in ('firmware','scripts','docs'):
        for file in (ROOT/base).rglob('*'):
            relative=file.relative_to(ROOT)
            if not file.is_file() or any(p in ('build','__pycache__','.vscode') or p.startswith('simplicity_sdk_') for p in relative.parts):
                continue
            if file.suffix in ('.pyc','.log') or file.name=='slc_args.json':
                continue
            source_files.append(file)
    manifest=''.join(f'{hashlib.sha256(f.read_bytes()).hexdigest()}  {f.relative_to(ROOT).as_posix()}\n' for f in sorted(source_files))
    # Packaging must use binaries built after the exported source/configuration.
    binaries={}
    for ext in ('hex','s37'):
        binary=args.build_dir/f'ZigbeeWindowContactSensor.{ext}'
        if not binary.is_file():
            parser.error(f'missing {binary}; build firmware first')
        if any(f.stat().st_mtime > binary.stat().st_mtime for f in source_files if f.suffix in ('.c','.h','.zap','.cmake') or f.name=='CMakeLists.txt'):
            parser.error('firmware source/configuration is newer than the binary; rebuild first')
        binaries[f'window-contact-sensor-{args.version}.{ext}']=binary.read_bytes()
    files={**binaries, 'FLASHING.md':(ROOT/'docs/FLASHING.md').read_bytes(),
           'LICENSE':(ROOT/'LICENSE').read_bytes(),
           'THIRD_PARTY_NOTICES.md':(ROOT/'THIRD_PARTY_NOTICES.md').read_bytes(),
           'LICENSES/Simplicity-SDK.txt':(ROOT/'LICENSES/Simplicity-SDK.txt').read_bytes(),
           'RELEASE_NOTES.md':(ROOT/'RELEASE_NOTES.md').read_bytes(),
           'SOURCE_MANIFEST.sha256':manifest.encode(),
           'release.json':(json.dumps({'version':args.version, 'board':'Seeed Studio XIAO MG24',
               'part':'EFR32MG24B220F1536IM48','sdk':'2026.6.2','compiler':'Arm GNU 14.2.rel1',
               'ota_supported':False,'usb_sense_enabled':False,
               'source_manifest_sha256':hashlib.sha256(manifest.encode()).hexdigest()},indent=2)+'\n').encode()}
    files['SHA256SUMS']=''.join(f'{hashlib.sha256(data).hexdigest()}  {name}\n' for name,data in sorted(files.items())).encode()
    args.output.mkdir(parents=True,exist_ok=True)
    archive=args.output/f'window-contact-sensor-v{args.version}-xiao-mg24.zip'
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as out:
        for name,data in sorted(files.items()):
            info=zipfile.ZipInfo(name, date_time=(1980,1,1,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o100644 << 16
            out.writestr(info,data)
    checksum=args.output/(archive.name+'.sha256')
    checksum.write_text(f'{hashlib.sha256(archive.read_bytes()).hexdigest()}  {archive.name}\n')
    print(archive)
    print(checksum)
if __name__=='__main__':
    main()
