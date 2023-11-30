import math
from typing import Union, Tuple
# import highway_env
import gymnasium as gym
import highway_env.envs
import numpy as np

import spider
import spider.elements as elm
from spider.elements import TrackingBoxList, OccupancyGrid2D, RoutedLocalMap, VehicleState, Trajectory
# from spider.elements import Location, Rotation, Transform,

'''
Interface逻辑：
observation -> perception, routed_local_map, localization (planner统一的输入表达) -> output
'''

class HighwayEnvInterface:
    def __init__(self,
                 env: highway_env.envs.AbstractEnv,
                 # observation_flag=spider.HIGHWAYENV_OBS_KINEMATICS,
                 perception_flag=spider.PERCEPTION_BOX,
                 output_flag=spider.OUTPUT_TRAJECTORY,

                 veh_length=5.0,
                 veh_width=2.0):

        self._env = env
        self._env_config = env.config

        # 车长车宽没考虑
        self.observation_flag = self._observation_type()
        self.perception_flag = perception_flag
        self.output_flag = output_flag

        self.veh_length = 5.0
        self.veh_width = 2.0

        # self.kine_feature_index_mapping = self._build_feature_index_mapping()
        self._all_features = self._env_config["observation"]["features"]
        assert "x" in self._all_features and "y" in self._all_features


    # def observe_env(self):
    #     obs, info = self._env.

    def wrap_observation(self, observation, center_lines=None) \
            -> Tuple[Union[TrackingBoxList, OccupancyGrid2D], RoutedLocalMap, VehicleState]:
        '''
        qzl:这个函数的名字可以再改
        把observation改成planner的统一输入形式。
        '''



        if self.observation_flag == spider.HIGHWAYENV_OBS_KINEMATICS:
            # highway-env的观测是kinematics

            ego_veh_state = self._get_kine_ego_state(observation)


            if self.perception_flag == spider.PERCEPTION_BOX:
                perception = self._wrap_kine2box(observation)
            elif self.perception_flag == spider.PERCEPTION_OCC:
                perception = self._wrap_kine2box(observation)
            else:
                raise ValueError("INVALID perception_flag")

        else:
            raise NotImplementedError("not supported now...")

        return perception, RoutedLocalMap, VehicleState

    def convert_action(self, action, planner_dt):
        if self.output_flag == spider.OUTPUT_TRAJECTORY: # 轨迹
            next_x, next_y = action.x[1], action.y[1]
        else: # 控制量
            raise NotImplementedError("not supported now...")



    def conduct_action(self, action, planner_dt):
        '''
        qzl: 应该写成直接执行动作呢还是写成输出对应格式的动作呢？
        '''
        if self.output_flag == spider.OUTPUT_TRAJECTORY: # 轨迹


            pass
        else: # 控制量
            raise NotImplementedError("not supported now...")

    def _observation_type(self):
        type_str = self._env_config["observation"]["type"]
        if type_str == "Kinematics":
            return spider.HIGHWAYENV_OBS_KINEMATICS
        elif type_str == "GrayscaleObservation":
            return spider.HIGHWAYENV_OBS_GRAYIMG
        elif type_str == "OccupancyGird":
            return spider.HIGHWAYENV_OBS_OCCUPANCY
        elif type_str == "TimeToCollision":
            return spider.HIGHWAYENV_OBS_TTC
        else:
            raise ValueError("INVALID observation type")

    # def _build_feature_index_mapping(self):
    #     features: list = self._env_config["observation"]["features"]
    #     necessary_keys = ["presence", "x", "y", "vx", "vy","heading","cos_h", "sin_h"]
    #     for key in necessary_keys:
    #         if key in features:
    #             idx = features.index(key)
    #             self.kine_feature_index_mapping[key] = idx
    #     assert "x" in self.kine_feature_index_mapping and "y" in self.kine_feature_index_mapping


    def _get_veh_info_dict(self, veh_info_vector, feat_names, *, calc_heading: bool=True) -> dict:
        '''
        feat_names: 需要给出的feature的名字
        veh_info_vector: 目标车辆的Observation的对应切片
        '''
        # todo:qzl: 要加入，关于absolute和normalize的自调整

        # idxs = self.kine_feature_index_mapping
        #
        # features: list = self._env_config["observation"]["features"]

        all_veh_info_dict = dict(zip(self._all_features, veh_info_vector))

        # veh_info_dict = {key: veh_info_vector[idxs[key]] if key in features else 0.0 for key in feat_names}
        veh_info_dict = {key: all_veh_info_dict[key] if key in all_veh_info_dict else 0.0
                         for key in feat_names}


        if calc_heading:
            if "heading" in feat_names: # 如果需要储存heading信息，但heading可能用别的方式表达，那么需要进行以下处理
                if "heading" in self._all_features:
                    pass  #  如果本身observation给出的heading就直接用heading信息
                elif "cos_h" in self._all_features:
                    veh_info_dict["heading"] = math.acos(all_veh_info_dict["cos_h"])
                elif "sin_h" in self._all_features:
                    veh_info_dict["heading"] = math.asin(all_veh_info_dict["sin_h"])
                elif ("vx" in self._all_features) and ("vy" in self._all_features):
                    veh_info_dict["heading"] = math.atan2(all_veh_info_dict["vy"], all_veh_info_dict["vx"])
                else:
                    pass # 默认设0.0

        return veh_info_dict


    def _get_kine_ego_state(self, observation) -> VehicleState:
        necessary_feat = ["x", "y", "vx", "vy", "heading", "cos_h", "sin_h"]
        ego_info:dict = self._get_veh_info_dict(observation[0], necessary_feat)
        loc = elm.Location(ego_info["x"], ego_info["y"], 0.)
        rot = elm.Rotation(0., ego_info["heading"], 0.)
        velocity = elm.Vector3D(ego_info["vx"], ego_info["vy"], 0.)
        ego_state = VehicleState(elm.Transform(loc, rot), velocity, elm.Vector3D())
        return ego_state


    def _wrap_kine2box(self, observation) -> TrackingBoxList:

        necessary_feat = ["presence", "x", "y", "vx", "vy", "heading"]
        tbox_list = TrackingBoxList()
        for i, veh_info_vector in enumerate(observation):
            if i == 0:
                # i=0 是自车，不需要加入BoundingBox
                continue

            veh_info = self._get_veh_info_dict(veh_info_vector, necessary_feat)
            if "presence" in self._all_features and (not veh_info["presence"]):
                # 存在presence属性，且该车的presence属性是0，表明这不存在
                continue

            x, y = veh_info["x"], veh_info["y"]
            heading = veh_info["heading"]
            vx = veh_info["vx"]
            vy = veh_info["vy"]
            tbox = elm.TrackingBox(obb=(x, y, self.veh_length,self.veh_width,heading), vx=vx, vy=vy)

            tbox_list.append(tbox)

        return tbox_list


    def _wrap_kine2grid(self) -> OccupancyGrid2D:
        pass


    def _extract_map(self, delta_s=1.0) -> RoutedLocalMap:
        # todo:qzl:现在没有加入extend车道的功能，也就是在长度不够的情况下，通过route信息，把下一个路段的lane加载进来。
        # todo:qzl: 另外导航信息也没加到routedmap里面
        local_map = RoutedLocalMap()

        ego_veh = self._env.vehicle

        network = ego_veh.road.network

        target_lane_idx = ego_veh.target_lane_index
        all_neighbor_lanes = network.all_side_lanes(target_lane_idx)

        for i, lane in enumerate(all_neighbor_lanes):
            sampled_s = np.arange(0, lane.length, delta_s)
            center_line = [lane.position(s, 0) for s in sampled_s]
            spd_lane = elm.Lane(i, center_line, width=lane.width_at(0), speed_limit=lane.speed_limit)
            local_map.add_lane(spd_lane)

        # local_map.network = ego_veh.road.network # todo:qzl: 由于没有确认好network的形式，建议后面再说
        # local_map.route = ego_veh.route if not (ego_veh.route is None) else [target_lane_idx]
        return local_map


if __name__ == '__main__':
    import gym
    import highway_env
    from matplotlib import pyplot as plt

    # env = gym.make('highway-v0', render_mode='rgb_array')
    env = gym.make("highway-v0")
    env.reset()


    for _ in range(3):
        action = env.action_type.actions_indexes["IDLE"]
        obs, reward, done, truncated, info = env.step(action)
        env.render()

    plt.imshow(env.render())
    plt.show()




