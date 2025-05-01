import pyautogui
import time
from PIL import ImageGrab
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from collections import deque

class CarnationGameAutoClicker:
    def __init__(self, scan_interval=0.00001):  
        self.game_area = (25, 434, 379, 995)  # (x1, y1, x2, y2)
        
        # 고정 좌표값 설정
        self.fixed_points = [
            {"index": 1, "center": (82, 496)},
            {"index": 2, "center": (203, 500)},
            {"index": 3, "center": (325, 487)},
            {"index": 4, "center": (82, 599)},
            {"index": 5, "center": (203, 599)},
            {"index": 6, "center": (325, 599)},
            {"index": 7, "center": (82, 710)},
            {"index": 8, "center": (203, 710)},
            {"index": 9, "center": (325, 710)},
            {"index": 10, "center": (82, 812)},
            {"index": 11, "center": (203, 812)},
            {"index": 12, "center": (325, 812)},
            {"index": 13, "center": (82, 920)},
            {"index": 14, "center": (203, 920)},
            {"index": 15, "center": (325, 920)}
        ]
        
        # 카네이션 색상 범위 설정
        self.pink_min = 140
        self.red_contrast = 55
        self.red_g_max = 120
        self.red_b_max = 100
        
        # 갈색 범위 설정
        self.brown_r_range = (80, 190)
        self.brown_g_range = (50, 150)
        self.brown_b_range = (30, 110)
        
        # 캐시 설정
        self.brown_cache = {}
        self.cache_size = 1000
        self.cache_queue = deque()
        
        # 클릭 설정
        self.click_duration = 0.0001  
        self.click_count = 0
        self.click_lock = threading.Lock()
        
        # 멀티스레딩 설정
        self.max_workers = 15  
        
        # PyAutoGUI 설정
        pyautogui.PAUSE = 0  
        pyautogui.FAILSAFE = False
        
        # 클릭 쿨다운 설정
        self.cooldown_time = 0.15  
        self.cell_cooldowns = {}  
        self.cooldown_lock = threading.Lock()
        
        # 성능 최적화 설정
        self.scan_interval = scan_interval  
        print(f"스캔 간격: {self.scan_interval:.8f}초")
    
    def is_brown_fast(self, r, g, b):
        rgb_key = (r, g, b)
        if rgb_key in self.brown_cache:
            return self.brown_cache[rgb_key]
            
        if (self.brown_r_range[0] <= r <= self.brown_r_range[1] and
            self.brown_g_range[0] <= g <= self.brown_g_range[1] and
            self.brown_b_range[0] <= b <= self.brown_b_range[1]):
            
            r_g_diff = abs(r - g)
            if (r_g_diff < 60 and
                b < min(r, g) * 0.9 and
                (r <= g * 1.5 and g <= r * 1.5)):
                self._add_to_cache(rgb_key, True)
                return True
        
        if (r > 120 and
            60 <= g <= 140 and
            b < 100 and
            r - g < 70 and
            g > b * 1.2):
            self._add_to_cache(rgb_key, True)
            return True
        
        self._add_to_cache(rgb_key, False)
        return False
    
    def _add_to_cache(self, key, value):
        if len(self.cache_queue) >= self.cache_size:
            old_key = self.cache_queue.popleft()
            if old_key in self.brown_cache:
                del self.brown_cache[old_key]
        
        self.brown_cache[key] = value
        self.cache_queue.append(key)
    
    def is_pink_or_red_fast(self, r, g, b):
        if r < self.pink_min:
            return False
            
        if r - g < self.red_contrast or r - b < self.red_contrast:
            return False
            
        if g > self.red_g_max or b > self.red_b_max:
            return False
            
        if r < g * 1.5:
            return False
            
        r_g_ratio = r / max(g, 1)
        r_b_ratio = r / max(b, 1)
        
        if r_g_ratio < 1.4 or r_b_ratio < 1.4:
            return False
            
        return True
    
    def is_carnation_color_fast(self, pixel):
        try:
            if len(pixel) == 4:
                r, g, b, a = pixel
            elif len(pixel) == 3:
                r, g, b = pixel
            else:
                return False
            
            if self.is_brown_fast(r, g, b):
                return False
                
            if g > r:
                return False
                
            if r > 200 and g > 180 and b > 180:
                return False
                
            return self.is_pink_or_red_fast(r, g, b)
            
        except:
            return False
    
    def is_cell_in_cooldown(self, index):
        """셀이 쿨다운 상태인지 확인합니다."""
        if index in self.cell_cooldowns:
            if time.time() < self.cell_cooldowns[index]:
                return True
            # 쿨다운이 끝났으면 제거
            else:
                with self.cooldown_lock:
                    if index in self.cell_cooldowns:
                        del self.cell_cooldowns[index]
        return False
    
    def set_cell_cooldown(self, index):
        """셀에 쿨다운을 설정합니다."""
        with self.cooldown_lock:
            self.cell_cooldowns[index] = time.time() + self.cooldown_time
    
    def click_point(self, x, y, point_index):
        try:
            # 더 빠른 클릭 위해 duration 최소화
            pyautogui.click(x=x, y=y, duration=self.click_duration)
            
            # 클릭 통계 업데이트
            self.click_count += 1
            
            # 쿨다운 설정
            self.set_cell_cooldown(point_index)
            print(f"{point_index}번째 셀에서 카네이션 발견! [O]")
            return True
        except Exception as e:
            print(f"{point_index}번째 셀에서 카네이션 발견! [X] - 클릭 실패: {str(e)}")
            return False
    
    def check_and_click_point(self, point, screenshot):
        center = point['center']
        index = point['index']
        
        if self.is_cell_in_cooldown(index):
            return False
            
        rel_x = center[0] - self.game_area[0]
        rel_y = center[1] - self.game_area[1]
        
        if rel_x < 0 or rel_y < 0 or rel_x >= screenshot.width or rel_y >= screenshot.height:
            return False
        
        try:
            pixel = screenshot.getpixel((rel_x, rel_y))
            
            if self.is_carnation_color_fast(pixel):
                return self.click_point(center[0], center[1], index)
                
        except Exception:
            pass
        
        return False
    
    def check_fixed_points_for_carnations(self):
        try:
            # 화면 캡처
            screenshot = ImageGrab.grab(bbox=self.game_area)
            
            # 병렬 처리로 모든 포인트 검사
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = [
                    executor.submit(self.check_and_click_point, point, screenshot)
                    for point in self.fixed_points
                ]
                
                # 즉시 결과 수집
                for future in futures:
                    if future.result():
                        return True
            
            return False
        except:
            return False
    
    def play_game(self, duration=25):
        start_time = time.time()
        self.click_count = 0
        
        try:
            while time.time() - start_time < duration:
                self.check_fixed_points_for_carnations()
                # 최소 지연으로 CPU 사용률 조절
                time.sleep(self.scan_interval)
                
        except KeyboardInterrupt:
            pass
        
        # 소요 시간 계산 및 출력
        elapsed_time = time.time() - start_time
        print(f"종료 됐습니다. 소요시간: {elapsed_time:.2f}초, 총 클릭: {self.click_count}회")


def main():
    auto_clicker = CarnationGameAutoClicker(scan_interval=0.00001)
    auto_clicker.play_game(duration=25)


if __name__ == "__main__":
    main() 