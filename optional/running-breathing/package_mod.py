"""Package current Lua with the unchanged, hash-audited native audio release."""
import argparse
import hashlib
import json
import re
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path): return json.loads(path.read_text(encoding='utf-8-sig'))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audio-bundle', type=Path, required=True,
                        help='Extracted Nexus 0.2.9 bundle containing its audited audio files')
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'build/packages')
    args = parser.parse_args()
    release = read(ROOT / 'release.json')
    version = release['version']
    assert f'Loaded v{version}:' in (ROOT / 'mod/Scripts/main.lua').read_text()
    tests = read(ROOT / 'checks/lua-behavior-tests.json')
    assert tests['passed'] and tests['checks'] and all(tests['checks'].values())
    current = {name: sha(ROOT / 'mod/Scripts' / name)
               for name in ('main.lua', 'config.lua', 'running_state.lua')}
    assert tests['source_sha256'] == current, 'Run current Lua tests before packaging'
    assert len(release['audited_audio_payload']) == 3
    source = args.audio_bundle.resolve()
    for row in release['audited_audio_payload']:
        path = source / row['relative_path']
        assert path.stat().st_size == row['bytes'] and sha(path) == row['sha256'], path
    config = (ROOT / 'mod/Scripts/config.lua').read_text()
    def number(key):
        match = re.search(r'^\s*' + re.escape(key) + r'\s*=\s*([0-9.]+)\s*,', config, re.M)
        assert match, key
        return float(match.group(1))
    idle = bool(re.search(r'^\s*IdleAfterMovement\s*=\s*true\s*,', config, re.M))
    out = args.output_dir.resolve()
    bundle = out / ('Codex-Running-Breath-' + version)
    assert not bundle.exists(), 'Output bundle already exists; choose a fresh --output-dir'
    lua = bundle / 'SB/Binaries/Win64/ue4ss/Mods/CodexRunningBreath'
    (lua / 'Scripts').mkdir(parents=True)
    for row in release['audited_audio_payload']:
        target = bundle / row['relative_path']
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / row['relative_path'], target)
    for name in current:
        shutil.copy2(ROOT / 'mod/Scripts' / name, lua / 'Scripts' / name)
    (lua / 'enabled.txt').write_bytes(b'')
    shutil.copy2(ROOT / 'Install.ps1', bundle / 'Install.ps1')
    shutil.copy2(ROOT / 'PACKAGE-README.txt', bundle / 'README.txt')
    payload = sorted(p for p in (bundle / 'SB').rglob('*') if p.is_file())
    assert len(payload) == 7
    rows = [{'relative_path': p.relative_to(bundle).as_posix(),
             'bytes': p.stat().st_size, 'sha256': sha(p)} for p in payload]
    manifest = {
        'name': release['name'], 'version': version, 'container_id': release['container_id'],
        'sounds': release['sounds'], 'UE4SS_required': True, 'CNS_required': False,
        'mask_required': False, 'idle_sound': 'walk' if idle else None,
        'continuous_idle_playback': idle, 'idle_requires_prior_movement': idle,
        'idle_at_startup': False, 'stop_fade': not idle, 'stop_sound': 'walk',
        'fade_in_seconds': number('FadeInSeconds'), 'fade_out_seconds': number('FadeOutSeconds'),
        'crossfade_seconds': number('CrossfadeSeconds'), 'default_volume': number('Volume'),
        'sprint_volume': number('SprintVolume'), 'files': rows,
    }
    (bundle / 'package-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (bundle / 'validation.json').write_text(json.dumps({
        'passed': True, 'lua_tests': tests['checks'], 'source_sha256': current,
        'audio_payload_sha256_verified': True, 'installed': False, 'runtime_verified': False,
        'scope': 'Current Lua mock tests, frozen native audio hashes and ZIP readback. New edits need gameplay testing.',
    }, indent=2) + '\n')
    archive = out / (bundle.name + '.zip')
    paths = sorted(p for p in bundle.rglob('*') if p.is_file())
    assert len(paths) == 11
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in paths: z.write(p, p.relative_to(bundle).as_posix())
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None and len(z.namelist()) == 11
        for row in rows:
            assert hashlib.sha256(z.read(row['relative_path'])).hexdigest() == row['sha256']
    report = {'passed': True, 'version': version, 'zip': str(archive),
              'zip_sha256': sha(archive), 'payload_files': 7, 'zip_files': 11,
              'installed': False, 'runtime_verified': False}
    (ROOT / 'checks/package-readback.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))

if __name__ == '__main__': main()
