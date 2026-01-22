import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly
from pedalboard import Pedalboard, Chorus, Distortion, LowpassFilter, Compressor, Gain
from mutagen.flac import FLAC
from mutagen.id3 import ID3, TIT2
from mutagen.mp4 import MP4
from mutagen.wave import WAVE
from mutagen import MutagenError, File as MutagenFile
from pydub import AudioSegment
from nicegui import ui, app, run

# ==================== 상수 및 설정 데이터 ====================
SUPPORTED_INPUT_FORMATS = {".wav", ".flac", ".mp3", ".m4a", ".aac", ".ogg"}

# 프리셋 데이터
PRESETS = {
    "Piano/Modern": {"speed": 0.98, "cutoff": 14000, "sat": 4, "wf_rate": 0.6, "wf_depth": 0.015, "crackle_amt": 0, "crackle_cps": 0},
    "Hardbop/Brass": {"speed": 0.97, "cutoff": 12000, "sat": 6, "wf_rate": 0.7, "wf_depth": 0.02, "crackle_amt": 0.0012, "crackle_cps": 0.8},
    "Vocal Jazz": {"speed": 0.99, "cutoff": 11000, "sat": 6, "wf_rate": 0, "wf_depth": 0, "crackle_amt": 0.0018, "crackle_cps": 1.2},
    "Fusion/Electric": {"speed": 0.96, "cutoff": 10000, "sat": 9, "wf_rate": 0.9, "wf_depth": 0.03, "crackle_amt": 0, "crackle_cps": 0},
}

# 기본 설정값
current_config = {
    "speed": 1.0, "cutoff": 20000, "sat": 0, 
    "wf_rate": 0, "wf_depth": 0, 
    "crackle_amt": 0, "crackle_cps": 0
}

# ==================== 핵심 로직 (기존 코드 유지) ====================
# (기존 load_audio_any, write_*, metadata 관련 함수들은 로직이 동일하므로 그대로 사용합니다.)
# 코드를 간결하게 하기 위해 핵심 처리 함수만 이곳에 포함하고, 
# 실제 사용 시에는 원본 파일의 헬퍼 함수들을 그대로 가져와야 합니다.
# 이 예제에서는 구조적 완결성을 위해 핵심 함수들을 다시 정의합니다.

def load_audio_any(file_path):
    try:
        audio_data, sample_rate = sf.read(file_path, always_2d=True)
        return audio_data.astype(np.float32), sample_rate
    except Exception:
        segment = AudioSegment.from_file(file_path)
        sample_rate = segment.frame_rate
        channels = segment.channels
        audio_array = np.array(segment.get_array_of_samples()).astype(np.float32)
        if channels > 1: audio_array = audio_array.reshape((-1, channels))
        else: audio_array = audio_array.reshape((-1, 1))
        max_value = float(2 ** (8 * segment.sample_width - 1))
        return (audio_array / max_value).astype(np.float32), sample_rate

def build_effect_board(rate_hz, depth, cutoff_hz, drive_db):
    effect_chain = []
    if rate_hz > 0 and depth > 0:
        effect_chain.append(Chorus(rate_hz=rate_hz, depth=depth, centre_delay_ms=7.0))
    if drive_db > 0:
        effect_chain.append(Distortion(drive_db=drive_db))
    try:
        lowpass = LowpassFilter(cutoff_frequency_hz=cutoff_hz)
    except TypeError:
        lowpass = LowpassFilter(cutoff_hz=cutoff_hz)
    effect_chain.extend([lowpass, Compressor(threshold_db=-18, ratio=2.0, attack_ms=15, release_ms=120), Gain(gain_db=-1.5)])
    return Pedalboard(effect_chain)

def add_crackle_noise(audio_signal, sample_rate, amount=0.0, crackles_per_second=0.0):
    if amount <= 0 or crackles_per_second <= 0: return audio_signal
    num_samples, num_channels = audio_signal.shape
    output = audio_signal.copy()
    num_crackles = int(crackles_per_second * num_samples / sample_rate)
    for _ in range(num_crackles):
        position = np.random.randint(0, max(1, num_samples - 64))
        window = np.hanning(64).astype(np.float32) * (np.random.rand() * 0.6 + 0.4)
        output[position:position + 64, :] += (amount * window)[:, None]
    return np.clip(output, -1.0, 1.0)

# 저장 및 메타데이터 복사 함수는 원본 코드의 것을 사용한다고 가정하고 간소화하여 작성합니다.
# 실제 실행 시에는 원본 파일의 write_* 함수들과 copy_metadata 함수를 모두 포함시켜야 합니다.
def save_processed_file(file_path, processed, sample_rate, output_format, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    output_filename = f"LP_{base_name}"
    
    # 원본 코드의 저장 로직 매핑
    out_path = os.path.join(output_dir, f"{output_filename}.{output_format if output_format != 'cd' else 'wav'}")
    
    # 포맷별 저장 (약식 구현 - 원본 함수의 전체 로직 필요)
    subtype = "PCM_16" if output_format == "cd" else "PCM_24"
    if output_format in ["flac", "wav", "cd"]:
        sf.write(out_path, processed, sample_rate, subtype=subtype)
    elif output_format == "mp3":
        # MP3 저장은 pydub 필요 (원본 코드 참조)
        audio_int16 = (processed * 32767.0).astype(np.int16)
        seg = AudioSegment(audio_int16.tobytes(), frame_rate=sample_rate, sample_width=2, channels=processed.shape[1])
        seg.export(out_path, format="mp3", bitrate="320k")
    elif output_format == "m4a":
        # M4A 저장 (원본 코드 참조)
        audio_int16 = (processed * 32767.0).astype(np.int16)
        seg = AudioSegment(audio_int16.tobytes(), frame_rate=sample_rate, sample_width=2, channels=processed.shape[1])
        seg.export(out_path, format="ipod", parameters=["-c:a", "alac"])

    return out_path

# ==================== NiceGUI UI 로직 ====================

def select_folder():
    """Tkinter를 사용하여 폴더 선택 다이얼로그를 띄웁니다."""
    root = tk.Tk()
    root.withdraw()  # 메인 윈도우 숨김
    root.attributes('-topmost', True)  # 창을 최상단으로
    folder_path = filedialog.askdirectory()
    root.destroy()
    if folder_path:
        folder_input.value = folder_path
        status_log.push(f"폴더 선택됨: {folder_path}")

def update_sliders_from_preset(e):
    """프리셋 선택 시 슬라이더 값을 업데이트합니다."""
    preset_name = e.value
    if preset_name in PRESETS:
        vals = PRESETS[preset_name]
        speed_slider.value = vals['speed']
        cutoff_slider.value = vals['cutoff']
        sat_slider.value = vals['sat']
        wfr_slider.value = vals['wf_rate']
        wfd_slider.value = vals['wf_depth']
        amt_slider.value = vals['crackle_amt']
        cps_slider.value = vals['crackle_cps']
        status_log.push(f"프리셋 적용: {preset_name}")

async def run_processing():
    """오디오 처리를 실행합니다."""
    source_folder = folder_input.value
    if not source_folder or not os.path.exists(source_folder):
        ui.notify('유효한 폴더를 선택해주세요.', type='warning')
        return

    target_files = []
    for root, _, files in os.walk(source_folder):
        for filename in files:
            if os.path.splitext(filename)[1].lower() in SUPPORTED_INPUT_FORMATS:
                target_files.append(os.path.join(root, filename))

    if not target_files:
        ui.notify('처리할 오디오 파일이 없습니다.', type='warning')
        return

    output_dir = os.path.join(source_folder, "LP_out")
    output_fmt = format_select.value
    
    # UI 비활성화 및 진행바 표시
    process_btn.disable()
    spinner.set_visibility(True)
    progress_bar.visible = True
    progress_bar.value = 0.0
    
    total = len(target_files)
    success_count = 0
    
    status_log.push(f"=== 처리 시작: 총 {total}개 파일 ===")
    
    # 블로킹 연산이므로 run.cpu_bound 사용 고려, 여기선 간단히 루프 내 await sleep으로 UI 갱신
    for i, file_path in enumerate(target_files):
        try:
            filename = os.path.basename(file_path)
            status_log.push(f"처리 중 ({i+1}/{total}): {filename}")
            
            # 현재 슬라이더 값 읽기
            config = {
                "speed": speed_slider.value,
                "cutoff": cutoff_slider.value,
                "sat": sat_slider.value,
                "wf_rate": wfr_slider.value,
                "wf_depth": wfd_slider.value,
                "crackle_amt": amt_slider.value,
                "crackle_cps": cps_slider.value
            }

            # 비동기 환경에서 무거운 작업을 실행하기 위해 run.io_bound 또는 run.cpu_bound 사용 권장
            # 여기서는 UI 반응성을 위해 NiceGUI의 run.cpu_bound 활용
            def process_single():
                audio_data, sample_rate = load_audio_any(file_path)
                
                # Resample
                processed = resample_poly(audio_data, int(config["speed"] * 100), 100, axis=0).astype(np.float32)
                
                # Effects
                board = build_effect_board(config["wf_rate"], config["wf_depth"], config["cutoff"], config["sat"])
                processed = board(processed, sample_rate)
                
                # Crackle
                processed = add_crackle_noise(processed, sample_rate, config["crackle_amt"], config["crackle_cps"])
                
                # Save
                return save_processed_file(file_path, processed, sample_rate, output_fmt, output_dir)

            # 별도 스레드에서 실행하여 UI 멈춤 방지
            await run.cpu_bound(process_single)
            
            # 메타데이터 복사는 여기서 생략되었으나 원본 함수 호출 필요
            # copy_metadata(file_path, output_path, ...)
            
            success_count += 1
            progress_bar.value = (i + 1) / total
            
        except Exception as e:
            status_log.push(f"[에러] {filename}: {str(e)}")
            print(e)
            
    status_log.push(f"=== 완료: {success_count}개 성공, 저장위치: {output_dir} ===")
    ui.notify(f'작업 완료! {output_dir}를 확인하세요.', type='positive')
    
    process_btn.enable()
    spinner.set_visibility(False)
    progress_bar.visible = False

# ==================== UI 레이아웃 구성 ====================

with ui.column().classes('w-full max-w-3xl mx-auto p-4 gap-4'):
    # 헤더
    ui.markdown('## 🎵 Audio LP Effect Processor').classes('text-center w-full')

    # 1. 파일 및 포맷 설정 카드
    with ui.card().classes('w-full'):
        ui.label('1. 파일 및 출력 설정').classes('text-lg font-bold')
        
        with ui.row().classes('w-full items-center'):
            folder_input = ui.input('대상 폴더 경로').classes('flex-grow')
            ui.button(icon='folder', on_click=select_folder).props('flat round')
            
        format_select = ui.select(
            options={'flac': 'FLAC (무손실)', 'm4a': 'M4A (ALAC)', 'mp3': 'MP3 (320k)', 'wav': 'WAV (24bit)', 'cd': 'CD (16bit)'},
            value='flac', label='출력 포맷'
        ).classes('w-full')

    # 2. 효과 설정 카드
    with ui.card().classes('w-full'):
        ui.label('2. 효과 설정 (Presets & Custom)').classes('text-lg font-bold')
        
        # 프리셋 선택
        ui.select(
            options=list(PRESETS.keys()), 
            label='프리셋 선택 (선택 시 아래 값이 자동 변경됨)',
            on_change=update_sliders_from_preset
        ).classes('w-full mb-4')
        
        with ui.grid(columns=2).classes('w-full gap-4'):
            # Speed & Cutoff
            with ui.column():
                ui.label('Speed (Playback Rate)')
                speed_slider = ui.slider(min=0.8, max=1.2, step=0.01, value=1.0).props('label-always')
            with ui.column():
                ui.label('Lowpass Cutoff (Hz)')
                cutoff_slider = ui.slider(min=1000, max=20000, step=100, value=20000).props('label-always')

            # Saturation & Wow/Flutter Rate
            with ui.column():
                ui.label('Saturation (Drive dB)')
                sat_slider = ui.slider(min=0, max=20, step=0.5, value=0).props('label-always')
            with ui.column():
                ui.label('Wow/Flutter Rate (Hz)')
                wfr_slider = ui.slider(min=0, max=5, step=0.1, value=0).props('label-always')

            # Wow/Flutter Depth & Crackle Amount
            with ui.column():
                ui.label('Wow/Flutter Depth')
                wfd_slider = ui.slider(min=0, max=0.1, step=0.001, value=0).props('label-always')
            with ui.column():
                ui.label('Crackle Amount')
                amt_slider = ui.slider(min=0, max=0.01, step=0.0001, value=0).props('label-always')
            
            # Crackle CPS
            with ui.column().classes('col-span-2'):
                ui.label('Crackle Rate (CPS)')
                cps_slider = ui.slider(min=0, max=5, step=0.1, value=0).props('label-always')

    # 3. 실행 및 로그
    with ui.card().classes('w-full'):
        process_btn = ui.button('변환 시작', on_click=run_processing, icon='play_arrow').classes('w-full h-12 text-lg')
        
        progress_bar = ui.linear_progress(value=0).classes('mt-4').props('instant-feedback')
        progress_bar.visible = False
        
        spinner = ui.spinner(size='lg').classes('self-center mt-2')
        spinner.set_visibility(False)
        
        ui.separator().classes('my-4')
        ui.label('작업 로그').classes('text-sm text-gray-500')
        status_log = ui.log().classes('w-full h-40 bg-gray-100 p-2 rounded')

ui.run(title='LP Effect Processor', port=8080, reload=False)