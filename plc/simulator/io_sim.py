"""
I/O Simulation layer.

Generates realistic sensor behavior for the virtual conveyor:
  - Boxes arrive at random intervals when the motor is running
  - Each box gets random attributes: size (small/large), metal presence, color
  - Box travels through a 5-step pipeline (detect → sense → gate zone → exit)
  - Motor feedback follows the run command with a 300 ms delay (contactor pickup)
  - Random jam faults at configurable probability
  - Simulates gate confirmation feedback
"""

import random
import time
from tag_db import TagDB


class BoxEvent:
    """Represents a single box in transit through the sensor zones."""

    SIZES = ["small", "large", "none"]
    COLORS = ["red", "blue", "green"]

    def __init__(self):
        self.size = random.choices(["small", "large", "none"], weights=[45, 35, 20])[0]
        self.is_metal = random.random() < 0.15
        self.color = random.choice(self.COLORS)
        # Which scan step are we on (0–9)
        self.step = 0
        self.total_steps = random.randint(6, 10)  # box transit duration in scans


class IOSimulator:
    """
    Updates discrete input tags once per scan to simulate physical sensors.
    Must be called before ladder_routines.execute().
    """

    def __init__(self, db: TagDB):
        self.db = db

        # Box arrival timing
        self._next_box_scan = 0    # scan number when next box should arrive
        self._scan_num = 0
        self._box_interval = (8, 20)   # scans between boxes (0.8–2.0 s)

        # Active box in transit
        self._current_box: BoxEvent | None = None

        # Motor feedback delay (contactor pickup simulation)
        self._motor_cmd_time: float | None = None
        self._fb_delay = 0.3   # seconds
        self._prev_motor_cmd = False

        # Jam simulation
        self._jam_prob_per_scan = 0.001   # ~0.1% per scan → rare random jam

    def tick(self, motor_running: bool, machine_state_val: int) -> None:
        """Called once per scan cycle. Updates all DI simulation tags."""
        self._scan_num += 1

        self._simulate_motor_feedback(motor_running)

        if not motor_running:
            self._clear_sensors()
            return

        self._simulate_jam()
        self._simulate_box_flow()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _simulate_motor_feedback(self, motor_cmd: bool) -> None:
        now = time.time()
        if motor_cmd and not self._prev_motor_cmd:
            # Rising edge: start contactor pickup timer
            self._motor_cmd_time = now
        if not motor_cmd:
            self._motor_cmd_time = None
            self.db.set("IN_MOTOR_FEEDBACK", False)
        else:
            if self._motor_cmd_time and (now - self._motor_cmd_time) >= self._fb_delay:
                self.db.set("IN_MOTOR_FEEDBACK", True)
        self._prev_motor_cmd = motor_cmd

    def _simulate_jam(self) -> None:
        if random.random() < self._jam_prob_per_scan:
            self.db.set("IN_JAM_SENSOR", True)
        else:
            # Jam clears only on fault reset (handled by ladder_routines)
            # Here we just ensure it's not permanently stuck without a box
            if self._current_box is None:
                self.db.set("IN_JAM_SENSOR", False)

    def _simulate_box_flow(self) -> None:
        """Advance boxes through sensor zones."""
        if self._current_box is None:
            if self._scan_num >= self._next_box_scan:
                self._current_box = BoxEvent()
                self._schedule_next_box()
        else:
            box = self._current_box
            box.step += 1

            step = box.step
            total = box.total_steps

            # Zone 1 (steps 1-2): Entry detection
            self.db.set("IN_BOX_DETECT", step <= 2)

            # Zone 2 (steps 2-4): Sensor reading
            self.db.set("IN_SIZE_SMALL", step in range(2, 5) and box.size == "small")
            self.db.set("IN_SIZE_LARGE", step in range(2, 5) and box.size == "large")
            self.db.set("IN_METAL_DETECT", step in range(2, 5) and box.is_metal)
            self.db.set("IN_COLOR_RED", step in range(2, 5) and box.color == "red")
            self.db.set("IN_COLOR_BLUE", step in range(2, 5) and box.color == "blue")

            # Zone 3 (steps 4-6): Gate confirmation
            self.db.set("IN_GATE_A_CONFIRM", step in range(4, 7) and box.size == "small" and not box.is_metal)
            self.db.set("IN_GATE_B_CONFIRM", step in range(4, 7) and box.is_metal)

            # Box exits conveyor
            if step >= total:
                self._current_box = None
                self._clear_sensors()

    def _schedule_next_box(self) -> None:
        interval = random.randint(*self._box_interval)
        self._next_box_scan = self._scan_num + interval

    def _clear_sensors(self) -> None:
        for tag in [
            "IN_BOX_DETECT", "IN_SIZE_SMALL", "IN_SIZE_LARGE",
            "IN_METAL_DETECT", "IN_COLOR_RED", "IN_COLOR_BLUE",
            "IN_GATE_A_CONFIRM", "IN_GATE_B_CONFIRM", "IN_JAM_SENSOR",
        ]:
            self.db.set(tag, False)
