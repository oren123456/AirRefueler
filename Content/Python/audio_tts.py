"""Tanker radio calls via the Windows built-in speech synthesizer -> Saved/ClaudeShots/tts/*.wav (raw; radio-filtered
offline by Tools/cockpit_audio.py). Lists installed voices to the log."""
import unreal, subprocess, os
root = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
out = os.path.join(root, "Saved", "ClaudeShots", "tts"); os.makedirs(out, exist_ok=True)
calls = {"cleared_contact": "Cleared contact.", "contact": "Contact.", "disconnect": "Disconnect."}
ps = ["Add-Type -AssemblyName System.Speech", "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer",
      "$s.GetInstalledVoices() | ForEach-Object { 'VOICE ' + $_.VoiceInfo.Name + ' ' + $_.VoiceInfo.Gender + ' ' + $_.VoiceInfo.Culture }",
      "try { $s.SelectVoiceByHints([System.Speech.Synthesis.VoiceGender]::Male) } catch {}", "$s.Rate = 1",
      "$f = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(22050, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono)"]
for k, v in calls.items():
    ps += ["$s.SetOutputToWaveFile('%s', $f)" % os.path.join(out, k + ".wav").replace("\\", "/"), "$s.Speak('%s')" % v, "$s.SetOutputToNull()"]
ps += ["'USED ' + $s.Voice.Name", "$s.Dispose()"]
r = subprocess.run(["powershell", "-NoProfile", "-Command", "; ".join(ps)], capture_output=True, text=True)
unreal.log("[TTS] rc=%d %s %s" % (r.returncode, r.stdout.replace("\n", " | ")[:600], r.stderr[:400]))
unreal.log("[TTS] files %s" % sorted(os.listdir(out)))
