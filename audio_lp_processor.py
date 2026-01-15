"""
Audio LP Effect Processor
오디오 파일에 LP(레코드판) 효과를 적용하는 프로그램
"""

import os
import sys
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
import shutil


# ==================== 상수 정의 ====================
SUPPORTED_INPUT_FORMATS = {".wav", ".flac", ".mp3", ".m4a", ".aac", ".ogg"}

EFFECT_PRESETS = {
    "1": {
        "label": "Piano/Modern",
        "speed": 0.98,
        "cutoff": 14000,
        "sat": 4,
        "wf_rate": 0.6,
        "wf_depth": 0.015,
        "crackle_amt": 0,
        "crackle_cps": 0
    },
    "2": {
        "label": "Hardbop/Brass",
        "speed": 0.97,
        "cutoff": 12000,
        "sat": 6,
        "wf_rate": 0.7,
        "wf_depth": 0.02,
        "crackle_amt": 0.0012,
        "crackle_cps": 0.8
    },
    "3": {
        "label": "Vocal Jazz",
        "speed": 0.99,
        "cutoff": 11000,
        "sat": 6,
        "wf_rate": 0,
        "wf_depth": 0,
        "crackle_amt": 0.0018,
        "crackle_cps": 1.2
    },
    "4": {
        "label": "Fusion/Electric",
        "speed": 0.96,
        "cutoff": 10000,
        "sat": 9,
        "wf_rate": 0.9,
        "wf_depth": 0.03,
        "crackle_amt": 0,
        "crackle_cps": 0
    }
}


# ==================== 오디오 입출력 함수 ====================
def load_audio_any(file_path):
    """
    다양한 포맷의 오디오 파일을 로드
    
    Args:
        file_path: 오디오 파일 경로
        
    Returns:
        tuple: (오디오 데이터 배열, 샘플레이트)
    """
    try:
        audio_data, sample_rate = sf.read(file_path, always_2d=True)
        return audio_data.astype(np.float32), sample_rate
    except Exception:
        # soundfile로 읽기 실패 시 pydub 사용 (ffmpeg 필요)
        segment = AudioSegment.from_file(file_path)
        sample_rate = segment.frame_rate
        channels = segment.channels
        
        audio_array = np.array(segment.get_array_of_samples()).astype(np.float32)
        
        if channels > 1:
            audio_array = audio_array.reshape((-1, channels))
        else:
            audio_array = audio_array.reshape((-1, 1))
        
        max_value = float(2 ** (8 * segment.sample_width - 1))
        return (audio_array / max_value).astype(np.float32), sample_rate


def write_wav_24bit(file_path, audio_data, sample_rate):
    """24비트 WAV 파일로 저장"""
    sf.write(file_path, audio_data, sample_rate, subtype="PCM_24")


def write_wav_16bit(file_path, audio_data, sample_rate):
    """16비트 WAV 파일로 저장"""
    sf.write(file_path, audio_data, sample_rate, subtype="PCM_16")


def write_flac(file_path, audio_data, sample_rate):
    """FLAC 파일로 저장"""
    sf.write(file_path, audio_data, sample_rate, subtype="PCM_24")


def write_m4a_alac(file_path, audio_data, sample_rate):
    """M4A (ALAC 무손실) 파일로 저장"""
    audio_int16 = (audio_data * 32767.0).astype(np.int16)
    segment = AudioSegment(
        audio_int16.tobytes(),
        frame_rate=sample_rate,
        sample_width=2,
        channels=audio_data.shape[1]
    )
    segment.export(file_path, format="ipod", parameters=["-c:a", "alac"])


def write_mp3(file_path, audio_data, sample_rate, bitrate="320k"):
    """MP3 파일로 저장"""
    audio_int16 = (audio_data * 32767.0).astype(np.int16)
    segment = AudioSegment(
        audio_int16.tobytes(),
        frame_rate=sample_rate,
        sample_width=2,
        channels=audio_data.shape[1]
    )
    segment.export(file_path, format="mp3", bitrate=bitrate)


# ==================== 메타데이터 처리 ====================
def read_metadata(file_path):
    """
    원본 파일의 모든 메타데이터 읽기
    
    Args:
        file_path: 파일 경로
        
    Returns:
        dict: 메타데이터 딕셔너리 (포맷별 원본 객체 포함)
    """
    try:
        audio = MutagenFile(file_path)
        if audio is None:
            return None
        
        metadata = {
            'tags': {},
            'audio_object': audio,
            'format': type(audio).__name__
        }
        
        # 모든 태그 복사
        if hasattr(audio, 'tags') and audio.tags:
            for key in audio.tags.keys():
                try:
                    metadata['tags'][key] = audio.tags[key]
                except:
                    pass
        
        # FLAC의 경우 직접 키-값 접근
        if isinstance(audio, FLAC):
            for key in audio.keys():
                metadata['tags'][key] = audio[key]
        
        # MP4의 경우
        elif isinstance(audio, MP4):
            for key in audio.keys():
                metadata['tags'][key] = audio[key]
        
        return metadata
        
    except Exception as e:
        return None


def copy_metadata(source_path, dest_path, new_title=None):
    """
    원본 파일의 메타데이터를 대상 파일로 복사
    
    Args:
        source_path: 원본 파일 경로
        dest_path: 대상 파일 경로
        new_title: 새로운 제목 (None이면 원본 유지)
    """
    source_metadata = read_metadata(source_path)
    if not source_metadata or not source_metadata['tags']:
        # 메타데이터가 없으면 제목만 설정
        if new_title:
            set_title_tag(dest_path, new_title)
        return
    
    try:
        dest_audio = MutagenFile(dest_path)
        if dest_audio is None:
            return
        
        source_ext = os.path.splitext(source_path)[1].lower()
        dest_ext = os.path.splitext(dest_path)[1].lower()
        
        # 같은 포맷인 경우 직접 복사
        if source_ext == dest_ext:
            if isinstance(dest_audio, FLAC):
                flac_dest = FLAC(dest_path)
                for key, value in source_metadata['tags'].items():
                    if key != 'title' or not new_title:
                        flac_dest[key] = value
                if new_title:
                    flac_dest['title'] = new_title
                flac_dest.save()
                
            elif isinstance(dest_audio, MP4):
                mp4_dest = MP4(dest_path)
                for key, value in source_metadata['tags'].items():
                    if key != '\xa9nam' or not new_title:
                        mp4_dest[key] = value
                if new_title:
                    mp4_dest['\xa9nam'] = new_title
                mp4_dest.save()
                
            elif hasattr(dest_audio, 'tags'):
                for key, value in source_metadata['tags'].items():
                    try:
                        dest_audio.tags[key] = value
                    except:
                        pass
                if new_title:
                    set_title_tag(dest_path, new_title)
                dest_audio.save()
        
        # 다른 포맷인 경우 공통 태그만 매핑
        else:
            copy_common_metadata(source_metadata['tags'], dest_path, source_ext, dest_ext, new_title)
            
    except Exception as e:
        # 실패시 최소한 제목이라도 설정
        if new_title:
            set_title_tag(dest_path, new_title)


def copy_common_metadata(source_tags, dest_path, source_ext, dest_ext, new_title=None):
    """
    포맷 간 공통 메타데이터 매핑 및 복사
    
    Args:
        source_tags: 원본 태그 딕셔너리
        dest_path: 대상 파일 경로
        source_ext: 원본 파일 확장자
        dest_ext: 대상 파일 확장자
        new_title: 새로운 제목
    """
    # 공통 태그 매핑 테이블
    tag_mapping = {
        'title': {
            '.flac': 'title',
            '.mp3': 'TIT2',
            '.m4a': '\xa9nam',
            '.wav': 'INAM'
        },
        'artist': {
            '.flac': 'artist',
            '.mp3': 'TPE1',
            '.m4a': '\xa9ART',
            '.wav': 'IART'
        },
        'album': {
            '.flac': 'album',
            '.mp3': 'TALB',
            '.m4a': '\xa9alb',
            '.wav': 'IPRD'
        },
        'date': {
            '.flac': 'date',
            '.mp3': 'TDRC',
            '.m4a': '\xa9day',
            '.wav': 'ICRD'
        },
        'genre': {
            '.flac': 'genre',
            '.mp3': 'TCON',
            '.m4a': '\xa9gen',
            '.wav': 'IGNR'
        },
        'albumartist': {
            '.flac': 'albumartist',
            '.mp3': 'TPE2',
            '.m4a': 'aART',
            '.wav': None
        },
        'tracknumber': {
            '.flac': 'tracknumber',
            '.mp3': 'TRCK',
            '.m4a': 'trkn',
            '.wav': None
        },
        'comment': {
            '.flac': 'comment',
            '.mp3': 'COMM',
            '.m4a': '\xa9cmt',
            '.wav': 'ICMT'
        }
    }
    
    try:
        dest_audio = MutagenFile(dest_path)
        
        # 각 공통 태그 처리
        for common_tag, format_map in tag_mapping.items():
            source_key = format_map.get(source_ext)
            dest_key = format_map.get(dest_ext)
            
            if not source_key or not dest_key:
                continue
            
            # 제목은 new_title이 있으면 그것 사용
            if common_tag == 'title' and new_title:
                set_specific_tag(dest_audio, dest_path, dest_ext, dest_key, new_title)
                continue
            
            # 원본에서 값 추출
            value = source_tags.get(source_key)
            if value:
                set_specific_tag(dest_audio, dest_path, dest_ext, dest_key, value)
        
        # 앨범 아트 복사
        copy_album_art(source_tags, dest_audio, dest_path, source_ext, dest_ext)
        
    except Exception as e:
        pass


def set_specific_tag(audio_obj, file_path, file_ext, tag_key, value):
    """특정 포맷의 태그 설정"""
    try:
        if file_ext == '.flac':
            flac = FLAC(file_path)
            flac[tag_key] = str(value) if not isinstance(value, list) else value
            flac.save()
            
        elif file_ext == '.mp3':
            from mutagen.id3 import ID3, TPE1, TALB, TDRC, TCON, TPE2, TRCK, COMM
            id3 = ID3(file_path)
            
            # ID3 프레임 타입에 맞게 설정
            frame_class = {
                'TIT2': TIT2, 'TPE1': TPE1, 'TALB': TALB,
                'TDRC': TDRC, 'TCON': TCON, 'TPE2': TPE2, 'TRCK': TRCK
            }.get(tag_key)
            
            if frame_class:
                id3.add(frame_class(encoding=3, text=str(value)))
            elif tag_key == 'COMM':
                id3.add(COMM(encoding=3, lang='eng', desc='', text=str(value)))
            
            id3.save(file_path, v2_version=3)
            
        elif file_ext == '.m4a':
            mp4 = MP4(file_path)
            if tag_key == 'trkn':
                # 트랙 번호는 튜플 형식
                try:
                    track_num = int(str(value).split('/')[0]) if '/' in str(value) else int(value)
                    mp4[tag_key] = [(track_num, 0)]
                except:
                    pass
            else:
                mp4[tag_key] = [str(value)] if not isinstance(value, list) else value
            mp4.save()
            
    except Exception as e:
        pass


def copy_album_art(source_tags, dest_audio, dest_path, source_ext, dest_ext):
    """앨범 아트 복사"""
    try:
        # FLAC → 다른 포맷
        if source_ext == '.flac' and hasattr(dest_audio, 'tags'):
            if 'APIC:' in source_tags or any(k.startswith('APIC') for k in source_tags.keys()):
                for key, value in source_tags.items():
                    if key.startswith('APIC'):
                        if dest_ext == '.mp3':
                            from mutagen.id3 import APIC
                            id3 = ID3(dest_path)
                            id3.add(value)
                            id3.save(dest_path, v2_version=3)
                        elif dest_ext == '.m4a':
                            mp4 = MP4(dest_path)
                            if hasattr(value, 'data'):
                                mp4['covr'] = [value.data]
                            mp4.save()
        
        # MP3 → 다른 포맷
        elif source_ext == '.mp3':
            for key, value in source_tags.items():
                if key.startswith('APIC'):
                    if dest_ext == '.flac':
                        flac = FLAC(dest_path)
                        flac.add_picture(value)
                        flac.save()
                    elif dest_ext == '.m4a':
                        mp4 = MP4(dest_path)
                        if hasattr(value, 'data'):
                            mp4['covr'] = [value.data]
                        mp4.save()
        
        # M4A → 다른 포맷
        elif source_ext == '.m4a' and 'covr' in source_tags:
            cover_data = source_tags['covr'][0]
            if dest_ext == '.mp3':
                from mutagen.id3 import APIC
                id3 = ID3(dest_path)
                id3.add(APIC(encoding=3, mime='image/jpeg', type=3, desc='Cover', data=bytes(cover_data)))
                id3.save(dest_path, v2_version=3)
            elif dest_ext == '.flac':
                from mutagen.flac import Picture
                flac = FLAC(dest_path)
                picture = Picture()
                picture.data = bytes(cover_data)
                picture.type = 3
                picture.mime = 'image/jpeg'
                flac.add_picture(picture)
                flac.save()
                
    except Exception as e:
        pass


def set_title_tag(file_path, title):
    """
    오디오 파일의 제목 태그 설정 (기존 호환성 유지)
    
    Args:
        file_path: 파일 경로
        title: 설정할 제목
    """
    file_extension = os.path.splitext(file_path)[1].lower()
    
    try:
        if file_extension == ".flac":
            audio = FLAC(file_path)
            audio["title"] = title
            audio.save()
            
        elif file_extension == ".mp3":
            try:
                audio = ID3(file_path)
            except Exception:
                audio = ID3()
            audio.add(TIT2(encoding=3, text=title))
            audio.save(file_path, v2_version=3)
            
        elif file_extension == ".m4a":
            audio = MP4(file_path)
            audio["\xa9nam"] = title
            audio.save()
            
        elif file_extension == ".wav":
            try:
                audio = WAVE(file_path)
                audio["INAM"] = title
                audio.save()
            except Exception:
                pass
                
    except MutagenError:
        pass


# ==================== 오디오 효과 처리 ====================
def build_effect_board(rate_hz, depth, cutoff_hz, drive_db):
    """
    오디오 이펙트 체인 구성
    
    Args:
        rate_hz: 코러스 속도
        depth: 코러스 깊이
        cutoff_hz: 로우패스 필터 차단 주파수
        drive_db: 디스토션 강도
        
    Returns:
        Pedalboard: 구성된 이펙트 체인
    """
    effect_chain = []
    
    # 코러스 효과 추가
    if rate_hz > 0 and depth > 0:
        effect_chain.append(
            Chorus(rate_hz=rate_hz, depth=depth, centre_delay_ms=7.0)
        )
    
    # 디스토션 효과 추가
    if drive_db > 0:
        effect_chain.append(Distortion(drive_db=drive_db))
    
    # 로우패스 필터 (버전 호환성 처리)
    try:
        lowpass = LowpassFilter(cutoff_frequency_hz=cutoff_hz)
    except TypeError:
        lowpass = LowpassFilter(cutoff_hz=cutoff_hz)
    
    # 나머지 이펙트 체인
    effect_chain.extend([
        lowpass,
        Compressor(
            threshold_db=-18,
            ratio=2.0,
            attack_ms=15,
            release_ms=120
        ),
        Gain(gain_db=-1.5)
    ])
    
    return Pedalboard(effect_chain)


def add_crackle_noise(audio_signal, sample_rate, amount=0.0, crackles_per_second=0.0):
    """
    LP 특유의 크래클 노이즈 추가
    
    Args:
        audio_signal: 오디오 신호
        sample_rate: 샘플레이트
        amount: 크래클 강도
        crackles_per_second: 초당 크래클 발생 횟수
        
    Returns:
        numpy.ndarray: 크래클이 추가된 오디오 신호
    """
    if amount <= 0 or crackles_per_second <= 0:
        return audio_signal
    
    num_samples, num_channels = audio_signal.shape
    output = audio_signal.copy()
    
    # 크래클 발생 횟수 계산
    num_crackles = int(crackles_per_second * num_samples / sample_rate)
    
    for _ in range(num_crackles):
        # 랜덤 위치에 크래클 추가
        position = np.random.randint(0, max(1, num_samples - 64))
        
        # 해닝 윈도우로 자연스러운 크래클 생성
        window = np.hanning(64).astype(np.float32)
        window *= (np.random.rand() * 0.6 + 0.4)
        
        output[position:position + 64, :] += (amount * window)[:, None]
    
    return np.clip(output, -1.0, 1.0)


# ==================== 사용자 인터페이스 ====================
def prompt_folder_path():
    """대상 폴더 경로 입력 받기"""
    print("[Folder] 대상 폴더 경로를 입력하세요:")
    return input("> ").strip('"').strip()


def prompt_preset_selection():
    """
    프리셋 또는 커스텀 설정 선택
    
    Returns:
        tuple: (설정 딕셔너리, 커스텀 여부)
    """
    print("\n[Preset] 효과 프리셋을 선택하세요:")
    print("1) Piano/Modern")
    print("2) Hardbop/Brass")
    print("3) Vocal Jazz")
    print("4) Fusion/Electric")
    print("5) Custom")
    
    selection = input("> ").strip()
    
    if selection in EFFECT_PRESETS:
        return EFFECT_PRESETS[selection], False
    else:
        return {}, True


def prompt_output_format():
    """
    출력 포맷 선택
    
    Returns:
        str: 선택된 출력 포맷
    """
    print("\n[Output] 출력 포맷을 선택하세요:")
    print("1) FLAC (무손실)")
    print("2) M4A (ALAC 무손실)")
    print("3) WAV (24bit)")
    print("4) MP3 (320kbps)")
    print("5) Audio-CD (WAV 16bit)")
    
    selection = input("> ").strip()
    
    format_map = {
        "1": "flac",
        "2": "m4a",
        "3": "wav",
        "4": "mp3",
        "5": "cd"
    }
    
    return format_map.get(selection, "flac")


# ==================== 파일 처리 ====================
def process_audio_file(input_path, output_dir, config, output_format):
    """
    개별 오디오 파일 처리
    
    Args:
        input_path: 입력 파일 경로
        output_dir: 출력 디렉토리
        config: 효과 설정
        output_format: 출력 포맷
        
    Returns:
        str: 출력 파일 경로
    """
    # 파일명 추출
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    
    # 오디오 로드
    audio_data, sample_rate = load_audio_any(input_path)
    
    # 속도 조정 (리샘플링)
    speed_ratio = config["speed"]
    processed = resample_poly(
        audio_data,
        int(speed_ratio * 100),
        100,
        axis=0
    ).astype(np.float32)
    
    # 이펙트 체인 적용
    effect_board = build_effect_board(
        config["wf_rate"],
        config["wf_depth"],
        config["cutoff"],
        config["sat"]
    )
    processed = effect_board(processed, sample_rate)
    
    # 크래클 노이즈 추가
    processed = add_crackle_noise(
        processed,
        sample_rate,
        config["crackle_amt"],
        config["crackle_cps"]
    )
    
    # 출력 디렉토리 생성
    os.makedirs(output_dir, exist_ok=True)
    
    # 포맷별 저장
    output_filename = f"LP_{base_name}"
    
    if output_format == "flac":
        output_path = os.path.join(output_dir, f"{output_filename}.flac")
        write_flac(output_path, processed, sample_rate)
        
    elif output_format == "m4a":
        output_path = os.path.join(output_dir, f"{output_filename}.m4a")
        write_m4a_alac(output_path, processed, sample_rate)
        
    elif output_format == "mp3":
        output_path = os.path.join(output_dir, f"{output_filename}.mp3")
        write_mp3(output_path, processed, sample_rate)
        
    else:  # wav 또는 cd
        output_path = os.path.join(output_dir, f"{output_filename}.wav")
        write_wav_24bit(output_path, processed, sample_rate)
    
    # 원본 파일의 모든 메타데이터 복사 (제목은 새로 설정)
    copy_metadata(input_path, output_path, new_title=output_filename)
    
    return output_path


def collect_audio_files(root_folder):
    """
    폴더에서 지원되는 오디오 파일 수집
    
    Args:
        root_folder: 검색할 루트 폴더
        
    Returns:
        list: 오디오 파일 경로 리스트
    """
    audio_files = []
    
    for root, _, files in os.walk(root_folder):
        for filename in files:
            file_extension = os.path.splitext(filename)[1].lower()
            if file_extension in SUPPORTED_INPUT_FORMATS:
                audio_files.append(os.path.join(root, filename))
    
    return audio_files


# ==================== 메인 함수 ====================
def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("Audio LP Effect Processor")
    print("=" * 60)
    
    # 사용자 입력
    source_folder = prompt_folder_path()
    effect_config, is_custom = prompt_preset_selection()
    output_format = prompt_output_format()
    
    # 출력 디렉토리 설정
    output_directory = os.path.join(source_folder, "LP_out")
    
    # 오디오 파일 수집
    target_files = collect_audio_files(source_folder)
    
    if not target_files:
        print("\n처리할 오디오 파일이 없습니다.")
        return
    
    print(f"\n총 {len(target_files)}개 파일 처리 시작...\n")
    
    # 파일 처리
    processed_files = []
    failed_files = []
    
    for file_path in target_files:
        try:
            output_path = process_audio_file(
                file_path,
                output_directory,
                effect_config,
                output_format
            )
            processed_files.append(output_path)
            print(f"[완료] {os.path.basename(file_path)}")
            
        except Exception as error:
            failed_files.append((file_path, str(error)))
            print(f"[실패] {os.path.basename(file_path)} - {error}")
    
    # 결과 요약
    print("\n" + "=" * 60)
    print(f"처리 완료: {len(processed_files)}개")
    print(f"처리 실패: {len(failed_files)}개")
    print(f"출력 위치: {output_directory}")
    print("=" * 60)


if __name__ == "__main__":
    main()
