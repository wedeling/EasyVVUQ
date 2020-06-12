class ReplicaSampler(BaseSamplingElement, name='replica_sampler'):
    def __init__(self, sampler, ensemble_col):
        self.sampler = sampler
        self.ensemble_col = ensemble_col

    def is_finite(self):
        return False

    def element_version(self):
        return '0.1'

    def n_samples(self):
        raise RuntimeError("You can't get the number of samples in an infinite sampler")

    def __next__(self):
        pass

    def is_restartable(self):
        return False