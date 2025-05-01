import pyautogui
import time
import numpy as np
from PIL import ImageGrab
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from collections import deque

class CarnationGameAutoClicker:
    def __init__(self):
        # 게임 영역을 고정값으로 설정
        self.game_area = (25, 434, 379, 995)  # (x1, y1, x2, y2)
        
        # 고정 좌표값 설정 (셀 1부터 15까지)
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
        
        # 현재 디렉토리 설정
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 카네이션 색상 범위 설정 - 고속 판단을 위한 단순화
        self.pink_min = 140  # 핑크/붉은색의 최소 R값 (더 높게 설정)
        self.red_contrast = 55  # R과 G, B 사이의 최소 대비 (더 높게 설정)
        
        # 갈색 꽃 RGB 범위 단순화 (빠른 판단용) - 더 넓은 범위로 설정
        self.brown_r_range = (80, 190)   # 갈색 R 범위
        self.brown_g_range = (50, 150)   # 갈색 G 범위
        self.brown_b_range = (30, 110)   # 갈색 B 범위
        
        # 핑크색/붉은색 추가 조건
        self.red_g_max = 120  # 붉은색의 최대 G값
        self.red_b_max = 100  # 붉은색의 최대 B값
        
        # 브라운 캐시 - 같은 RGB값에 대한 중복 계산 방지
        self.brown_cache = {}
        self.cache_size = 1000  # 최대 캐시 크기
        self.cache_queue = deque()
        
        # 디버그 모드 (첫 10초 동안 색상 정보 출력)
        self.debug = True
        self.debug_end_time = time.time() + 10
        
        # 클릭 설정
        self.click_duration = 0.0001  # 0.001초 동안 마우스 버튼을 누르고 있음
        
        # pyautogui 설정 최적화
        pyautogui.PAUSE = 0.0001  # 클릭 사이의 대기 시간 최소화
        pyautogui.FAILSAFE = False  # 안전 장치 비활성화 (주의: 필요시에만 사용)
        
        # 클릭 카운터와 락
        self.click_count = 0
        self.click_lock = threading.Lock()
        
        # 멀티스레딩 최적화
        self.max_workers = 10  # 스레드 수 증가
        
        # 고정 좌표값 출력
        self.print_fixed_points()
    
    def print_fixed_points(self):
        """고정 좌표값을 출력합니다."""
        print("고정 좌표값을 사용합니다.")
        for point in self.fixed_points:
            print(f"셀 {point['index']}: 좌표 {point['center']}")
    
    def is_brown_fast(self, r, g, b):
        """갈색인지 빠르게 판단합니다. 캐싱 적용."""
        # 캐시 확인
        rgb_key = (r, g, b)
        if rgb_key in self.brown_cache:
            return self.brown_cache[rgb_key]
            
        # 범위 기반 빠른 판정
        # 1. 갈색의 일반적인 범위 확인
        if (self.brown_r_range[0] <= r <= self.brown_r_range[1] and
            self.brown_g_range[0] <= g <= self.brown_g_range[1] and
            self.brown_b_range[0] <= b <= self.brown_b_range[1]):
            
            # 2. 갈색의 특성 검사 - 더 강화된 조건
            # R과 G가 비슷하고 B가 낮음
            r_g_diff = abs(r - g)
            if (r_g_diff < 60 and                # R과 G의 차이가 작음
                b < min(r, g) * 0.9 and          # B가 R, G보다 확실히 낮음
                (r <= g * 1.5 and g <= r * 1.5)  # R과 G의 비율이 서로 1.5배 이내
               ):
                # 결과 캐싱
                self._add_to_cache(rgb_key, True)
                return True
        
        # 추가 갈색 판단 조건 - 밝은 갈색 (고레벨 R, 중간 레벨 G, 낮은 레벨 B)
        if (r > 120 and
            60 <= g <= 140 and
            b < 100 and
            r - g < 70 and  # R과 G의 차이가 너무 크지 않음
            g > b * 1.2):   # G가 B보다 확실히 큼
            # 결과 캐싱
            self._add_to_cache(rgb_key, True)
            return True
        
        # 결과 캐싱
        self._add_to_cache(rgb_key, False)
        return False
    
    def _add_to_cache(self, key, value):
        """캐시에 결과 추가 (크기 제한 있음)"""
        # 캐시가 너무 크면 오래된 항목 제거
        if len(self.cache_queue) >= self.cache_size:
            old_key = self.cache_queue.popleft()
            if old_key in self.brown_cache:
                del self.brown_cache[old_key]
        
        # 새 결과 추가
        self.brown_cache[key] = value
        self.cache_queue.append(key)
    
    def is_pink_or_red_fast(self, r, g, b):
        """핑크색 또는 붉은색인지 빠르게 판단합니다."""
        # 더 엄격한 붉은색/핑크색 판단
        
        # 1. R 값이 충분히 높아야 함
        if r < self.pink_min:
            return False
            
        # 2. R 값이 G, B와 충분히 큰 대비를 가져야 함
        if r - g < self.red_contrast or r - b < self.red_contrast:
            return False
            
        # 3. G와 B 값이 너무 높지 않아야 함
        if g > self.red_g_max or b > self.red_b_max:
            return False
            
        # 4. R이 G의 최소 1.5배 이상이어야 함 (붉은색 특성)
        if r < g * 1.5:
            return False
            
        # 5. R/G와 R/B 비율 확인 (진한 붉은색/핑크색의 특성)
        r_g_ratio = r / max(g, 1)  # 0으로 나누기 방지
        r_b_ratio = r / max(b, 1)  # 0으로 나누기 방지
        
        if r_g_ratio < 1.4 or r_b_ratio < 1.4:
            return False
            
        return True
    
    def is_carnation_color_fast(self, pixel):
        """카네이션 색상인지 빠르게 확인합니다. 최적화된 버전."""
        try:
            # 픽셀 값 분리
            if len(pixel) == 4:  # RGBA 형식
                r, g, b, a = pixel
            elif len(pixel) == 3:  # RGB 형식
                r, g, b = pixel
            else:
                return False
                
            # 디버그 모드일 때만 색상 정보 출력
            if self.debug and time.time() < self.debug_end_time:
                # 갈색으로 판정된 픽셀 중 r이 높은 것 출력 (갈색 오인식 디버깅용)
                if r > 140 and self.is_brown_fast(r, g, b):
                    print(f"갈색 감지: RGB({r},{g},{b}), R-G: {r-g}, R-B: {r-b}, R/G: {r/g if g else 0}")
                
                # 핑크색/붉은색으로 판정된 픽셀 출력 (붉은색 판단 디버깅용)
                if r > 140 and not self.is_brown_fast(r, g, b) and self.is_pink_or_red_fast(r, g, b):
                    print(f"핑크/붉은색 감지: RGB({r},{g},{b}), R-G: {r-g}, R-B: {r-b}, R/G: {r/g if g else 0}")
                
            # 1. 갈색은 제외 (먼저 갈색 검사로 오인식 방지)
            if self.is_brown_fast(r, g, b):
                return False
                
            # 2. 초록색 줄기 제외 (빠른 판단)
            if g > r:
                return False
                
            # 3. 배경색 제외 (빠른 판단)
            if r > 200 and g > 180 and b > 180:
                return False
                
            # 4. 핑크색/붉은색 확인 (빠른 판단)
            return self.is_pink_or_red_fast(r, g, b)
            
        except:
            return False
    
    def click_point(self, x, y):
        """마우스를 클릭합니다. 최대한 빠르게."""
        pyautogui.click(x, y, duration=self.click_duration)
        with self.click_lock:
            self.click_count += 1
        return True
    
    def check_and_click_point(self, point, screenshot):
        """하나의 포인트를 확인하고 필요시 클릭합니다. 최적화 버전."""
        # 게임 영역에 대한 상대 좌표로 변환
        center = point['center']
        rel_x = center[0] - self.game_area[0]
        rel_y = center[1] - self.game_area[1]
        
        # 화면 범위를 벗어나지 않는지 확인
        if rel_x < 0 or rel_y < 0 or rel_x >= screenshot.width or rel_y >= screenshot.height:
            return False
        
        # 픽셀 확인
        try:
            # 픽셀 색상 얻기
            pixel = screenshot.getpixel((rel_x, rel_y))
            
            # 카네이션 색상인지 확인 (핑크색/붉은색만) - 최적화 버전
            if self.is_carnation_color_fast(pixel):
                # 더 빠른 클릭
                self.click_point(center[0], center[1])
                return True
                
        except Exception:
            pass
        
        return False
    
    def check_fixed_points_for_carnations(self):
        """고정된 좌표 포인트만 확인하여 카네이션을 탐지합니다."""
        # 전체 화면을 한 번만 캡처해서 처리
        try:
            screenshot = ImageGrab.grab(bbox=self.game_area)
        except:
            return False
        
        # 동시에 모든 포인트 검사 (멀티스레딩 강화)
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            results = list(executor.map(
                lambda point: self.check_and_click_point(point, screenshot), 
                self.fixed_points
            ))
        
        # 하나라도 클릭되었으면 True 반환
        return any(results)
    
    def play_game(self, duration=25):
        """게임을 자동으로 플레이합니다."""
        print(f"{duration}초 동안 게임을 시작합니다!")
        print(f"클릭 지속 시간: {self.click_duration}초")
        print("초고속 인식 모드: 색상 판단 최적화, 갈색 오인식 방지 강화")
        print("게임 시작!")
        
        start_time = time.time()
        self.click_count = 0
        
        try:
            while time.time() - start_time < duration:
                remaining = duration - int(time.time() - start_time)
                
                # 10초 후에는 디버그 비활성화
                if time.time() > self.debug_end_time:
                    self.debug = False
                
                if remaining % 5 == 0 and remaining > 0 and time.time() % 1 < 0.01:
                    print(f"남은 시간: {remaining}초, 클릭: {self.click_count}회")
                
                # 카네이션 찾고 클릭 - 최대한 빠른 반복
                self.check_fixed_points_for_carnations()
                
                # 최소 대기 시간 감소
                time.sleep(0.0001)  # 0.1ms로 대기 시간 감소 (실질적으로 CPU 자원만 허용하는 한 연속 실행)
                
        except KeyboardInterrupt:
            print("프로그램이 사용자에 의해 중단되었습니다.")
            
        game_time = time.time() - start_time
        print(f"게임 종료! 총 실행 시간: {game_time:.2f}초, 총 클릭: {self.click_count}회")


def main():
    print("카네이션 게임 자동화 프로그램을 시작합니다!")
    print("고정된 15개 좌표값을 사용합니다.")
    print("초고속 최적화 모드: 갈색 오인식 방지 강화")
    
    # 자동 클릭 객체 생성 및 게임 시작
    auto_clicker = CarnationGameAutoClicker()
    auto_clicker.play_game(duration=25)


if __name__ == "__main__":
    main() 