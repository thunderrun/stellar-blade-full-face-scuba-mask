import hashlib, json, traceback
from pathlib import Path
import unreal
PROJECT = Path(unreal.SystemLibrary.get_project_directory()).resolve()
ROOT = PROJECT.parent
REPORT = {'success': False, 'sounds': {}}
try:
    for mode, name in [('run', 'SW_RunBreathingLoop'), ('walk', 'SW_WalkBreathingLoop')]:
        source = ROOT / ('source/audio/' + mode + '_breathing_loop.wav')
        task = unreal.AssetImportTask()
        task.set_editor_property('filename', str(source))
        task.set_editor_property('destination_path', '/Game/CodexRunningBreath/Audio')
        task.set_editor_property('destination_name', name)
        task.set_editor_property('automated', True)
        task.set_editor_property('replace_existing', True)
        task.set_editor_property('save', True)
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        paths = task.get_editor_property('imported_object_paths')
        assert len(paths) == 1, paths
        sound = unreal.EditorAssetLibrary.load_asset(paths[0])
        assert isinstance(sound, unreal.SoundWave)
        sound.set_editor_property('looping', True)
        sound.set_editor_property('streaming', False)
        sound.set_editor_property('compression_quality', 100)
        sound.set_editor_property('virtualization_mode', unreal.VirtualizationMode.PLAY_WHEN_SILENT)
        sound.set_editor_property('sound_class_object', None)
        sound.set_editor_property('volume', 1.)
        sound.set_editor_property('pitch', 1.)
        assert unreal.EditorAssetLibrary.save_loaded_asset(sound, only_if_is_dirty=False)
        REPORT['sounds'][mode] = {'asset': sound.get_path_name(), 'looping': bool(sound.get_editor_property('looping')),
            'streaming': bool(sound.get_editor_property('streaming')), 'duration': float(sound.get_editor_property('duration')),
            'source': str(source), 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest()}
    REPORT.update(success=True, engine=unreal.SystemLibrary.get_engine_version())
except Exception as e:
    REPORT.update(error=str(e), traceback=traceback.format_exc())
    unreal.log_error(REPORT['traceback'])
    raise
finally:
    (PROJECT / 'Saved').mkdir(exist_ok=True)
    (PROJECT / 'Saved/audio-import-report.json').write_text(json.dumps(REPORT, indent=2) + '\n')
    unreal.log('RUNNING_BREATH_IMPORT ' + json.dumps(REPORT))
