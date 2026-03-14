import random
import itertools
import re
import concurrent.futures
from pathlib import Path
from datetime import datetime

# --- CẤU HÌNH ---
MIN_LEN = 8
MAX_LEN = 64
RESULT_GENERATE = 1000
MIN_COMBO = 1
MAX_COMBO = 7
MAX_WORKERS = 8 # Tùy vào số nhân CPU của bạn

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
        """Tạo kho ngày tháng năm để 'buff' độ khó cho password"""
        now = datetime.now()
        day, month = now.strftime("%d"), now.strftime("%m")
        year_f, year_s = now.strftime("%Y"), now.strftime("%y") 
        dates = set()
        for y in range(1950, int(year_f) + 1):
            dates.add(str(y)); dates.add(str(y)[2:])
        formats = [f"{day}{month}", f"{month}{day}", f"{day}{month}{year_f}", f"{month}{day}{year_f}",
                   f"{year_f}{month}{day}", f"{day}{month}{year_s}", f"{month}{day}{year_s}", f"{year_s}{month}{day}"]
        dates.update(formats)
        for s in ['.', '-', '_', '/']:
            dates.add(f"{day}{s}{month}{s}{year_f}"); dates.add(f"{day}{s}{month}{s}{year_s}")
        return list(dates)

    def _get_leet_variations(self, word):
        """Biến đổi chữ thành ký tự đặc biệt kiểu Hacker"""
        char_map = {'a':['a','A','@','4'],'b':['b','B','8'],'e':['e','E','3'],
                    'i':['i','I','1','!'],'o':['o','O','0'],'s':['s','S','$','5'],
                    't':['t','T','7'],'g':['g','G','9']}
        options = []
        for char in word.lower():
            v = set(char_map.get(char, [char]))
            v.update([char.upper(), char.lower()])
            options.append(list(v))
        return ["".join(item) for item in itertools.product(*options)]

    def generate_worker(self, combo_size, num_results, whitelist, all_ingredients, blacklist):
        """Mỗi luồng sẽ tự 'nấu' một loại combo riêng"""
        local_results = set()
        attempts = 0
        while len(local_results) < num_results and attempts < num_results * 100:
            attempts += 1
            selected = [random.choice(whitelist)]
            if combo_size > 1:
                if random.random() < 0.3: selected = selected * combo_size
                else: selected.extend(random.choices(all_ingredients, k=combo_size - 1))
            
            random.shuffle(selected)
            transformed = []
            for w in selected:
                if w.isdigit() or any(s in w for s in './-_'): transformed.append(w)
                else: transformed.append(random.choice(self._get_leet_variations(w)))
            
            final_word = "".join(transformed)
            # Lọc sơ bộ ngay khi tạo
            if not any(bad in final_word.lower() for bad in blacklist if bad) and \
               self.min_len <= len(final_word) <= self.max_len:
                local_results.add(final_word)
        return local_results

    def run_parallel(self):
        whitelist = list(self._read_and_clean(self.whitelist_path))
        blacklist = [b.lower() for b in self._read_and_clean(self.blacklist_path)]
        all_ingredients = whitelist + self._get_dynamic_dates()
        
        if not whitelist: 
            print("[-] Whitelist trống, không có gì để làm.")
            return

        print("="*40)
        print(f"🚀 MULTI-THREAD START: {MAX_WORKERS} luồng đang chạy...")
        print("="*40)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = [executor.submit(self.generate_worker, s, RESULT_GENERATE, whitelist, all_ingredients, blacklist) 
                       for s in range(MIN_COMBO, MAX_COMBO)]
            
            all_generated = set()
            for future in concurrent.futures.as_completed(futures):
                res = future.result()
                all_generated.update(res)

        # Append vào file
        with open(self.output_path, 'a', encoding='utf-8') as f:
            for w in all_generated: f.write(w + "\n")

    def final_clean(self):
        """Bước quan trọng nhất: Tổng vệ sinh bằng Regex để diệt tận gốc vov0, sex, fuck..."""
        print("[*] Đang thực hiện chế độ TRUY QUÉT GẮT GAO...")
        blacklist_raw = self._read_and_clean(self.blacklist_path)
        # re.escape giúp tránh lỗi nếu blacklist có ký tự lạ
        blacklist = [re.escape(b.lower()) for b in blacklist_raw if len(b) > 1]
        
        if not blacklist: return

        pattern = re.compile("|".join(blacklist), re.IGNORECASE)
        if self.output_path.exists():
            with open(self.output_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            total_before = len(lines)
            # Dùng Regex để quét sạch toàn bộ list mật khẩu
            clean_data = sorted(set(l.strip() for l in lines if not pattern.search(l.strip())))
            
            with open(self.output_path, 'w', encoding='utf-8') as f:
                for item in clean_data: f.write(item + "\n")
            
            print(f"  [v] Đã tiêu diệt: {total_before - len(clean_data)} từ vi phạm.")
            print(f"  [v] Wordlist hiện tại: {len(clean_data)} từ sạch.")

if __name__ == "__main__":
    manager = WordlistManager(min_len=MIN_LEN, max_len=MAX_LEN)
    manager.run_parallel()
    manager.final_clean()
    print("="*40)
    print(f"✨ [SUCCESS] XONG! File sẵn sàng tại: {manager.output_path}")
    print("="*40)