import os

def save_tree_to_md():
    # 1. 설정: 저장할 파일명 및 스캔 시작 위치
    output_filename = "project_structure.md"
    
    # 스크립트 파일의 위치(Utility)가 아니라, 프로젝트 루트(python_script)를 기준으로 잡기 위해 상위 폴더(..)로 이동
    # 만약 이 파일을 루트에 두셨다면 base_dir = '.' 로 바꾸시면 됩니다.
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) 
    output_path = os.path.join(base_dir, output_filename)

    # 2. 무시할 폴더 및 파일 (보기 싫은 것들)
    ignore_set = {
        '.git', '.vscode', 'myenv', '__pycache__', 
        '.ipynb_checkpoints', '.DS_Store', '.idea', 
        output_filename, '.gitignore', 'README.md'
    }

    # 3. 파일 작성 시작
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("# 📂 프로젝트 폴더 구조\n\n")
        f.write("```text\n") # 마크다운 코드 블록 시작

        for root, dirs, files in os.walk(base_dir):
            # 무시할 폴더들을 탐색 목록에서 제외
            dirs[:] = [d for d in dirs if d not in ignore_set]
            
            # 들여쓰기 계산
            level = root.replace(base_dir, '').count(os.sep)
            indent = ' ' * 4 * level
            
            # 폴더명 기록 (루트 폴더 이름은 제외하고 싶으면 level 0일 때 조건 추가 가능)
            folder_name = os.path.basename(root)
            f.write(f'{indent}📂 {folder_name}/\n')
            
            # 파일명 기록
            subindent = ' ' * 4 * (level + 1)
            for file in files:
                if file not in ignore_set and not file.endswith('.pyc'):
                    f.write(f'{subindent}📄 {file}\n')
        
        f.write("```\n") # 마크다운 코드 블록 끝

    print(f"✅ 저장 완료! '{output_path}' 파일이 생성되었습니다.")

if __name__ == '__main__':
    save_tree_to_md()
