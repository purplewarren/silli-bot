"""
Audio analysis pipeline for voice notes.
Converts Telegram voice notes to WAV, extracts features, and provides scoring.
"""

import os
import tempfile
import asyncio
import subprocess
import shutil
import numpy as np
import librosa
import soundfile as sf
import ffmpeg
from typing import Tuple, Dict, Any
from loguru import logger
from .models import FeatureSummary
from .scoring import WindDownScorer

FFMPEG = shutil.which("ffmpeg") or "ffmpeg"


async def _dl_with_retry(bot, file_id: str, out_path: str, tries: int = 3) -> str:
    """Download voice file from Telegram with retries."""
    for i in range(tries):
        try:
            tgfile = await bot.get_file(file_id)
            await bot.download_file(tgfile.file_path, out_path)
            logger.info(f"Downloaded voice file to {out_path}")
            return out_path
        except Exception as e:
            if i == tries - 1:
                logger.error(f"Error downloading voice file after {tries} tries: {e}")
                raise
            logger.warning(f"Download attempt {i+1} failed, retrying...")
            await asyncio.sleep(0.5 * (2 ** i))

async def download_voice_file(bot, file_id: str) -> str:
    """Download voice file from Telegram and return local path."""
    # Create temp file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.ogg')
    temp_path = temp_file.name
    temp_file.close()
    
    return await _dl_with_retry(bot, file_id, temp_path)


def _ffmpeg_wav(src: str, dst: str) -> str:
    """Convert audio to WAV using explicit ffmpeg flags."""
    try:
        cmd = [FFMPEG, "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
               "-i", str(src), "-ac", "1", "-ar", "16000", str(dst)]
        subprocess.run(cmd, check=True)
        logger.info(f"Converted {src} to {dst}")
        return dst
    except Exception as e:
        logger.error(f"Error converting to WAV: {e}")
        raise

def to_wav(input_path: str) -> str:
    """Convert OGG to 16k mono WAV using ffmpeg."""
    # Create output path
    output_path = input_path.replace('.ogg', '.wav')
    return _ffmpeg_wav(input_path, output_path)


def extract_features(wav_path: str) -> FeatureSummary:
    """Extract audio features using librosa."""
    try:
        # Load audio
        y, sr = librosa.load(wav_path, sr=16000)

        # Guard: too short or effectively silent clip -> return safe defaults
        if len(y) < int(0.2 * sr) or np.max(np.abs(y)) < 1e-5:
            return FeatureSummary(
                level_dbfs=float(-80.0),
                centroid_norm=0.0,
                rolloff_norm=0.0,
                flux_norm=0.0,
                vad_fraction=0.0,
                stationarity=1.0
            )

        features = {}

        # RMS level (dBFS)
        rms = librosa.feature.rms(y=y)
        level_dbfs = 20 * np.log10(np.mean(rms) + 1e-10)
        features['level_dbfs'] = float(level_dbfs)

        # Spectral centroid
        centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
        features['centroid_norm'] = float(np.clip(np.mean(centroid) / (sr/2), 0.0, 1.0))

        # Spectral rolloff
        rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)
        features['rolloff_norm']  = float(np.clip(np.mean(rolloff)  / (sr/2), 0.0, 1.0))

        # Spectral flux (true frame-to-frame magnitude change)
        S = np.abs(librosa.stft(y, n_fft=1024, hop_length=512, center=True))
        if S.shape[1] > 1:
            delta = np.diff(S, axis=1)
            flux = np.sqrt((delta ** 2).sum(axis=0)) / (S.shape[0] ** 0.5)
            # Normalize by average magnitude to keep ~0..1 range
            norm = np.mean(S) + 1e-8
            features['flux_norm'] = float(np.clip(np.mean(flux) / norm, 0.0, 1.0))
        else:
            features['flux_norm'] = 0.0

        # Voice Activity Detection (simplified)
        # Use energy-based VAD
        frame_length = int(0.025 * sr)  # 25ms frames
        hop_length = int(0.010 * sr)    # 10ms hop

        # Calculate frame energy
        frames = librosa.util.frame(y, frame_length=frame_length, hop_length=hop_length)
        frame_energy = np.sum(frames**2, axis=0)

        # Simple threshold-based VAD
        threshold = np.percentile(frame_energy, 30)  # 30th percentile as threshold
        abs_floor = 1e-6  # prevent false speech in ultra-quiet rooms
        threshold = max(threshold, abs_floor)
        vad_frames = frame_energy > threshold
        features['vad_fraction'] = float(np.sum(vad_frames) / len(vad_frames))

        # Stationarity (variance of spectral features over time)
        # Use centroid variance as stationarity measure
        centroid_var = np.var(centroid)
        centroid_mean = np.mean(centroid)
        features['stationarity'] = float(1.0 / (1.0 + centroid_var / (centroid_mean + 1e-10)))

        logger.info(f"Extracted features: {features}")
        return FeatureSummary(**features)

    except Exception as e:
        logger.error(f"Error extracting features: {e}")
        raise


async def process_voice_note(bot, file_id: str, family_id: str, session_id: str) -> Tuple[Dict[str, Any], str]:
    """
    Process a voice note: download, convert, analyze, score, and generate card.
    Returns (analysis_result, card_path).
    """
    temp_files = []
    
    try:
        # Download voice file
        ogg_path = await download_voice_file(bot, file_id)
        temp_files.append(ogg_path)
        
        # Convert to WAV
        wav_path = to_wav(ogg_path)
        temp_files.append(wav_path)
        
        # Extract features
        features = extract_features(wav_path)
        
        # Score and get tips
        scorer = WindDownScorer()
        score, badges, tips = scorer.score_and_tips(features)
        
        # Generate summary card
        card_path = f"data/cards/{session_id}_card.png"
        os.makedirs(os.path.dirname(card_path), exist_ok=True)
        
        from .cards import render_summary_card
        render_summary_card(score, badges, tips, card_path)
        
        # Prepare result
        result = {
            'score': score,
            'badges': badges,
            'tips': tips,
            'features': features.dict(),
            'family_id': family_id,
            'session_id': session_id
        }
        
        logger.info(f"Processed voice note: score={score}, badges={badges}")
        return result, card_path
        
    finally:
        # Cleanup temp files unless KEEP_RAW_MEDIA is set
        if os.getenv('KEEP_RAW_MEDIA', 'false').lower() != 'true':
            for temp_file in temp_files:
                try:
                    if os.path.exists(temp_file):
                        os.unlink(temp_file)
                        logger.info(f"Cleaned up {temp_file}")
                except Exception as e:
                    logger.warning(f"Could not clean up {temp_file}: {e}")
        else:
            logger.info("KEEP_RAW_MEDIA=true, preserving temp files") 