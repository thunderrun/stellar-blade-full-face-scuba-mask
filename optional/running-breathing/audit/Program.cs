using System.Buffers.Binary;
using System.Security.Cryptography;
using CUE4Parse.Compression;
using CUE4Parse.Encryption.Aes;
using CUE4Parse.FileProvider;
using CUE4Parse.MappingsProvider.Usmap;
using CUE4Parse.UE4.Assets.Exports.Sound;
using CUE4Parse.UE4.Objects.Core.Misc;
using CUE4Parse.UE4.Versions;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

if (args.Length < 2 || args[0] is "-h" or "--help")
{
    Console.Error.WriteLine("Usage: Audit <selected container directory> <cooked-audio-audit.json> --game-paks <SB/Content/Paks> --usmap <mapping.usmap> [--oodle <Oodle DLL>]");
    Console.Error.WriteLine("Path inputs also accept SB_GAME_PAKS, SB_USMAP and SB_OODLE_DLL environment variables.");
    return args.Length > 0 && (args[0] is "-h" or "--help") ? 0 : 2;
}

var options = new Dictionary<string, string>(StringComparer.Ordinal);
for (var index = 2; index < args.Length; index += 2)
{
    if (index + 1 >= args.Length || args[index] is not ("--game-paks" or "--usmap" or "--oodle") ||
        !options.TryAdd(args[index], args[index + 1]))
    {
        Console.Error.WriteLine("Expected each supported path option once, followed by its value.");
        return 2;
    }
}
string? Input(string option, string environment) => options.TryGetValue(option, out var value)
    ? value : Environment.GetEnvironmentVariable(environment);
var paksInput = Input("--game-paks", "SB_GAME_PAKS");
var usmapInput = Input("--usmap", "SB_USMAP");
var oodleInput = Input("--oodle", "SB_OODLE_DLL");
if (string.IsNullOrWhiteSpace(paksInput) || string.IsNullOrWhiteSpace(usmapInput))
{
    Console.Error.WriteLine("Supply --game-paks and --usmap, or their SB_GAME_PAKS and SB_USMAP environment variables.");
    return 2;
}
var stage = Path.GetFullPath(args[0]);
var output = Path.GetFullPath(args[1]);
var root = Path.GetDirectoryName(output)!;
var paks = Path.GetFullPath(paksInput);
var usmap = Path.GetFullPath(usmapInput);
var oodle = string.IsNullOrWhiteSpace(oodleInput) ? null : Path.GetFullPath(oodleInput);
if (!Directory.Exists(stage) || !Directory.Exists(paks) || !File.Exists(usmap) ||
    !File.Exists(Path.Combine(paks, "global.utoc")) || (oodle is not null && !File.Exists(oodle)))
{
    Console.Error.WriteLine("Selected container directory, game Paks/global.utoc, mapping, or supplied Oodle library is missing.");
    return 2;
}
var ownedInstalledUtoc = Path.GetFullPath(Path.Combine(paks, @"~mods\CodexRunningBreath\Codex-RunningBreath-19530.utoc"));
var expectedSounds = new Dictionary<string, string>
{
    ["run"] = "/Game/CodexRunningBreath/Audio/SW_RunBreathingLoop",
    ["walk"] = "/Game/CodexRunningBreath/Audio/SW_WalkBreathingLoop"
};
var failures = new List<string>();
void Check(bool test, string message) { if (!test) failures.Add(message); }
string Id(string path)
{
    var h = new byte[64];
    using (var f = File.OpenRead(path)) f.ReadExactly(h);
    if (!h.AsSpan(0, 16).SequenceEqual("-==--==--==--==-"u8)) throw new InvalidDataException(path);
    return BinaryPrimitives.ReadUInt64LittleEndian(h.AsSpan(56, 8)).ToString("x16");
}
string Sha256(string path) => Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path))).ToLowerInvariant();

var prep = JObject.Parse(File.ReadAllText(Path.Combine(root, "audio-preparation.json")));
Check(prep.Value<bool?>("passed") == true, "Audio preparation did not pass");
Check(prep["sounds"] is JObject prepSounds && prepSounds.Properties().Select(x => x.Name).Order().SequenceEqual(expectedSounds.Keys.Order()),
    "Audio preparation must contain exactly run and walk sound expectations");

var utoc = Path.Combine(stage, "pakchunk19530-WindowsNoEditor.utoc");
var id = Id(utoc);
var installed = Directory.GetFiles(paks, "*.utoc", SearchOption.AllDirectories)
    .Select(p => new { path = Path.GetFullPath(p), id = Id(p) }).ToArray();
// Only the exact installed container owned by this mod is replaced. All other
// installed containers, including similarly named paths, remain collision checks.
var checkedInstalled = installed.Where(p => !string.Equals(p.path, ownedInstalledUtoc, StringComparison.OrdinalIgnoreCase)).ToArray();
var excludedOwned = installed.Where(p => string.Equals(p.path, ownedInstalledUtoc, StringComparison.OrdinalIgnoreCase)).ToArray();
var conflicts = checkedInstalled.Where(p => p.id == id).ToArray();
Check(conflicts.Length == 0, "New audio container ID conflicts with an installed foreign container");

// The selected audio container is uncompressed. A caller may supply Oodle for
// compressed metadata in their game installation; no library is redistributed.
if (oodle is not null) OodleHelper.Initialize(oodle);
using var provider = new DefaultFileProvider(new DirectoryInfo(stage), SearchOption.TopDirectoryOnly,
    new VersionContainer(EGame.GAME_UE4_26), StringComparer.OrdinalIgnoreCase);
provider.Initialize();
// The selected add-on contains only its two SoundWaves. The game's global
// container supplies native script-object metadata needed to deserialize them.
var scriptMetadataUtoc = Path.Combine(paks, "global.utoc");
provider.RegisterVfs(scriptMetadataUtoc);
provider.SubmitKey(new FGuid(), new FAesKey(new byte[32]));
provider.MappingsContainer = new FileUsmapTypeMappingsProvider(usmap);
provider.PostMount();
provider.LoadVirtualPaths();
var files = provider.Files.Keys.Order(StringComparer.OrdinalIgnoreCase).ToArray();
var expectedFiles = expectedSounds.Values.Select(p => "SB/Content/" + p["/Game/".Length..] + ".uasset")
    .Order(StringComparer.OrdinalIgnoreCase).ToArray();
Check(files.SequenceEqual(expectedFiles, StringComparer.OrdinalIgnoreCase), "Expected exactly two audio packages and no foreign payloads");

var sounds = new JObject();
foreach (var (role, asset) in expectedSounds)
{
    var expected = prep["sounds"]?[role] as JObject;
    Check(expected is not null && expected.Value<bool?>("passed") == true, $"{role}: missing or failed audio preparation record");
    var expectedDuration = expected?.Value<double?>("processed_duration_seconds");
    var expectedChannels = expected?.Value<int?>("channels");
    var expectedSampleRate = expected?.Value<int?>("sample_rate");
    Check(expectedDuration is > 0 && expectedChannels is > 0 && expectedSampleRate is > 0,
        $"{role}: missing valid dynamic duration/channel/sample rate expectations");
    try
    {
        var exports = provider.LoadPackage(asset).GetExports().ToArray();
        var exportTypes = exports.Select(x => x.GetType().Name).ToArray();
        Check(exports.Length == 1 && exports[0] is USoundWave, $"{role}: expected one SoundWave export only");
        if (exports.Length != 1 || exports[0] is not USoundWave wave)
        {
            sounds[role] = JObject.FromObject(new { asset, export_types = exportTypes, passed = false });
            continue;
        }
        var json = JObject.FromObject(wave);
        File.WriteAllText(Path.Combine(root, $"soundwave-{role}-export.json"), json.ToString(Formatting.Indented));
        bool looping = wave.GetOrDefault<bool>("bLooping", false);
        float duration = wave.GetOrDefault<float>("Duration", 0);
        int channels = wave.GetOrDefault<int>("NumChannels", 0);
        int sampleRate = wave.GetOrDefault<int>("SampleRate", 0);
        var compressedMetadata = json["CompressedFormatData"] as JObject;
        bool hasInlinePayload = compressedMetadata is not null && compressedMetadata.Properties().Any()
            && compressedMetadata.Properties().All(p =>
                p.Value.Value<string>("BulkDataFlags")?.Contains("BULKDATA_ForceInlinePayload", StringComparison.Ordinal) == true
                && p.Value.Value<long?>("ElementCount") is > 0
                && p.Value.Value<long?>("SizeOnDisk") is > 0);
        bool inlineCompressed = !wave.bStreaming && wave.CompressedFormatData is not null && hasInlinePayload;
        Check(looping, $"{role}: cooked wave is not set to loop");
        Check(expectedDuration.HasValue && Math.Abs(duration - expectedDuration.Value) < .001,
            $"{role}: cooked duration differs from the supplied processed recording");
        Check(channels == expectedChannels && sampleRate == expectedSampleRate,
            $"{role}: cooked channel count/sample rate differ from the processed recording");
        Check(inlineCompressed, $"{role}: expected inline compressed audio data");
        sounds[role] = JObject.FromObject(new
        {
            asset,
            export_types = exportTypes,
            looping,
            duration_seconds = duration,
            channels,
            sample_rate = sampleRate,
            streaming = wave.bStreaming,
            inline_compressed_audio = inlineCompressed,
            compressed_format_metadata = json["CompressedFormatData"],
            expected_duration_seconds = expectedDuration,
            expected_channels = expectedChannels,
            expected_sample_rate = expectedSampleRate,
            passed = !failures.Any(f => f.StartsWith(role + ":", StringComparison.Ordinal))
        });
    }
    catch (Exception e)
    {
        failures.Add($"{role}: package inspection failed: {e.GetType().Name}: {e.Message}");
        sounds[role] = JObject.FromObject(new { asset, passed = false, error = e.Message });
    }
}

var report = new
{
    passed = failures.Count == 0,
    scope = "Static native packages and cooked SoundWave audit; no in-game audio validation",
    sounds,
    container_id = id,
    installed_containers_discovered = installed.Length,
    installed_containers_checked = checkedInstalled.Length,
    excluded_owned_container = excludedOwned,
    conflicts,
    conflict_count = conflicts.Length,
    isolated_files = files,
    isolated_file_count = files.Length,
    expected_isolated_files = expectedFiles,
    script_metadata_utoc = scriptMetadataUtoc,
    script_metadata_utoc_sha256 = Sha256(scriptMetadataUtoc),
    failures,
    runtime_verified = false,
    utoc_sha256 = Sha256(utoc),
    ucas_sha256 = Sha256(Path.ChangeExtension(utoc, ".ucas")),
    pak_sha256 = Sha256(Path.ChangeExtension(utoc, ".pak"))
};
var result = JsonConvert.SerializeObject(report, Formatting.Indented);
File.WriteAllText(output, result + "\n");
Console.WriteLine(result);
return failures.Count == 0 ? 0 : 1;
