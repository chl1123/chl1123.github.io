import math

from syspy import Loc, Navigation, Trace
from syspy.lib.action_task import ActionBase, ActionStatus


def _normalize_motion_status(status):
    if status == ActionStatus.INIT:
        return ActionStatus.RUNNING
    return status


class GoArcWorld(ActionBase):
    """Run one odometry arc tangent to the current travel direction."""

    _STRAIGHT_EPS = 1e-4
    _SAMPLE_DIST = 0.01

    def __init__(self, target_world, is_backwards=False, max_speed=0.2,
                 path_dist_accuracy=0.05, path_angle_accuracy=180.0):
        super().__init__(self.__class__.__name__)
        self.target_world = list(target_world[:3])
        self.is_backwards = bool(is_backwards)
        self.max_speed = float(max_speed)
        self.path_dist_accuracy = float(path_dist_accuracy)
        self.path_angle_accuracy = math.radians(float(path_angle_accuracy))
        self.motion_started = False
        self.path_started = False
        self.params = None
        self.xs = []
        self.ys = []

    def reset(self):
        super().reset()
        Navigation.resetPath()
        Navigation.resetOdoMove()
        self.motion_started = False
        self.path_started = False
        pose = Loc.getPose() or {}
        try:
            x0, y0 = float(pose["x"]), float(pose["y"])
            yaw = math.radians(float(pose["yaw"]))
            xt, yt = float(self.target_world[0]), float(self.target_world[1])
        except (KeyError, TypeError, ValueError) as error:
            self.fail_reason = "invalid arc pose: {}".format(error)
            self.action_status = ActionStatus.FAILED
            return

        travel_yaw = yaw + (math.pi if self.is_backwards else 0.0)
        dx, dy = xt - x0, yt - y0
        local_x = math.cos(travel_yaw) * dx + math.sin(travel_yaw) * dy
        local_y = -math.sin(travel_yaw) * dx + math.cos(travel_yaw) * dy
        if local_x <= 0.0:
            self.fail_reason = "arc target must be ahead of the travel direction"
            self.action_status = ActionStatus.FAILED
            return

        chord = math.hypot(local_x, local_y)
        if chord <= self.path_dist_accuracy:
            self.action_status = ActionStatus.FINISHED
            return
        if abs(local_y) <= self._STRAIGHT_EPS:
            angle = 0.0
            radius = None
            self.params = {
                "moveDist": chord,
                "speedX": -self.max_speed if self.is_backwards else self.max_speed,
                "actionName": self.action_name,
            }
            samples = max(2, int(math.ceil(chord / self._SAMPLE_DIST)) + 1)
            local_points = [(local_x * index / (samples - 1), 0.0)
                            for index in range(samples)]
        else:
            radius = (local_x * local_x + local_y * local_y) / (2.0 * local_y)
            angle = 2.0 * math.atan2(local_y, local_x)
            self.params = {
                "rotDegree": abs(math.degrees(angle)),
                "rotRadius": radius,
                "rotSpeed": (
                    -self.max_speed if self.is_backwards else self.max_speed
                ) / abs(radius),
                "actionName": self.action_name,
            }
            arc_length = abs(radius * angle)
            samples = max(2, int(math.ceil(arc_length / self._SAMPLE_DIST)) + 1)
            local_points = [
                (radius * math.sin(angle * index / (samples - 1)),
                 radius * (1.0 - math.cos(angle * index / (samples - 1))))
                for index in range(samples)
            ]
        cos_yaw, sin_yaw = math.cos(travel_yaw), math.sin(travel_yaw)
        self.xs = [x0 + cos_yaw * x - sin_yaw * y for x, y in local_points]
        self.ys = [y0 + sin_yaw * x + cos_yaw * y for x, y in local_points]
        self.xs[-1], self.ys[-1] = xt, yt
        self.motion_started = True
        # MF consumes a world path for this motion.  The arc samples above are
        # retained as the path so the planner can follow the complete curve;
        # the odometry arc parameters are kept in the trace for diagnostics.
        Navigation.setPathReachAngle(self.path_angle_accuracy)
        Navigation.setPathReachDist(self.path_dist_accuracy)
        Navigation.setPathBackMode(self.is_backwards)
        Navigation.setPathMaxSpeed(self.max_speed)
        Navigation.setPathOnWorld(self.xs, self.ys, yaw)
        Navigation.goPathParam({})
        self.path_started = True
        Trace.log({
            "event": "arcPathStarted",
            "target": [xt, yt],
            "backwards": self.is_backwards,
            "radius": radius,
            "angle": math.degrees(angle),
            "pointCount": len(self.xs),
            "params": dict(self.params),
        }, name="goArc")

    def run(self, _ctx=None):
        if self.action_status != ActionStatus.RUNNING:
            return self.action_status
        self.action_status = _normalize_motion_status(
            ActionStatus.FINISHED if Navigation.isPathReached()
            else ActionStatus.RUNNING
        )
        if self.action_status in (ActionStatus.FINISHED, ActionStatus.FAILED):
            Navigation.resetPath()
        return self.action_status

    def cancel(self):
        Navigation.resetOdoMove()
        Navigation.resetPath()
        self.motion_started = False
        self.path_started = False
        super().cancel()

    def suspend(self):
        if self.action_status == ActionStatus.RUNNING and self.path_started:
            Navigation.stopRobotNow()
        super().suspend()

    def resume(self):
        if self.action_status == ActionStatus.SUSPENDED and self.path_started:
            Navigation.goPathParam({})
        super().resume()
