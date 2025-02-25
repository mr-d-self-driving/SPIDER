import numpy as np
from itertools import product

from spider.sampler.BaseSampler import BaseSampler
from spider.sampler.common import LazyList
from spider.elements.curves import QuarticPolynomial, QuinticPolynomial, PiecewiseQuinticPolynomial


# 变量符号含义：x对t的函数
# todo: 这里的变量名字要改，x和t常有歧义
class QuarticPolyminalSampler(BaseSampler):
    def __init__(self, end_t_candidates, end_dx_candidates):
        '''
        end_dx_candidates: x一阶导的终值候选项
        '''
        super(QuarticPolyminalSampler, self).__init__()
        self.end_t_candidates = end_t_candidates
        self.end_dx_candidates = end_dx_candidates

    def sample(self, start_state, calc_by_need=False):
        xs, dxs, ddxs = start_state

        if calc_by_need:
            func = QuarticPolynomial.from_kine_states
            samples = LazyList()
            for dxe in self.end_dx_candidates:
                for te in self.end_t_candidates:
                    samples.append( # append一个callable函数
                        LazyList.wrap_generator(func, xs, dxs, ddxs, dxe, 0.0, te)
                    )
        else:
            samples = []
            for dxe in self.end_dx_candidates:
                for te in self.end_t_candidates:
                    samples.append(QuarticPolynomial.from_kine_states(xs, dxs, ddxs, dxe, 0.0, te))

        return samples

    def sample_one(self, start_state, end_t, end_dx):
        xs, dxs, ddxs = start_state
        return QuinticPolynomial.from_kine_states(xs, dxs, ddxs, end_dx, 0.0, end_t)


class QuinticPolyminalSampler(BaseSampler):
    def __init__(self, end_t_candidates, end_x_candidates):
        """
        end_x_candidates: x的终值候选项
        """
        super(QuinticPolyminalSampler, self).__init__()
        self.end_t_candidates = end_t_candidates
        self.end_x_candidates = end_x_candidates

    def sample(self, start_state, calc_by_need=False):
        # TODO:QZL:未来可以根据werling论文考虑末态s的影响，用于跟车场景/停车线场景
        xs, dxs, ddxs = start_state
        if calc_by_need:
            func = QuinticPolynomial.from_kine_states
            samples = LazyList()
            for xe in self.end_x_candidates:
                for te in self.end_t_candidates:
                    samples.append( # append一个callable函数
                        LazyList.wrap_generator(func, xs, dxs, ddxs, xe, 0.0, 0.0, te)
                    )
        else:
            samples = []
            for xe in self.end_x_candidates:
                for te in self.end_t_candidates:
                    samples.append(QuinticPolynomial.from_kine_states(xs, dxs, ddxs, xe, 0.0, 0.0, te))

        return samples

    def sample_one(self, start_state, end_t, end_x):
        xs, dxs, ddxs = start_state
        return QuinticPolynomial.from_kine_states(xs, dxs, ddxs, end_x, 0.0, 0.0, end_t)



class PiecewiseQuinticPolyminalSampler(BaseSampler):
    def __init__(self, delta_t, max_segment_num, x_candidates, critical_x_candidates=None):
        """
        end_x_candidates: x的终值候选项
        """
        super(PiecewiseQuinticPolyminalSampler, self).__init__()
        self.delta_t = delta_t
        self.max_segment_num = max_segment_num
        self.x_candidates = x_candidates
        # self.critical_x_candidates = end_x_candidates if critical_x_candidates is None else critical_x_candidates

    def sample(self, start_state, calc_by_need=False):
        xs, dxs, ddxs = start_state
        samples = LazyList() if calc_by_need else []

        for seg_num in range(1, self.max_segment_num+1):
            all_points_with_derivatives = np.zeros((seg_num+1, 4))
            all_points_with_derivatives[0,:] = np.array([0., xs, dxs, ddxs])
            all_points_with_derivatives[:,0] = np.arange(seg_num+1) * self.delta_t
            # 每一层，采样中间点
            for all_critical_x in product(self.x_candidates, repeat=seg_num): # 连续排列组合的迭代工具
                all_points_with_derivatives[1:, 1] = np.array(all_critical_x)
                if calc_by_need:
                    func = PiecewiseQuinticPolynomial
                    samples.append(
                        LazyList.wrap_generator(func, all_points_with_derivatives))
                else:
                    curve = PiecewiseQuinticPolynomial(all_points_with_derivatives)
                    samples.append(curve)

        return samples

if __name__ == '__main__':
    deltax, max_seg_num = 10, 4
    sampler = PiecewiseQuinticPolyminalSampler(deltax, max_seg_num, [-2,-1,0,1,2])
    samples = sampler.sample([0,-0.1,0])

    import matplotlib.pyplot as plt
    xx = np.linspace(0,deltax*max_seg_num,100)
    for curve in samples:
        yy = curve(xx, order=0)
        plt.plot(xx,yy,'k')
    plt.show()

