import cv2
import mediapipe as mp
import time
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from shared.protocol import (
    GESTURE_SLICE, GESTURE_SHIELD, GESTURE_POWER_UP,
    GESTURE_DOUBLE_SLICE, GESTURE_NONE
)

# ─────────────────────────────────────────────
#  SliceWars Gesture Classifier
#
#  Qualcomm signal:
#  - Processes webcam input at 30fps
#  - Uses MediaPipe's 21 hand landmarks
#  - Custom geometric classifier — no ML needed
#  - Measures and reports input latency in ms
#  - Per-player calibration support
#  - Input smoothing over rolling window
#
#  Gesture → Game action mapping:
#  SLICE        (index finger)  → blade
#  SHIELD       (open palm)     → block next bomb
#  POWER_UP     (closed fist)   → activate multiplier
#  DOUBLE_SLICE (peace sign)    → wider blade
#  NONE         (no hand)       → nothing
# ─────────────────────────────────────────────

# MediaPipe landmark indices
# Full map: https://developers.google.com/mediapipe/solutions/vision/hand_landmarker
WRIST          = 0
THUMB_TIP      = 4
INDEX_TIP      = 8
INDEX_MCP      = 5    # base of index finger
MIDDLE_TIP     = 12
MIDDLE_MCP     = 9
RING_TIP       = 16
RING_MCP       = 13
PINKY_TIP      = 20
PINKY_MCP      = 17

# Finger tip and pip (middle joint) indices for extension detection
FINGER_TIPS  = [INDEX_TIP,  MIDDLE_TIP, RING_TIP,  PINKY_TIP]
FINGER_PIPS  = [6,          10,         14,         18]


class GestureClassifier:
    """
    Real-time hand gesture classifier using MediaPipe landmarks.

    Architecture (Qualcomm signal):
    Webcam frame → MediaPipe (21 landmarks) → geometric analysis
    → gesture enum → game action

    The classifier works by measuring which fingers are extended.
    A finger is "extended" when its tip is further from the wrist
    than its middle joint (PIP) — pure geometry, no ML required.
    """

    def __init__(self, camera_index: int = 0, smooth_window: int = 1):
        """
        camera_index   : which webcam to use (0 = default)
        smooth_window  : number of frames to smooth over (reduces jitter)
        """
        self.camera_index   = camera_index
        self.smooth_window  = smooth_window

        # MediaPipe setup
        self.mp_hands    = mp.solutions.hands
        self.mp_draw     = mp.solutions.drawing_utils
        self.hands       = self.mp_hands.Hands(
            static_image_mode       = False,
            max_num_hands           = 1,
            min_detection_confidence= 0.5,
            min_tracking_confidence = 0.3
        )

        # Webcam
        self.cap         = None
        self.frame_w     = 640
        self.frame_h     = 480

        # Smoothing buffer — rolling window of recent gestures
        self.gesture_buffer = []

        # Latency tracking — Qualcomm signal
        self.last_frame_time  = 0
        self.latency_ms       = 0

        # Calibration thresholds (can be adjusted per player)
        self.extension_threshold = 0.8   # ratio: tip_dist / pip_dist

        # Current state
        self.current_gesture = GESTURE_NONE
        self.finger_x        = 0.0   # normalized 0-1
        self.finger_y        = 0.0   # normalized 0-1
        self.running         = False

    # ─────────────────────────────────────────
    #  Start / stop
    # ─────────────────────────────────────────
    def start(self) -> bool:
        """Open webcam. Returns True on success."""
        self.cap = cv2.VideoCapture(self.camera_index)
        if not self.cap.isOpened():
            print(f"ERROR: Cannot open camera {self.camera_index}")
            return False

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,  self.frame_w)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_h)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        self.running = True
        print(f"Webcam started — camera {self.camera_index}")
        return True

    def stop(self):
        """Release webcam and MediaPipe resources."""
        self.running = False
        if self.cap:
            self.cap.release()
        self.hands.close()
        cv2.destroyAllWindows()

    # ─────────────────────────────────────────
    #  Main update — call once per game frame
    # ─────────────────────────────────────────
    def update(self) -> tuple:
        """
        Capture one frame, classify gesture.
        Returns (x, y, gesture, latency_ms)
        where x, y are normalized finger position (0.0 to 1.0)

        Latency is measured from frame capture to classification.
        This is the Qualcomm signal — we measure our pipeline speed.
        """
        if not self.cap or not self.running:
            return (0.0, 0.0, GESTURE_NONE, 0)

        # ── Capture frame ──────────────────────
        t_start = int(time.time() * 1000)
        ret, frame = self.cap.read()
        if not ret:
            return (0.0, 0.0, GESTURE_NONE, 0)

        # Flip horizontally — mirror effect feels natural
        frame = cv2.flip(frame, 1)

        # ── MediaPipe processing ───────────────
        rgb    = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = self.hands.process(rgb)

        gesture = GESTURE_NONE
        x, y    = 0.0, 0.0

        if result.multi_hand_landmarks:
            landmarks = result.multi_hand_landmarks[0]

            # Get index fingertip position (normalized 0-1)
            tip = landmarks.landmark[INDEX_TIP]
            x   = tip.x
            y   = tip.y

            # Classify the gesture
            gesture = self._classify(landmarks)

            # Draw landmarks on frame (for debug window)
            self.mp_draw.draw_landmarks(
                frame, landmarks, self.mp_hands.HAND_CONNECTIONS
            )

        # ── Smoothing ──────────────────────────
        gesture = self._smooth(gesture)

        # ── Latency measurement ────────────────
        self.latency_ms = int(time.time() * 1000) - t_start

        # Store current state
        self.current_gesture = gesture
        self.finger_x        = x
        self.finger_y        = y

        return (x, y, gesture, self.latency_ms)

    def get_frame(self):
        """
        Returns the current annotated frame for display.
        Call after update() if you want to show the webcam feed.
        """
        if not self.cap:
            return None
        ret, frame = self.cap.read()
        if not ret:
            return None
        return cv2.flip(frame, 1)

    # ─────────────────────────────────────────
    #  Gesture classifier — core logic
    #  Qualcomm signal: geometric analysis of
    #  21 skeletal landmarks
    # ─────────────────────────────────────────
    def _classify(self, landmarks) -> str:
        """
        Classify hand pose from MediaPipe landmarks.

        Method:
        1. Determine which fingers are extended
        2. Map extension pattern to gesture enum

        A finger is extended when its tip is farther
        from the wrist than its PIP (middle) joint.
        This is pure trigonometry — no ML needed.
        """
        lm = landmarks.landmark

        # Get wrist position as reference point
        wrist = lm[WRIST]

        extended = []
        for tip_idx, pip_idx in zip(FINGER_TIPS, FINGER_PIPS):
            tip = lm[tip_idx]
            pip = lm[pip_idx]

            # Distance from wrist to tip vs wrist to pip
            tip_dist = self._distance(wrist, tip)
            pip_dist = self._distance(wrist, pip)

            # Finger is extended if tip is significantly
            # further from wrist than pip joint
            if pip_dist > 0:
                ratio = tip_dist / pip_dist
                extended.append(ratio > self.extension_threshold)
            else:
                extended.append(False)

        # extended = [index, middle, ring, pinky]
        index, middle, ring, pinky = extended

        # Also check thumb (different geometry — compare x position)
        thumb_tip  = lm[THUMB_TIP]
        index_base = lm[INDEX_MCP]
        thumb_extended = abs(thumb_tip.x - index_base.x) > 0.05

        fingers_up = sum(extended)

        # ── Gesture rules ──────────────────────
        # SLICE: only index finger extended
        if index and not middle and not ring and not pinky:
            return GESTURE_SLICE

        # DOUBLE_SLICE: index + middle (peace sign)
        if index and middle and not ring and not pinky:
            return GESTURE_DOUBLE_SLICE

        # SHIELD: all 4 fingers extended (open palm)
        if index and middle and ring and pinky:
            return GESTURE_SHIELD

        # POWER_UP: no fingers extended (closed fist)
        if fingers_up == 0:
            return GESTURE_POWER_UP

        # Default — hand detected but no clear gesture
        return GESTURE_NONE

    def _distance(self, a, b) -> float:
        """Euclidean distance between two MediaPipe landmarks."""
        return ((a.x - b.x)**2 + (a.y - b.y)**2 + (a.z - b.z)**2) ** 0.5

    # ─────────────────────────────────────────
    #  Smoothing — reduces jitter
    # ─────────────────────────────────────────
    def _smooth(self, gesture: str) -> str:
        """
        Rolling window smoothing over last N frames.
        Returns the most common gesture in the window.
        This prevents flickering between gestures.
        """
        self.gesture_buffer.append(gesture)
        if len(self.gesture_buffer) > self.smooth_window:
            self.gesture_buffer.pop(0)

        # Return most common gesture in window
        return max(set(self.gesture_buffer),
                   key=self.gesture_buffer.count)

    # ─────────────────────────────────────────
    #  Calibration
    # ─────────────────────────────────────────
    def calibrate(self, threshold: float):
        """
        Adjust extension threshold for this player's hand.
        Default 0.8 works for most people.
        Increase if gestures trigger too easily.
        Decrease if gestures don't register.
        """
        self.extension_threshold = threshold
        print(f"Calibrated: extension threshold = {threshold}")


# ─────────────────────────────────────────────
#  Mouse fallback — identical interface
# ─────────────────────────────────────────────
class MouseInput:
    """
    Fallback input for players without webcam.
    Identical interface to GestureClassifier —
    game engine never knows which one is active.
    """
    def __init__(self):
        self.current_gesture = GESTURE_SLICE
        self.finger_x        = 0.0
        self.finger_y        = 0.0
        self.latency_ms      = 0
        self.running         = False

    def start(self) -> bool:
        self.running = True
        return True

    def stop(self):
        self.running = False

    def update(self, pygame_events=None, screen_w=800, screen_h=600):
        """
        Read mouse position and button state.
        Left button held = SLICE gesture.
        Returns same tuple as GestureClassifier.
        """
        import pygame
        mx, my   = pygame.mouse.get_pos()
        buttons  = pygame.mouse.get_pressed()

        # Normalize to 0-1
        x = mx / screen_w
        y = my / screen_h

        # Left mouse button = slicing
        gesture = GESTURE_SLICE if buttons[0] else GESTURE_NONE

        self.finger_x        = x
        self.finger_y        = y
        self.current_gesture = gesture
        return (x, y, gesture, 0)

    def calibrate(self, threshold: float):
        pass   # no-op for mouse


# ─────────────────────────────────────────────
#  Factory function — used by main.py
# ─────────────────────────────────────────────
def create_input(choice: str):
    """
    Returns the correct input object based on player's choice.
    Usage:
        inp = create_input("webcam")   # or "mouse"
        inp.start()
        x, y, gesture, latency = inp.update()
    """
    if choice == "webcam":
        return GestureClassifier()
    else:
        return MouseInput()


# ─────────────────────────────────────────────
#  Live test — run this file directly to test
#  your webcam and gesture classifier
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("SliceWars Gesture Classifier — live test")
    print("Controls:")
    print("  Index finger only  → SLICE")
    print("  Peace sign         → DOUBLE_SLICE")
    print("  Open palm          → SHIELD")
    print("  Closed fist        → POWER_UP")
    print("  Press Q to quit\n")

    classifier = GestureClassifier(smooth_window=3)
    if not classifier.start():
        sys.exit(1)

    import cv2 as cv

    while True:
        x, y, gesture, latency = classifier.update()

        # Get frame for display
        ret, frame = classifier.cap.read()
        if not ret:
            break
        frame = cv2.flip(frame, 1)

        # Draw gesture label on frame
        color = {
            GESTURE_SLICE        : (0,   255, 0),
            GESTURE_DOUBLE_SLICE : (0,   200, 255),
            GESTURE_SHIELD       : (255, 165, 0),
            GESTURE_POWER_UP     : (255, 0,   0),
            GESTURE_NONE         : (150, 150, 150),
        }.get(gesture, (255, 255, 255))

        cv2.putText(frame, f"Gesture: {gesture}",
                    (20, 40), cv2.FONT_HERSHEY_SIMPLEX,
                    1.0, color, 2)
        cv2.putText(frame, f"Latency: {latency}ms",
                    (20, 80), cv2.FONT_HERSHEY_SIMPLEX,
                    0.7, (255, 255, 255), 1)
        cv2.putText(frame, f"Finger: ({x:.2f}, {y:.2f})",
                    (20, 110), cv2.FONT_HERSHEY_SIMPLEX,
                    0.7, (255, 255, 255), 1)

        cv2.imshow("SliceWars — Gesture Test", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    classifier.stop()
    print("Test complete.")
