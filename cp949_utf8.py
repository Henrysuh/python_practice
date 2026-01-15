print("깨진 텍스트를 입력하세요 (빈 줄에서 종료):")

lines = []
while True:
    line = input()
    if line == "":
        break
    lines.append(line)

text = "\n".join(lines)

try:
    fixed = text.encode("latin1").decode("cp949")
    print("\n복원 결과:\n")
    print(fixed)
except UnicodeError as e:
    print("복원 실패:", e)