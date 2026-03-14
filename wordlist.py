import random
import itertools
import re
from pathlib import Path
from datetime import datetime

# --- CẤU HÌNH HỆ THỐNG ---
MIN_LEN = 8
MAX_LEN = 64
RESULT_GENERATE = 888  # Số lượng mẫu cho mỗi loại combo
MIN_COMBO = 1          # Ghép tối thiểu 1 từ
MAX_COMBO = 7          # Ghép tối đa 6 từ (7 là giới hạn range)

class WordlistManager:
    def __init__(self, min_len=None, max_len=None):
        self.data_dir = Path("data")
        self.whitelist_path = self.data_dir / "wordlist_whitelist.txt"
        self.blacklist_path = self.data_dir / "wordlist_blacklist.txt"
        self.output_path = self.data_dir / "wordlist.txt"
        
        self.min_len = min_len
        self.max_len = max_len
        self.data_dir.mkdir(exist_ok=True)

    def _read_and_clean(self, file_path):
        """Đọc file, xóa khoảng trắng thừa và loại bỏ dòng trống"""
        if not file_path.exists(): return set()
        with open(file_path, 'r', encoding='utf-8') as f:
            return {line.strip() for line in f if line.strip()}

    def _get_dynamic_dates(self):
        """Tạo kho dữ liệu ngày tháng năm đa định dạng (World Format) trong RAM"""
        now = datetime.now()
        day, month = now.strftime("%d"), now.strftime("%m")
        year_f, year_s = now.strftime("%Y"), now.strftime("%y") 
        
        dates = set()
        # 1. Dải năm từ 1950 đến nay (Full: 1990, Short: 90)
        for y in range(1950, int(year_f) + 1):
            dates.add(str(y))
            dates.add(str(y)[2:])

        # 2. Các tổ hợp ngày tháng phổ biến (D-M, M-D, ISO, Short)
        formats = [
            f"{day}{month}", f"{month}{day}",
            f"{day}{month}{year_f}", f"{month}{day}{year_f}",
            f"{year_f}{month}{day}", f"{day}{month}{year_s}",
            f"{month}{day}{year_s}", f"{year_s}{month}{day}"
        ]
        dates.update(formats)

        # 3. Định dạng có dấu phân cách (., -, _, /) - Tăng độ phức tạp cho password
        for s in ['.', '-', '_', '/']:
            dates.add(f"{day}{s}{month}{s}{year_f}")
            dates.add(f"{day}{s}{month}{s}{year_s}")
            
        return dates

    def _get_leet_and_case_variations(self, word):
        """Tạo biến thể chữ hoa/thường và ký tự đặc biệt (Leet Speak)"""
        char_map = {
            'a': ['a', 'A', '@', '4'], 'b': ['b', 'B', '8'],
            'e': ['e', 'E', '3'], 'i': ['i', 'I', '1', '!'],
            'o': ['o', 'O', '0'], 's': ['s', 'S', '$', '5'],
            't': ['t', 'T', '7'], 'g': ['g', 'G', '9']
        }
        options = []
        for char in word.lower():
            v = set(char_map.get(char, [char]))
            v.update([char.upper(), char.lower()])
            options.append(list(v))
        return ["".join(item) for item in itertools.product(*options)]

    def generate_smart_combos(self, num_results=None, combo_size=None):
        """Bắt đầu trộn đồ Custom với kho ngày tháng để tạo Wordlist"""
        # Load Blacklist để lọc ngay trong lúc tạo
        blacklist = [b.lower() for b in self._read_and_clean(self.blacklist_path)]
        whitelist = list(self._read_and_clean(self.whitelist_path))
        dynamic_dates = list(self._get_dynamic_dates())
        
        # Kho nguyên liệu tổng hợp
        all_ingredients = whitelist + dynamic_dates        
        
        if not whitelist: 
            print(f"[-] Bỏ qua Combo {combo_size}: Whitelist đang trống!")
            return

        new_words = set()
        attempts = 0
        max_attempts = num_results * 500 # Giới hạn thử lại để tránh lặp vô tận

        while len(new_words) < num_results and attempts < max_attempts:
            attempts += 1
            
            # ƯU TIÊN: Luôn bốc ít nhất 1 từ trong Whitelist của bạn
            selected_raw = [random.choice(whitelist)]
            
            if combo_size > 1:
                # 30% xác suất tạo mẫu lặp (ví dụ: adminadmin)
                if random.random() < 0.3:
                    selected_raw = selected_raw * combo_size
                else:
                    # 70% còn lại ghép ngẫu nhiên với Date hoặc từ Whitelist khác
                    selected_raw.extend(random.choices(all_ingredients, k=combo_size - 1))
            
            # Xáo trộn vị trí các thành phần (ví dụ: 1990admin thay vì admin1990)
            random.shuffle(selected_raw)
            
            transformed = []
            for w in selected_raw:
                # Nếu là số hoặc ngày tháng có dấu thì giữ nguyên cho dễ đọc
                if w.isdigit() or any(s in w for s in './-_'):
                    transformed.append(w)
                else:
                    # Nếu là chữ thì mới biến đổi Case/Leet Speak
                    vars_list = self._get_leet_and_case_variations(w)
                    transformed.append(random.choice(vars_list))
            
            final_word = "".join(transformed)
            word_lower = final_word.lower()

            # KIỂM TRA BLACKLIST: Nếu chứa từ cấm thì loại ngay
            is_bad = any(bad in word_lower for bad in blacklist if bad)
            
            if not is_bad and self.min_len <= len(final_word) <= self.max_len:
                new_words.add(final_word)

        # Ghi thêm (Append) vào file wordlist.txt
        with open(self.output_path, 'a', encoding='utf-8') as f:
            for w in new_words: f.write(w + "\n")
        print(f"[+] Hoàn tất Combo {combo_size}: Đã tạo {len(new_words)} mật khẩu.")

    def sort_all_files(self):
        """Tổng vệ sinh: Xóa trùng, lọc từ cấm gắt gao bằng Regex, sắp xếp lại file"""
        print("\n[*] ĐANG THỰC HIỆN TRUY QUÉT GẮT GAO VÀ TỐI ƯU HÓA...")
        
        # Đọc blacklist, loại bỏ các mục rỗng hoặc quá ngắn (<2 ký tự) để tránh lỗi lọc sạch file
        blacklist_raw = self._read_and_clean(self.blacklist_path)
        blacklist = [re.escape(b.lower()) for b in blacklist_raw if len(b) > 1]
        
        if not blacklist:
            print("[!] Blacklist trống. Chỉ tiến hành lọc trùng và sắp xếp.")
            pattern = None
        else:
            # Tạo Pattern Regex để tìm tất cả từ cấm cùng lúc
            pattern = re.compile("|".join(blacklist), re.IGNORECASE)

        if self.output_path.exists():
            with open(self.output_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            total_before = len(lines)
            # LỌC: Chỉ giữ lại những từ KHÔNG khớp với Pattern Blacklist
            if pattern:
                clean_data = [l.strip() for l in lines if not pattern.search(l.strip())]
            else:
                clean_data = [l.strip() for l in lines]
            
            # Xóa trùng bằng set() và sắp xếp theo bảng chữ cái
            final_data = sorted(set(clean_data))
            
            with open(self.output_path, 'w', encoding='utf-8') as f:
                for item in final_data:
                    if item: f.write(item + "\n")
            
            print(f"  [>] Kết quả Wordlist: {total_before} -> {len(final_data)} từ.")
            print(f"  [v] Đã tiêu diệt: {total_before - len(final_data)} rác/từ cấm.")

# --- LUỒNG THỰC THI CHÍNH ---
if __name__ == "__main__":
    # Khởi tạo Manager
    manager = WordlistManager(min_len=MIN_LEN, max_len=MAX_LEN)
    
    # Hiển thị thông báo bắt đầu
    print("="*40)
    print(f"🔥 BẮT ĐẦU GENERATE WORDLIST: {datetime.now().strftime('%H:%M:%S')}")
    print("="*40)

    # Chạy vòng lặp tạo combo từ 1 đến 6
    for s in range(MIN_COMBO, MAX_COMBO):
        manager.generate_smart_combos(num_results=RESULT_GENERATE, combo_size=s)

    # Tổng vệ sinh cuối cùng
    manager.sort_all_files()
    
    print("="*40)
    print(f"[SUCCESS] Wordlist đã sẵn sàng tại: {manager.output_path}")
    print("="*40)