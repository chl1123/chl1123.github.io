import math
import logging
import json
from enum import IntEnum
import time

from syspy.script_data import ScriptData
from syspy import Navigation, Loc, Abnormal, Logger, Module, ScriptStatus, Recognize, Trace
from syspy.lib.module import pos2World
from syspy.utils.time import Timer
from standard import goPath
from syspy.core.rbk_rpc import Service

class GoLiveRec:
    def __init__(self):
        self.attempts = 0
        self.results_dict = None
        self.rec_status = None
        self.success = False
        self.max_attempts = None
        self.goal = [0, 0, 0]
        self.init = False
        self.status = ScriptStatus.NONE
        self.task_state = True
        self.doing_rec = True
        self.doing_path = True
        # Variable to store recognition results
        self.rec_result = None
        #Path to the recognition data file
        self.recfile = "default.srec"

    def run(self):
        self.status = ScriptStatus.RUNNING

        # Initialize on first run
        if not self.init:
            self.init = True
            self.doing_rec = True
            self.doing_path = True
            Recognize.resetRec()

        # Log current recognition and path planning status
        Trace.log(f"[liveRecScript][{self.doing_rec}|{self.doing_path}]")

        # Perform recognition if needed
        if self.doing_rec:

            if not self.success:
                self.success, self.rec_status, self.results_dict = self.rec(self.recfile)
            else:
                results_list = self.results_dict.get("recoList", [])
                obstacle_polygon = self.results_dict.get("obstaclePolygon", [])
                self.doing_rec = False
                self.rec_result = results_list[0]
                # Log recognition results
                Trace.log("rec_result: " + json.dumps(self.rec_result))
                self.doing_path = True
            return self.status

        # Perform path planning if needed
        if self.doing_path:
            self.doing_path = False
            # Get current robot position
            pos = Loc.getPose()
            Trace.log("pos: " + json.dumps(pos))

            # Calculate path based on current position and recognition results
            path = Navigation.getRecPath(
                robot_pos_x=0,
                robot_pos_y=0,
                robot_pos_theta=0,
                rec_x=self.rec_result["x"],
                rec_y=self.rec_result["y"],
                rec_theta=self.rec_result["yaw"],
                back_dist=1.0,
                min_ahead_dist=0.5,
                ahead_dist=0.0,
                back_mode=True,
                use_bezier=True,
                hold_dir=999,
                max_speed=0.3,
                slow_down_dist=0.5,
                slow_down_speed=0.02,
                liveRec=True)
            Trace.log("path: " + json.dumps(path))

            # Reset and prepare for movement
            if not Navigation.liveRecGoReset(
                    recfile=self.recfile,
                    x=self.rec_result["x"],
                    y=self.rec_result["y"],
                    theta=self.rec_result["yaw"],
                    tracker_id=self.rec_result["class"],
                    paths=path):
                Trace.log("liveRecGoReset fail!")
                self.status = ScriptStatus.FAILED
                return self.status

            self.doing_rec = True

        # Execute the planned movement
        self.status = Navigation.liveRecGo()
        return self.status

    def rec(self, recfile):
        rec_status = Recognize.getRecStatus()
        if rec_status == 2:
            rec_results = Recognize.getRecResults()
            Trace.log(f"rec_result:{rec_results}")
            return True, rec_status, rec_results
        elif rec_status in (-1, 3):
            if Timer.delay(0.05):
                self.attempts += 1
                if self.attempts > self.max_attempts:
                    rec_results = Recognize.getRecResults()
                    Trace.log(f"raw results:{rec_results}")
                    error_type = rec_results["error"]
                    error_msg = rec_results["logMsg"]
                    Trace.log(f"error_type: {error_type}")
                    self.status = ScriptStatus.FAILED
                    Abnormal.setTask(53306,
                                     "Recognition failed, the maximum number of retries exceeded",
                                     f"{error_msg}",
                                     "",
                                     "")
                else:
                    Recognize.resetRec()
        else:
            Recognize.doRec(recfile, "")
            Timer.delay(0.05)
        return False, rec_status, dict()

    def cancel(self):
        self.status = ScriptStatus.FAILED
        Navigation.cancelLiveRecGo()

