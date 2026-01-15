# Image to SVG

vtracer_script_auto.py
pip install vtracer
하나의 폴더에 JPG file 여러 개를 두고, SVG로 한 번에 변환
먼저 이미지가 있는 파일을 준비하고, SVG가 저장될 폴더를 생성하는 것이 적절함
from png, jpg, bmp, gif, webp 가능

```
# vtracer_script_auto.py
# pip install vtracer

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
```
# 
### 경로 설정시 엔터 치는 부분

```
        hint = ""
        if last_input_path:
            hint = f" (엔터만 치면 마지막 파일: {os.path.basename(last_input_path)})"
        input_path = input(f"변환할 이미지 파일 경로를 입력하세요{hint}: ").strip().strip('"\'')
```

### 1. hint = ""
* 먼저 hint라는 변수에 빈 문자열("")을 넣어둡니다.
* 이 변수는 사용자에게 보여줄 **추가 안내 문구**를 저장하기 위한 용도예요.
* 처음에는 아무 안내도 하지 않도록 빈 문자열로 시작합니다.

⠀2. if last_input_path:
* last_input_path는 이전에 성공적으로 변환했던 이미지 파일의 경로를 기억하고 있는 변수예요.
* 이 변수에 값이 있으면 (즉, 이전에 한 번이라도 변환을 성공했다면) True로 평가됩니다.
* 값이 없으면 (첫 번째 실행일 때) False가 되어 if 문 안으로 들어가지 않습니다.

⠀3. hint = f" (엔터만 치면 마지막 파일: {os.path.basename(last_input_path)})"
* 이전에 변환했던 파일이 있다면, 사용자에게 편리한 안내 문구를 만들어 줍니다.
* 예시: (엔터만 치면 마지막 파일: vecteezy_pochacco-cute-photo_52877118.jpg)
* os.path.basename(last_input_path) 부분 설명:
  * last_input_path가 전체 경로라면 (예: /Users/kyunghosuh/Documents/image/vecteezy_pochacco-cute-photo_52877118.jpg)
  * os.path.basename()은 그 경로에서 **파일 이름만** 추출해 줍니다.
  * 결과: vecteezy_pochacco-cute-photo_52877118.jpg만 가져와서 화면에 깔끔하게 보여줍니다.

⠀4. input_path = input(f"변환할 이미지 파일 경로를 입력하세요{hint}: ").strip().strip('"\'')
* 실제로 사용자에게 입력을 받는 부분입니다.
* 보여지는 메시지 예시:
  * 첫 번째 실행 → 변환할 이미지 파일 경로를 입력하세요: 
  * 두 번째부터 → 변환할 이미지 파일 경로를 입력하세요 (엔터만 치면 마지막 파일: pochacco.jpg): 
* {hint} 부분에 위에서 만든 안내 문구가 들어가서 상황에 따라 다르게 표시됩니다.
* .strip(): 입력 양 끝의 공백(스페이스, 엔터 등)을 제거합니다.
* .strip('"\''): 만약 사용자가 경로를 복사해서 붙여넣을 때 생기는 따옴표("나 ')를 자동으로 제거해 줍니다. → 예: "/Users/xxx/image.jpg" → "/Users/xxx/image.jpg" (따옴표 사라짐)

⠀요약: 이 코드가 하는 일
사용자에게 이미지 파일 경로를 물어볼 때,
* **첫 번째**에는 그냥 경로 입력하라고만 물어봄
* **두 번째부터**는 “엔터만 치면 이전에 했던 그 파일 다시 변환할게요!”라고 친절하게 안내해 줌
* 파일 이름만 보여주고, 불필요한 공백이나 따옴표는 자동 정리
