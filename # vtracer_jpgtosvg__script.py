# vtracer_script_auto.py
# pip install vtracer
# pochacco와 같이 간단한 그림을 변환하는데 적절함
# 하나의 폴더에 JPG file 여러 개를 두고, SVG로 한 번에 변환
# 먼저 이미지가 있는 파일을 준비하고, SVG가 저장될 폴더를 생성하는 것이 적절함
# from png, jpg, bmp, gif, webp 가능

import os
import vtracer

# 마지막으로 성공한 입력 파일을 기억하기 위한 변수 (스크립트 실행 중 유지)
last_input_path = None

def main():
    global last_input_path
    print("PNG/JPG 이미지를 SVG로 변환하는 스크립트입니다.\n")
    
    while True:  # 무한 루프로 여러 파일 연속 변환 가능 (Ctrl+C로 종료)
        # 입력 파일 경로
        hint = ""
        if last_input_path:
            hint = f" (엔터만 치면 마지막 파일: {os.path.basename(last_input_path)})"
        
        input_path = input(f"변환할 이미지 파일 경로를 입력하세요{hint}: ").strip().strip('"\'')
        
        # 엔터만 친 경우 마지막 파일 사용
        if not input_path and last_input_path:
            input_path = last_input_path
            print(f"마지막 파일 사용: {input_path}")
        elif not input_path:
            print("첫 번째 파일이므로 경로를 입력해야 합니다.")
            continue
        
        if not os.path.isfile(input_path):
            print(f"오류: '{input_path}' 파일을 찾을 수 없습니다. 다시 입력해주세요.\n")
            continue
        
        # 출력 파일 경로
        default_output = os.path.splitext(input_path)[0] + ".svg"
        output_hint = f" (기본: {default_output})"
        if last_output_dir := os.path.dirname(default_output):
            output_hint += f" 또는 폴더만 입력 가능"
        
        output_path = input(f"출력 SVG 파일 경로를 입력하세요{output_hint}: ").strip().strip('"\'')
        
        if not output_path:
            output_path = default_output
        
        # 출력이 폴더만 지정된 경우
        if os.path.isdir(output_path):
            filename = os.path.splitext(os.path.basename(input_path))[0] + ".svg"
            output_path = os.path.join(output_path, filename)
        
        # 출력 디렉토리 생성
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        print("\n변환 중입니다... (이미지 크기에 따라 시간이 걸릴 수 있습니다)")
        
        try:
            vtracer.convert_image_to_svg_py(
                input_path,
                output_path,
                colormode='color',
                hierarchical='stacked',
                mode='spline',
                filter_speckle=4,
                color_precision=6,
                layer_difference=16,
                corner_threshold=60,
                length_threshold=4.0,
                max_iterations=10,
                splice_threshold=45,
                path_precision=8
            )
            
            print(f"\n완료! SVG 파일이 저장되었습니다: {output_path}\n")
            
            # 성공 시 마지막 입력 경로 기억
            last_input_path = input_path
            
        except Exception as e:
            print(f"\n변환 중 오류가 발생했습니다: {e}\n")
        
        # 계속할지 물어보기
        cont = input("다른 이미지 변환하시겠습니까? (엔터: 계속, n: 종료): ").strip().lower()
        if cont == 'n':
            break

    print("스크립트를 종료합니다.")

if __name__ == "__main__":
    main()