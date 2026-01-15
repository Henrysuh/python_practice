import re
from pathlib import Path

# 작성 배경: txt파일의 잘못된 엔터를 손으로 고치기가 너무 힘들어서 자동화 방법 검토
# 디지털 데이터의 cleansing으로 이해하면 된디

# 1. 파일 경로 입력
file_path = Path(input("Enter txt file path: ").strip())

# 2. 파일 읽기
with file_path.open("r", encoding="utf-8") as f:
    text = f.read()

# 3. 단일 개행 → 공백 (문단 개행은 유지)
text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)

# 4. 출력 파일 경로 생성
output_path = file_path.with_stem(file_path.stem + "_cleaned")

# 5. 파일 저장
with output_path.open("w", encoding="utf-8") as f:
    f.write(text)

print(f"Saved cleaned file to: {output_path}")
