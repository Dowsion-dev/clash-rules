#!/usr/bin/env python3
"""Download a consistent upstream snapshot, convert and publish only changes."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile
import time
import urllib.request

VERSION = 'v1.19.30'
UPSTREAM = 'Loyalsoldier/clash-rules'
RULES = {'direct': 'domain', 'reject': 'domain', 'cncidr': 'ipcidr'}


def download(url):
    headers = {'User-Agent': 'clash-rules-mrs-builder'}
    if url.startswith('https://api.github.com/') and os.getenv('GH_TOKEN'):
        headers['Authorization'] = 'Bearer ' + os.environ['GH_TOKEN']
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=90) as response:
                return response.read()
        except Exception:
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    sha = json.loads(download(f'https://api.github.com/repos/{UPSTREAM}/commits/release'))['sha']
    base = f'https://raw.githubusercontent.com/{UPSTREAM}/{sha}'
    source = {name: download(f'{base}/{name}.txt') for name in RULES}
    for name, data in source.items():
        if not data.startswith(b'payload:') or b'\n  - ' not in data:
            raise ValueError(f'{name}: expected nonempty YAML payload')
    hashes = {name: digest(data) for name, data in source.items()}
    previous = json.loads((out / 'manifest.json').read_text()) if (out / 'manifest.json').exists() else {}
    if (previous.get('source_sha256') == hashes and previous.get('mihomo_version') == VERSION
            and all((out / f'{name}.mrs').is_file()
                    and digest((out / f'{name}.mrs').read_bytes()) == previous.get('mrs_sha256', {}).get(name)
                    for name in RULES)):
        print('All three upstream files are unchanged; skipping conversion.')
        return
    system, machine = platform.system(), platform.machine()
    arch = {('Linux', 'x86_64'): 'linux-amd64-compatible',
            ('Darwin', 'arm64'): 'darwin-arm64'}.get((system, machine))
    if not arch:
        raise RuntimeError(f'Unsupported build platform: {system}/{machine}')
    asset_name = f'mihomo-{arch}-{VERSION}.gz'
    release = json.loads(download(f'https://api.github.com/repos/MetaCubeX/mihomo/releases/tags/{VERSION}'))
    asset = next(a for a in release['assets'] if a['name'] == asset_name)
    packed = download(asset['browser_download_url'])
    expected = asset.get('digest')
    if not expected or expected != 'sha256:' + digest(packed):
        raise ValueError('Mihomo download SHA256 verification failed or digest missing')
    with tempfile.TemporaryDirectory() as temp:
        stage = Path(temp)
        binary = stage / 'mihomo'
        binary.write_bytes(gzip.decompress(packed))
        binary.chmod(0o755)
        (stage / 'sources').mkdir()
        for name, behavior in RULES.items():
            src = stage / 'sources' / f'{name}.txt'
            src.write_bytes(source[name])
            dst = stage / f'{name}.mrs'
            subprocess.run([str(binary), 'convert-ruleset', behavior, 'yaml', str(src), str(dst)], check=True)
            if not dst.exists() or dst.stat().st_size < 16:
                raise ValueError(f'{name}: invalid conversion output')
        license_data = download(f'https://raw.githubusercontent.com/{UPSTREAM}/master/LICENSE')
        (stage / 'LICENSE').write_bytes(license_data)
        (stage / 'README.md').write_text(
            '# MRS rules\n\nSource: https://github.com/Loyalsoldier/clash-rules\n\n'
            'Original YAML files are preserved in sources/. Upstream license: GPL-3.0; see LICENSE.\n\n'
            f'Converted using MetaCubeX/mihomo {VERSION}. See manifest.json for provenance and checksums.\n')
        manifest = {'upstream': UPSTREAM, 'upstream_commit': sha, 'mihomo_version': VERSION,
                    'source_sha256': hashes,
                    'mrs_sha256': {name: digest((stage / f'{name}.mrs').read_bytes()) for name in RULES}}
        (stage / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
        # Copy only after all downloads and conversions succeed.
        for name in [*(f'{n}.mrs' for n in RULES), 'sources', 'LICENSE', 'README.md', 'manifest.json']:
            if (stage / name).is_dir():
                shutil.copytree(stage / name, out / name, dirs_exist_ok=True)
            else:
                shutil.copy2(stage / name, out / name)
        print('Successfully built all three MRS files.')


if __name__ == '__main__':
    main()
