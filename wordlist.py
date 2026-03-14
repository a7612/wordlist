import random
import itertools
from pathlib import Path
from datetime import datetime

MIN_LEN = 8
MAX_LEN = 64
RESULT_GENERATE = 888
MIN_COMBO = 1
MAX_COMBO = 7

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
        if not file_path.exists(): return set()
        with open(file_path, 'r', encoding='utf-8') as f:
            return {line.strip() for line in f if line.strip()}

    def _get_dynamic_dates(self):
        """Tạo danh sách ngày tháng năm đa định dạng trong RAM (Virtual Injection)"""
        now = datetime.now()
        day, month = now.strftime("%d"), now.strftime("%m")
        year_f, year_s = now.strftime("%Y"), now.strftime("%y") # 2026 và 26
        
        dates = set()
        # 1. Thêm dải năm từ 1950 - nay & 2 số cuối của năm
        for y in range(1950, int(year_f) + 1):
            dates.add(str(y))
            dates.add(str(y)[2:])

        # 2. Các tổ hợp ngày tháng thế giới (D-M, M-D, Full, Short, ISO)
        formats = [
            f"{day}{month}", f"{month}{day}",
            f"{day}{month}{year_f}", f"{month}{day}{year_f}",
            f"{year_f}{month}{day}", f"{day}{month}{year_s}",
            f"{month}{day}{year_s}", f"{year_s}{month}{day}"
        ]
        dates.update(formats)

        # 3. Định dạng có dấu phân cách phổ biến (., -, _, /)
        for s in ['.', '-', '_', '/']:
            dates.add(f"{day}{s}{month}{s}{year_f}")
            dates.add(f"{day}{s}{month}{s}{year_s}")
            
        return dates

    def _get_leet_and_case_variations(self, word):
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
        whitelist = list(self._read_and_clean(self.whitelist_path))
        dynamic_dates = list(self._get_dynamic_dates())
        
        # Gộp chung để bốc ngẫu nhiên cho các vị trí còn lại
        all_ingredients = whitelist + dynamic_dates
        blacklist = list(self._read_and_clean(self.blacklist_path)) 
        
        if not whitelist: 
            print("[-] Whitelist trống, không có đồ custom để trộn!")
            return

        new_words = set()
        attempts = 0
        max_attempts = num_results * 150

        while len(new_words) < num_results and attempts < max_attempts:
            # --- LOGIC ƯU TIÊN MỚI ---
            # 1. Bắt buộc vị trí đầu tiên phải là một từ trong Whitelist của bạn
            selected_raw = [random.choice(whitelist)]
            
            # 2. Nếu combo_size > 1, các vị trí còn lại bốc ngẫu nhiên (có thể là whitelist hoặc date)
            if combo_size > 1:
                # Nếu là mẫu lặp "đồ đồ" (30%)
                if random.random() < 0.3:
                    selected_raw = selected_raw * combo_size
                else:
                    # Bốc thêm các phần tử còn lại từ kho tổng
                    selected_raw.extend(random.choices(all_ingredients, k=combo_size - 1))
            
            # Xáo trộn thứ tự để từ whitelist không luôn nằm ở đầu
            random.shuffle(selected_raw)
            
            # Biến đổi Leet/Case (giữ nguyên logic cũ)
            transformed = []
            for w in selected_raw:
                if w.isdigit() or any(s in w for s in './-_'):
                    transformed.append(w)
                else:
                    vars_list = self._get_leet_and_case_variations(w)
                    transformed.append(random.choice(vars_list))
            
            final_word = "".join(transformed)
            
            # Lọc Blacklist
            word_lower = final_word.lower()
            if not any(bad.lower() in word_lower for bad in blacklist) and \
               self.min_len <= len(final_word) <= self.max_len:
                new_words.add(final_word)
            attempts += 1

        with open(self.output_path, 'a', encoding='utf-8') as f:
            for w in new_words: f.write(w + "\n")
        print(f"[+] Size {combo_size}: Đã đảm bảo xuất hiện whitelist trong combo.")

    def sort_all_files(self):
        print("[*] Đang tổng vệ sinh (Lọc trùng & Sắp xếp)...")
        blacklist = list(self._read_and_clean(self.blacklist_path))
        for p in [self.whitelist_path, self.blacklist_path, self.output_path]:
            if p.exists():
                data = self._read_and_clean(p)
                # Lọc lại lần cuối để đảm bảo output không chứa bất kỳ chuỗi cấm nào
                clean = [i for i in data if not (p != self.blacklist_path and any(b.lower() in i.lower() for b in blacklist))]
                with open(p, 'w', encoding='utf-8') as f:
                    for item in sorted(clean): f.write(item + "\n")

# --- Thực thi ---
if __name__ == "__main__":
    # Min length 4 để tránh mấy pass quá ngắn dễ bị block
    manager = WordlistManager(min_len=MIN_LEN, max_len=MAX_LEN)

    # Chạy combo từ 1 đến 6 thành phần (Mỗi loại 1000 mẫu)
    for s in range(MIN_COMBO, MAX_COMBO):
        manager.generate_smart_combos(num_results=RESULT_GENERATE, combo_size=s)

    # Cuối cùng mới sort và dọn dẹp
    manager.sort_all_files()
    print("\n[SUCCESS] Wordlist sạch và 'khét' đã sẵn sàng lâm trận!")