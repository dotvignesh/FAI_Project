"""
Modified Code from: https://github.com/eunjuyummy/autonomous-drone-flight-project/
"""

import os
import numpy as np
import pybullet as p
import pkg_resources

from gym_pybullet_drones.utils.enums import DroneModel, Physics
from BaseNewRLAviary import ActionType, ObservationType, BaseNewRLAviary


class FlyThruGateAviary(BaseNewRLAviary):
    """Single agent RL problem: fly through a gate."""
    
    ################################################################################
    
    def __init__(self,
                 drone_model: DroneModel=DroneModel.CF2X,
                 initial_xyzs=None,
                 initial_rpys=None,
                 physics: Physics=Physics.PYB,
                 pyb_freq: int = 240,
                 ctrl_freq: int = 240,
                 gui=True,
                 record=True,
                 obs: ObservationType=ObservationType.KIN,
                 act: ActionType=ActionType.RPM
                 ):
        """Initialization of a single agent RL environment.

        Using the generic single agent RL superclass.

        Parameters
        ----------
        drone_model : DroneModel, optional
            The desired drone type (detailed in an .urdf file in folder `assets`).
        initial_xyzs: ndarray | None, optional
            (NUM_DRONES, 3)-shaped array containing the initial XYZ position of the drones.
        initial_rpys: ndarray | None, optional
            (NUM_DRONES, 3)-shaped array containing the initial orientations of the drones (in radians).
        physics : Physics, optional
            The desired implementation of PyBullet physics/custom dynamics.
        pyb_freq : int, optional
            The frequency at which PyBullet steps (a multiple of ctrl_freq).
        ctrl_freq : int, optional
            The frequency at which the environment steps.
        gui : bool, optional
            Whether to use PyBullet's GUI.
        record : bool, optional
            Whether to save a video of the simulation in folder `files/videos/`.
        obs : ObservationType, optional
            The type of observation space (kinematic information or vision)
        act : ActionType, optional
            The type of action space (1 or 3D; RPMS, thurst and torques, or waypoint with PID control)

        """
        super().__init__(drone_model=drone_model,
                         initial_xyzs=initial_xyzs,
                         initial_rpys=initial_rpys,
                         physics=physics,
                         pyb_freq=pyb_freq,
                         ctrl_freq=ctrl_freq,
                         gui=gui,
                         record=record,
                         obs=obs,
                         act=act
                         )

    ################################################################################
    
    def _addObstacles(self):
        """Add obstacles to the environment.

        Extends the superclass method and adds two gates and walls between them.
        """
        super()._addObstacles()
        # First gate
        p.loadURDF(pkg_resources.resource_filename('gym_pybullet_drones', 'assets/architrave.urdf'),
                   [0, -1, .55],
                   p.getQuaternionFromEuler([0, 0, 0]),
                   physicsClientId=self.CLIENT
                   )
        # Second gate
        p.loadURDF(pkg_resources.resource_filename('gym_pybullet_drones', 'assets/architrave.urdf'),
                   [0, -2, .55],
                   p.getQuaternionFromEuler([0, 0, 0]),
                   physicsClientId=self.CLIENT
                   )
        
        # Create pillars for both gates
        for i in range(10):
            # First gate pillars
            p.loadURDF("cube_small.urdf",
                       [-.3, -1, .02+i*0.05],
                       p.getQuaternionFromEuler([0, 0, 0]),
                       physicsClientId=self.CLIENT
                       )
            p.loadURDF("cube_small.urdf",
                       [.3, -1, .02+i*0.05],
                       p.getQuaternionFromEuler([0,0,0]),
                       physicsClientId=self.CLIENT
                       )
            # Second gate pillars
            p.loadURDF("cube_small.urdf",
                       [-.3, -2, .02+i*0.05],
                       p.getQuaternionFromEuler([0, 0, 0]),
                       physicsClientId=self.CLIENT
                       )
            p.loadURDF("cube_small.urdf",
                       [.3, -2, .02+i*0.05],
                       p.getQuaternionFromEuler([0,0,0]),
                       physicsClientId=self.CLIENT
                       )
            
            # Add walls between gates (using small cubes)
            if i < 8:  # Make walls slightly shorter than gates
                p.loadURDF("cube_small.urdf",
                          [0.15, -1.5, .02+i*0.05],
                          p.getQuaternionFromEuler([0, 0, 0]),
                          physicsClientId=self.CLIENT
                          )
                p.loadURDF("cube_small.urdf",
                          [-0.15, -1.5, .02+i*0.05],
                          p.getQuaternionFromEuler([0, 0, 0]),
                          physicsClientId=self.CLIENT
                          )

    ################################################################################
    
    def _computeReward(self):
        """Computes the current reward value."""
        reward = 0.0
        state = self._getDroneStateVector(0)
        norm_ep_time = (self.step_counter/self.PYB_FREQ) / self.EPISODE_LEN_SEC
        
        # Check first gate
        if (state[0] >= -.27) and (state[0] <= .27) and (state[1] >= -1.1) and (state[1] <= -0.9) and (state[2] <= .5):
            reward += 10
        # Check second gate
        if (state[0] >= -.27) and (state[0] <= .27) and (state[1] >= -2.1) and (state[1] <= -1.9) and (state[2] <= .5):
            reward += 10
        
        # Penalty for hitting walls (adjusted for closer walls)
        if (state[1] >= -1.7) and (state[1] <= -1.3):  # Between gates
            if (state[0] >= 0.1) or (state[0] <= -0.1):  # Near walls (adjusted from ±0.15 to ±0.1)
                if state[2] <= 0.4:  # Below wall height
                    reward -= 5
        
        return (-10 * np.linalg.norm(np.array([0, -2*norm_ep_time, 0.75])-state[0:3])**2) + reward

    ################################################################################
    
    def _computeTerminated(self):
        """Computes the current done value.

        Returns
        -------
        bool
            Whether the current episode is done.

        """
        if self.step_counter/self.PYB_FREQ > self.EPISODE_LEN_SEC:
            return True
        else:
            return False
        
    ################################################################################
    
    def _computeTruncated(self):
        """Computes the current truncated value(s)."""
        state = self._getDroneStateVector(0)
        # Successfully passed both gates
        if ((state[0] >= -.27) and (state[0] <= .27) and 
            (state[1] >= -2.1) and (state[1] <= -1.9) and 
            (state[2] <= .5)):
            return True
        return False

    ################################################################################
    
    def _computeInfo(self):
        """Computes the current info dict(s).

        Unused.

        Returns
        -------
        dict[str, int]
            Dummy value.

        """
        return {"answer": 42} #### Calculated by the Deep Thought supercomputer in 7.5M years

    ################################################################################
    
    def _clipAndNormalizeState(self,
                               state
                               ):
        """Normalizes a drone's state to the [-1,1] range.

        Parameters
        ----------
        state : ndarray
            (20,)-shaped array of floats containing the non-normalized state of a single drone.

        Returns
        -------
        ndarray
            (20,)-shaped array of floats containing the normalized state of a single drone.

        """
        MAX_LIN_VEL_XY = 3 
        MAX_LIN_VEL_Z = 1

        MAX_XY = MAX_LIN_VEL_XY*self.EPISODE_LEN_SEC
        MAX_Z = MAX_LIN_VEL_Z*self.EPISODE_LEN_SEC

        MAX_PITCH_ROLL = np.pi # Full range

        clipped_pos_xy = np.clip(state[0:2], -MAX_XY, MAX_XY)
        clipped_pos_z = np.clip(state[2], 0, MAX_Z)
        clipped_rp = np.clip(state[7:9], -MAX_PITCH_ROLL, MAX_PITCH_ROLL)
        clipped_vel_xy = np.clip(state[10:12], -MAX_LIN_VEL_XY, MAX_LIN_VEL_XY)
        clipped_vel_z = np.clip(state[12], -MAX_LIN_VEL_Z, MAX_LIN_VEL_Z)

        if self.GUI:
            self._clipAndNormalizeStateWarning(state,
                                               clipped_pos_xy,
                                               clipped_pos_z,
                                               clipped_rp,
                                               clipped_vel_xy,
                                               clipped_vel_z
                                               )

        normalized_pos_xy = clipped_pos_xy / MAX_XY
        normalized_pos_z = clipped_pos_z / MAX_Z
        normalized_rp = clipped_rp / MAX_PITCH_ROLL
        normalized_y = state[9] / np.pi # No reason to clip
        normalized_vel_xy = clipped_vel_xy / MAX_LIN_VEL_XY
        normalized_vel_z = clipped_vel_z / MAX_LIN_VEL_XY
        normalized_ang_vel = state[13:16]/np.linalg.norm(state[13:16]) if np.linalg.norm(state[13:16]) != 0 else state[13:16]

        norm_and_clipped = np.hstack([normalized_pos_xy,
                                      normalized_pos_z,
                                      state[3:7],
                                      normalized_rp,
                                      normalized_y,
                                      normalized_vel_xy,
                                      normalized_vel_z,
                                      normalized_ang_vel,
                                      state[16:20]
                                      ]).reshape(20,)

        return norm_and_clipped
    
    ################################################################################
    
    def _clipAndNormalizeStateWarning(self,
                                      state,
                                      clipped_pos_xy,
                                      clipped_pos_z,
                                      clipped_rp,
                                      clipped_vel_xy,
                                      clipped_vel_z,
                                      ):
        """Debugging printouts associated to `_clipAndNormalizeState`.

        Print a warning if values in a state vector is out of the clipping range.
        
        """
        if not(clipped_pos_xy == np.array(state[0:2])).all():
            print("[WARNING] it", self.step_counter, "in FlyThruGateAviary._clipAndNormalizeState(), clipped xy position [{:.2f} {:.2f}]".format(state[0], state[1]))
        if not(clipped_pos_z == np.array(state[2])).all():
            print("[WARNING] it", self.step_counter, "in FlyThruGateAviary._clipAndNormalizeState(), clipped z position [{:.2f}]".format(state[2]))
        if not(clipped_rp == np.array(state[7:9])).all():
            print("[WARNING] it", self.step_counter, "in FlyThruGateAviary._clipAndNormalizeState(), clipped roll/pitch [{:.2f} {:.2f}]".format(state[7], state[8]))
        if not(clipped_vel_xy == np.array(state[10:12])).all():
            print("[WARNING] it", self.step_counter, "in FlyThruGateAviary._clipAndNormalizeState(), clipped xy velocity [{:.2f} {:.2f}]".format(state[10], state[11]))
        if not(clipped_vel_z == np.array(state[12])).all():
            print("[WARNING] it", self.step_counter, "in FlyThruGateAviary._clipAndNormalizeState(), clipped z velocity [{:.2f}]".format(state[12]))