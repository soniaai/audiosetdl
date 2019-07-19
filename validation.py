import json
import os.path
import sox
import soundfile as sf

from errors import FfmpegValidationError, FfmpegIncorrectDurationError, FfmpegUnopenableFileError
from utils import run_command


def ffprobe(ffprobe_path, filepath):
    """
    Run ffprobe to analyse audio or video file

    Args:
        ffprobe_path:  Path to ffprobe executable
                       (Type: str)

        filepath:      Path to audio or video file to analyse
                       (Type: str)

    Returns:
        output:  JSON object returned by ffprobe
                 (Type: JSON comptiable dict)
    """
    cmd_format = '{} -v quiet -print_format json -show_format -show_streams {}'
    cmd = cmd_format.format(ffprobe_path, filepath).split()
    stdout, stderr, retcode = run_command(cmd)
    return json.loads(stdout)


def validate_audio(audio_filepath, audio_info, end_past_video_end=False):
    """
    Take audio file and sanity check basic info.

        Sample output from sox:
            {
                'bitrate': 16,
                'channels': 2,
                'duration': 9.999501,
                'encoding': 'FLAC',
                'num_samples': 440978,
                'sample_rate': 44100.0,
                'silent': False
            }

    Args:
        audio_filepath:   Path to output audio
                          (Type: str)

        audio_info:       Audio info dict
                          (Type: dict[str, *])

    Returns:
        check_passed:  True if sanity check passed
                       (Type: bool)
    """
    if not os.path.exists(audio_filepath):
        error_msg = 'Output file {} does not exist.'.format(audio_filepath)
        raise FfmpegValidationError(error_msg)

    # Check to see if we can open the file
    try:
        sf.read(audio_filepath)
    except Exception as e:
        raise FfmpegUnopenableFileError(audio_filepath, e)

    sox_info = sox.file_info.info(audio_filepath)

    # If duration specifically doesn't match, catch that separately so we can
    # retry with a different duration
    target_duration = audio_info['duration']
    actual_duration = sox_info['num_samples'] / audio_info['sample_rate']
    if target_duration != actual_duration:
        if not(end_past_video_end and actual_duration < target_duration):
            raise FfmpegIncorrectDurationError(audio_filepath, target_duration,
                                               actual_duration)
    for k, v in audio_info.items():
        if k == 'duration' and (end_past_video_end and actual_duration < target_duration):
            continue

        output_v = sox_info[k]
        if output_v == 'Signed Integer PCM':
          output_v = 'PCM_S16LE'

        if v != output_v:
            error_msg = 'Output audio {} should have {} = {}, but got {}.'.format(audio_filepath, k, v, output_v)
            raise FfmpegValidationError(error_msg)
