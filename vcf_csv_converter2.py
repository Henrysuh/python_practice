import vobject
import pandas as pd
import os

def vcard_to_csv(vcf_path, csv_path):
    contacts = []
    with open(vcf_path, "r", encoding="utf-8") as vcf:
        vcard = vobject.readComponents(vcf)
        for contact in vcard:
            # 이름 설정
            first_name = getattr(contact.n.value, "given", "") if hasattr(contact, "n") else ""
            last_name = getattr(contact.n.value, "family", "") if hasattr(contact, "n") else ""
            
            # 전화번호 (최대 2개)
            tels = [tel.value for tel in contact.contents.get("tel", [])]
            phone1 = tels[0] if len(tels) > 0 else ""
            phone2 = tels[1] if len(tels) > 1 else ""

            # 이메일 (최대 2개)
            emails = [email.value for email in contact.contents.get("email", [])]
            email1 = emails[0] if len(emails) > 0 else ""
            email2 = emails[1] if len(emails) > 1 else ""

            # 기타 필드
            org = getattr(contact, "org", None)
            url = getattr(contact, "url", None)
            bday = getattr(contact, "bday", None)
            memo = getattr(contact, "note", None)
            
            # 주소 처리
            address_val = ""
            if hasattr(contact, "adr"):
                adr = contact.adr.value
                address_val = f"{adr.street} {adr.city} {adr.region} {adr.code} {adr.country}".strip()

            contacts.append({
                "First Name": first_name,
                "Last Name": last_name,
                "Phone 1": phone1,
                "Phone 2": phone2,
                "Email 1": email1,
                "Email 2": email2,
                "Organization": org.value[0] if org else "",
                "URL": url.value if url else "",
                "Birthday": bday.value if bday else "",
                "Address": address_val,
                "Memo": memo.value if memo else ""
            })

    df = pd.DataFrame(contacts)
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"✅ CSV 생성 완료: {csv_path}")

def csv_to_vcard(csv_path, vcf_path):
    df = pd.read_csv(csv_path, dtype=str).fillna("")
    
    with open(vcf_path, "w", encoding="utf-8") as vcf:
        for _, row in df.iterrows():
            vcard = vobject.vCard()
            
            # 이름 (N, FN)
            vcard.add('n')
            vcard.n.value = vobject.vcard.Name(family=row["Last Name"], given=row["First Name"])
            vcard.add('fn')
            vcard.fn.value = f"{row['First Name']} {row['Last Name']}".strip()

            # 전화번호
            if row["Phone 1"]:
                vcard.add('tel').value = row["Phone 1"]
                vcard.tel.type_param = "CELL"
            if row["Phone 2"]:
                t2 = vcard.add('tel')
                t2.value = row["Phone 2"]
                t2.type_param = "HOME"

            # 이메일
            if row["Email 1"]:
                vcard.add('email').value = row["Email 1"]
                vcard.email.type_param = "WORK"
            if row["Email 2"]:
                e2 = vcard.add('email')
                e2.value = row["Email 2"]
                e2.type_param = "HOME"

            # 추가 필드
            if row["Organization"]:
                vcard.add('org').value = [row["Organization"]]
            if row["URL"]:
                vcard.add('url').value = row["URL"]
            if row["Birthday"]:
                vcard.add('bday').value = row["Birthday"]
            if row["Address"]:
                vcard.add('adr').value = vobject.vcard.Address(street=row["Address"])
            if row["Memo"]:
                vcard.add('note').value = row["Memo"]

            vcf.write(vcard.serialize())

    print(f"✅ VCF 생성 완료: {vcf_path}")

if __name__ == "__main__":
    mode = input("작업 선택 (1: VCF -> CSV, 2: CSV -> VCF): ").strip()
    
    # 경로 입력 단계
    in_dir = input("입력 폴더 경로 (현재 폴더는 엔터): ").strip() or "."
    in_file = input("입력 파일명 (확장자 포함): ").strip()
    in_path = os.path.join(in_dir, in_file)

    if not os.path.exists(in_path):
        print(f"❌ 파일을 찾을 수 없습니다: {in_path}")
    else:
        out_dir = input("출력 폴더 경로 (현재 폴더는 엔터): ").strip() or "."
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)

        out_file = in_file.rsplit(".", 1)[0] + (".csv" if mode == "1" else ".vcf")
        out_path = os.path.join(out_dir, out_file)

        if mode == "1":
            vcard_to_csv(in_path, out_path)
        else:
            csv_to_vcard(in_path, out_path)