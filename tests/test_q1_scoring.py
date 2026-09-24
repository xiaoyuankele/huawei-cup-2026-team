import sys, unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.models.q1_scoring import critic_weights, topsis


class ModelProperties(unittest.TestCase):
    def test_anchors_and_identical_coordinates(self):
        w=np.array([.1,.2,.7]);x=np.array([[0,0,0],[1,1,1],[.37,.37,.37]])
        np.testing.assert_allclose(topsis(x,w)[0],[0,100,37],atol=1e-12)

    def test_improving_any_benefit_cannot_reduce_score(self):
        rng=np.random.default_rng(24);x=rng.random((500,16));w=rng.dirichlet(np.ones(16))
        old=topsis(x,w)[0]
        for j in range(16):
            y=x.copy();y[:,j]=np.minimum(1.,y[:,j]+.07)
            self.assertTrue(np.all(topsis(y,w)[0]>=old-1e-12))

    def test_fixed_reference_does_not_change_when_records_added(self):
        x=np.array([[.2,.8],[.3,.4]]);w=np.array([.3,.7])
        np.testing.assert_array_equal(topsis(x,w)[0],topsis(np.vstack([x,[0,0],[1,1]]),w)[0][:2])

    def test_invalid_data_is_not_imputed(self):
        for x,w in [(np.array([[np.nan,.5]]),[.5,.5]),(np.array([[1.2,.3]]),[.5,.5]),(np.array([[.2,.3]]),[-.2,1.2])]:
            with self.assertRaises(ValueError):topsis(x,w)

    def test_critic_constant_column_has_zero_weight(self):
        x=np.array([[0,.8,.5],[.2,.6,.5],[.4,.3,.5],[.9,.2,.5]])
        w,*_=critic_weights(x)
        self.assertEqual(w[2],0.);self.assertAlmostEqual(float(w.sum()),1.)
        with self.assertRaises(ValueError):critic_weights(np.ones((4,3)))


if __name__=='__main__':unittest.main()
