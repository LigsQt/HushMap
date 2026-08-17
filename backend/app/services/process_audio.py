import numpy as np 
from scipy import signal 
import math 
import struct 

# --- Microphone Characteristics (Match ESP32) ---
MIC_SENSITIVITY = -26.0
MIC_REF_DB = 94.0
MIC_OFFSET_DB = 3.0103
MIC_BITS = 24
MAX_AMP_24BIT = (1 << (MIC_BITS - 1)) - 1
MIC_REF_AMPL = pow(10.0, MIC_SENSITIVITY / 20.0) * MAX_AMP_24BIT
MIC_NOISE_DBA = 30.0
MIC_OVERLOAD_DB = 116.0

# --- IIR Filter Definitions ---
inmp441_gain = 1.00197834654696
inmp441_sos = np.array([
    [1.0, -1.986920458344451, 0.986963226946616, 1.0, -1.995178510504166, 0.995184322194091]
])
a_weighting_gain = 0.169994948147430
a_weighting_sos = np.array([
    [1.0, -2.00026996133106 , 1.00027056142719 , 1.0, 1.060868438509278 , 0.163987445885926],
    [1.0,  4.35912384203144 , 3.09120265783884 , 1.0, -1.208419926363593, 0.273166998428332],
    [1.0, -0.70930303489759 ,-0.29071868393580 , 1.0, -1.982242159753048, 0.982298594928989]
])

def apply_filters(audio_chunk_np, eq_zi, w_zi):
    """Applies Equalizer and Weighting filters sequentially."""
    audio_float = audio_chunk_np.astype(np.float64) / (1 << (32 - MIC_BITS))
    equalized_audio, eq_zf = signal.sosfilt(inmp441_sos, audio_float, zi=eq_zi)
    equalized_audio *= inmp441_gain
    weighted_audio, w_zf = signal.sosfilt(a_weighting_sos, equalized_audio, zi=w_zi)
    weighted_audio *= a_weighting_gain
    return weighted_audio, eq_zf, w_zf

def calculate_dba(weighted_audio_chunk):
    """Calculates the A-weighted dB level."""
    if len(weighted_audio_chunk) == 0: return -np.inf
    weighted_audio_chunk = weighted_audio_chunk.astype(np.float64)
    rms = np.sqrt(np.mean(np.square(weighted_audio_chunk)))
    if rms <= 0: return MIC_NOISE_DBA
    dba_level = MIC_OFFSET_DB + MIC_REF_DB + 20 * math.log10(rms / MIC_REF_AMPL)
    if dba_level < MIC_NOISE_DBA: dba_level = MIC_NOISE_DBA
    elif dba_level > MIC_OVERLOAD_DB: dba_level = MIC_OVERLOAD_DB
    return dba_level


def process_audio(SAMPLES_PER_LEQ, buffered_audio: bytes):
    eq_zi = signal.sosfilt_zi(inmp441_sos) * 0.0
    w_zi = signal.sosfilt_zi(a_weighting_sos) * 0.0
    AUDIO_FORMAT_NP = np.int32

    chunk_bytes_for_leq = buffered_audio[:SAMPLES_PER_LEQ*4]

     # Unpack this chunk *only* for dBA calculation
    format_string = f'<{SAMPLES_PER_LEQ}i'
    try:
        current_chunk_np = np.array(struct.unpack(format_string, chunk_bytes_for_leq), dtype=AUDIO_FORMAT_NP)
    except struct.error as e:
        print(f"Struct unpack error for dBA calc: {e}. Len bytes: {len(buffered_audio)}, Expected: {SAMPLES_PER_LEQ*4}") # 4 is the SAMPLE WIDTH
        # Skip dBA calculation for this chunk if unpack fails
        pass

    # Apply Filters
    weighted_chunk, eq_zi, w_zi = apply_filters(current_chunk_np, eq_zi, w_zi)

    # Calculate dB Level
    dba = calculate_dba(weighted_chunk)
    return dba 
