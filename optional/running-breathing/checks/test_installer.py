"""Test the bundled installer against a temporary game fixture, never the live game."""
import hashlib,json,shutil,subprocess,tempfile,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BUNDLE=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else ROOT/'build/packages/Codex-Running-Breath-0.2.9'
manifest=json.loads((BUNDLE/'package-manifest.json').read_text())
FIXTURE=Path(tempfile.mkdtemp(prefix='installer-fixture-',dir=ROOT/'checks')).resolve()
(FIXTURE/'SB/Content/Paks/~mods/OtherMod').mkdir(parents=True)
(FIXTURE/'SB/Binaries/Win64/ue4ss/Mods').mkdir(parents=True)
(FIXTURE/'SB/Binaries/Win64/ue4ss/UE4SS.dll').write_bytes(b'fixture-only')
other=FIXTURE/'SB/Content/Paks/~mods/OtherMod/leave-me.txt'
other.write_text('unrelated fixture file')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
unrelated=sha(other)
results=[]
def run(*extra,success=True):
    r=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(BUNDLE/'Install.ps1'),
                      '-GameRoot',str(FIXTURE),*extra],capture_output=True,text=True)
    results.append({'args':list(extra),'expected_success':success,'exit_code':r.returncode,'output':r.stdout+r.stderr})
    assert (r.returncode==0)==success,r.stdout+r.stderr
    assert sha(other)==unrelated
def live_hashes():
    return {row['relative_path']:sha(FIXTURE/row['relative_path']) for row in manifest['files']}
run('-CheckOnly')
assert not (FIXTURE/'SB/Content/Paks/~mods/CodexRunningBreath').exists()
run()
expected={row['relative_path']:row['sha256'] for row in manifest['files']}
assert live_hashes()==expected
run(success=False) # existing folders are not overwritten
assert live_hashes()==expected
config=FIXTURE/'SB/Binaries/Win64/ue4ss/Mods/CodexRunningBreath/Scripts/config.lua'
config.write_text(config.read_text().replace('Volume = 0.45','Volume = 0.30'))
edited=live_hashes()
run('-Uninstall',success=False)
assert live_hashes()==edited # changed configuration and all other files retained
shutil.copy2(BUNDLE/'SB/Binaries/Win64/ue4ss/Mods/CodexRunningBreath/Scripts/config.lua',config)
run('-Uninstall','-CheckOnly')
assert live_hashes()==expected
run('-Uninstall')
assert not (FIXTURE/'SB/Content/Paks/~mods/CodexRunningBreath').exists()
assert not (FIXTURE/'SB/Binaries/Win64/ue4ss/Mods/CodexRunningBreath').exists()
assert sha(other)==unrelated
report={'passed':True,'scope':'Bundled PowerShell installer executed only against a temporary fixture',
        'fixture':str(FIXTURE),'preflight_read_only':True,'seven_file_hash_readback_passed':True,
        'existing_folders_not_overwritten':True,'edited_configuration_preserved':True,
        'scoped_uninstall_passed':True,'unrelated_file_unchanged':True,'results':results,
        'installed_to_actual_game':False}
(ROOT/'checks/installer-fixture-tests.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='results'},indent=2))
