import pyautogui
import time
import numpy as np
from PIL import ImageGrab
import os
import threading
from concurrent.futures import ThreadPoolExecutor

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
        
        # 카네이션 색상 범위 설정
        self.pink_min = 120  # 핑크/붉은색의 최소 R값
        self.pink_max = 255  # 핑크/붉은색의 최대 R값
        self.red_g_max = 80  # 핑크/붉은색의 최대 G값 (진한 붉은색)
        self.pink_g_max = 150  # 핑크색의 최대 G값 (연한 핑크색)
        self.red_b_max = 80  # 핑크/붉은색의 최대 B값
        
        # 갈색 꽃 RGB 범위 (이미지 참고)
        # 이미지에 있는 갈색 계열의 픽셀 값들
        self.brown_ranges = [
            # 어두운 갈색 (꽃 중앙)
            {"r_min": 100, "r_max": 140, "g_min": 60, "g_max": 90, "b_min": 40, "b_max": 70},
            # 중간 갈색 (꽃 전체)
            {"r_min": 120, "r_max": 170, "g_min": 75, "g_max": 120, "b_min": 45, "b_max": 90},
            # 밝은 갈색 (꽃 가장자리)
            {"r_min": 150, "r_max": 190, "g_min": 100, "g_max": 140, "b_min": 60, "b_max": 100}
        ]
        
        # 클릭 설정
        self.click_duration = 0.001  # 0.05초 동안 마우스 버튼을 누르고 있음
        
        # pyautogui 설정 최적화
        pyautogui.PAUSE = 0.001  # 클릭 사이의 대기 시간 최소화
        pyautogui.FAILSAFE = False  # 안전 장치 비활성화 (주의: 필요시에만 사용)
        
        # 클릭 카운터와 락
        self.click_count = 0
        self.click_lock = threading.Lock()
        
        # 디버그 모드
        self.debug = True
        
        # 고정 좌표값 출력
        self.print_fixed_points()
    
    def print_fixed_points(self):
        """고정 좌표값을 출력합니다."""
        print("고정 좌표값을 사용합니다.")
        for point in self.fixed_points:
            print(f"셀 {point['index']}: 좌표 {point['center']}")
    
    def is_brown_from_image(self, r, g, b):
        """이미지에서 확인한 갈색 꽃 색상인지 판단합니다."""
        # 이미지에서 추출한 갈색 범위를 확인
        for brown_range in self.brown_ranges:
            if (brown_range["r_min"] <= r <= brown_range["r_max"] and
                brown_range["g_min"] <= g <= brown_range["g_max"] and
                brown_range["b_min"] <= b <= brown_range["b_max"]):
                return True
                
        return False
    
    def is_brown(self, r, g, b):
        """갈색인지 판단합니다. 이미지에서 추출한 갈색과 일반적인 갈색 특성을 모두 확인합니다."""
        # 이미지에서 추출한 갈색 확인 (우선 적용)
        if self.is_brown_from_image(r, g, b):
            return True
        
        # 추가적인 갈색 판단 (더 넓은 범위의 갈색 감지)
        if r == 0 or g == 0:
            return False
            
        r_g_ratio = r / g
        g_r_ratio = g / r
        
        # 여러 갈색 계열 감지
        brown_1 = (
            (r >= 60 and g >= 60) and  # 충분히 밝음
            (0.65 <= r_g_ratio <= 1.5 or 0.65 <= g_r_ratio <= 1.5) and  # R과 G의 비율이 비슷함
            b < min(r, g) * 0.85  # B는 R과 G보다 낮음
        )
        
        # 특수한 갈색 계열 (r이 g보다 약간 높고, b가 낮은 계열)
        brown_2 = (
            r > 120 and 60 <= g <= 140 and b < 100 and
            r > g > b and 
            (r - g) < 50  # r과 g의 차이가 크지 않음
        )
        
        return brown_1 or brown_2
    
    def is_pink_or_red(self, r, g, b):
        """핑크색 또는 붉은색인지 판단합니다."""
        # 조건 강화 - 확실한 핑크색/붉은색만 감지
        
        # R 값이 충분히 높아야 함
        if r < self.pink_min:
            return False
            
        # R 값이 G와 B보다 크게 높아야 함 (대비)
        r_g_contrast = r - g
        r_b_contrast = r - b
        
        # G와 B 중에 하나라도 R과의 대비가 부족하면 해당 안됨
        # 갈색과 확실히 구분하기 위해 대비를 더 높임
        if r_g_contrast < 40 or r_b_contrast < 40:
            return False
        
        # G와 B 값이 너무 높으면 핑크/붉은색이 아님 (연한 색상 제외)
        if g > self.pink_g_max or b > self.red_b_max:
            return False
            
        # 붉은색/진한 핑크색: G와 B가 모두 낮음
        if g <= self.red_g_max and b <= self.red_b_max:
            return True
            
        # 중간~연한 핑크색: G가 중간 값, B는 낮음
        if g <= self.pink_g_max and b <= self.red_b_max:
            # G와 B의 차이가 크면 핑크색
            if g - b > 15:
                return True
        
        return False
    
    def is_carnation_color(self, pixel):
        """카네이션 색상(핑크색, 붉은색)인지 확인합니다."""
        # 픽셀이 3개(RGB) 또는 4개(RGBA) 값을 가질 수 있음
        if len(pixel) == 4:  # RGBA 형식
            r, g, b, a = pixel
        elif len(pixel) == 3:  # RGB 형식
            r, g, b = pixel
        else:
            return False  # 알 수 없는 형식
        
        # 먼저 갈색 확인 (갈색이면 무조건 제외) - 이미지 기반 갈색 감지 포함
        if self.is_brown(r, g, b):
            return False
        
        # 초록색 줄기 제외 (G > R, B)
        if g > r and g > b:
            return False
            
        # 배경 핑크색 배제 (배경은 R, G, B가 모두 높은 연한 핑크색)
        if r > 200 and g > 180 and b > 180:
            return False
            
        # 핑크색 또는 붉은색인지 확인
        return self.is_pink_or_red(r, g, b)
    
    def long_click(self, x, y, duration=None):
        """마우스를 지정된 시간 동안 누르고 있는 클릭 함수"""
        if duration is None:
            duration = self.click_duration
            
        try:
            # 마우스 다운
            pyautogui.mouseDown(x, y)
            # 지정된 시간 동안 대기
            time.sleep(duration)
            # 마우스 업
            pyautogui.mouseUp()
            return True
        except Exception as e:
            print(f"클릭 오류: {e}")
            return False
    
    def check_and_click_point(self, point, screenshot):
        """하나의 포인트를 확인하고 필요시 클릭합니다."""
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
            
            if len(pixel) >= 3:
                r, g, b = pixel[:3]
                
                # 디버그 모드: 갈색으로 감지되는 픽셀 출력
                if self.debug and self.is_brown(r, g, b):
                    print(f"갈색 감지 (클릭 안함) - 셀 {point['index']} 픽셀: RGB({r},{g},{b})")
                
            # 카네이션 색상인지 확인 (핑크색/붉은색만)
            if self.is_carnation_color(pixel):
                # 더 길게 클릭 실행
                self.long_click(center[0], center[1])
                with self.click_lock:
                    self.click_count += 1
                print(f"핑크/붉은색 카네이션 발견! 셀 {point['index']} RGB: {pixel[:3]}")
                return True
                
        except Exception as e:
            print(f"픽셀 처리 오류: {e} (셀 {point['index']}, 좌표: {rel_x}, {rel_y})")
        
        return False
    
    def check_fixed_points_for_carnations(self):
        """고정된 좌표 포인트만 확인하여 카네이션을 탐지합니다."""
        # 전체 화면을 한 번만 캡처해서 처리
        try:
            screenshot = ImageGrab.grab(bbox=self.game_area)
        except Exception as e:
            print(f"스크린샷 캡처 오류: {e}")
            return False
        
        clicked = False
        
        # 동시에 모든 포인트 검사 (멀티스레딩)
        with ThreadPoolExecutor(max_workers=5) as executor:
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
        print("핑크색과 붉은색 카네이션만 정확히 감지하도록 설정 (갈색 꽃 이미지 기반 필터링)")
        print("게임 시작!")
        
        # 디버그 모드: 최초 10초는 갈색 감지 정보 표시, 이후 비활성화
        debug_end_time = time.time() + 10
        
        start_time = time.time()
        self.click_count = 0
        
        try:
            while time.time() - start_time < duration:
                remaining = duration - int(time.time() - start_time)
                
                # 10초 후에는 디버그 비활성화
                if time.time() > debug_end_time:
                    self.debug = False
                
                if remaining % 5 == 0 and remaining > 0 and time.time() % 1 < 0.01:
                    print(f"남은 시간: {remaining}초, 클릭: {self.click_count}회")
                
                # 카네이션 찾고 클릭
                self.check_fixed_points_for_carnations()
                
                # 최소 대기 시간 (더 짧게 설정)
                time.sleep(0.001)  # 1ms 대기 (매우 빠른 반복)
                
        except KeyboardInterrupt:
            print("프로그램이 사용자에 의해 중단되었습니다.")
            
        game_time = time.time() - start_time
        print(f"게임 종료! 총 실행 시간: {game_time:.2f}초, 총 클릭: {self.click_count}회")


def main():
    print("카네이션 게임 자동화 프로그램을 시작합니다!")
    print("고정된 15개 좌표값을 사용합니다.")
    print("성능 최적화 모드: 멀티스레딩 사용")
    print("색상 필터링: 핑크색/붉은색만 감지, 이미지 기반 갈색 꽃 제외")
    
    # 자동 클릭 객체 생성 및 게임 시작
    auto_clicker = CarnationGameAutoClicker()
    auto_clicker.play_game(duration=25)


if __name__ == "__main__":
    main() 