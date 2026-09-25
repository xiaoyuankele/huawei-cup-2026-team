"""Scientific invariants specific to the pure-mixture ablation."""
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"scripts"))
from q1_s03.mixture_scale_ablation import features, oof_deltas, paired_bootstrap, P_COLS


class MixtureAblationTests(unittest.TestCase):
    def test_optional_quality_does_not_change_pure_mixture_features(self):
        rng=np.random.default_rng(48)
        p=rng.dirichlet(np.ones(17),size=12)
        p[0,0]=0
        p[0]/=p[0].sum()
        q=rng.uniform(size=12)
        for name,n in [("ilr_ridge",16),("quadratic_ridge",152)]:
            pure=features(p,None,name)
            np.testing.assert_array_equal(pure,features(p,q[::-1],name))
            extended=features(p,q,name+"_qproxy")
            self.assertEqual(pure.shape,(12,n))
            self.assertEqual(extended.shape,(12,n+1))
            np.testing.assert_array_equal(extended[:,:-1],pure)
            np.testing.assert_array_equal(extended[:,-1],q)

    def test_heldout_delta_cannot_change_its_own_oof_prediction(self):
        rng=np.random.default_rng(18)
        a6=pd.DataFrame(rng.dirichlet(np.ones(17),size=30),columns=P_COLS)
        delta=rng.normal(size=(30,13))
        changed=delta.copy()
        heldout=np.arange(30)%5==0
        changed[heldout]+=1000
        kinds=["C0_none","C1_global","C1_domain","C2_mixture_conditioned"]
        before=oof_deltas(a6,delta,10,kinds)
        after=oof_deltas(a6,changed,10,kinds)
        for kind in kinds:
            np.testing.assert_array_equal(before[kind][heldout],after[kind][heldout])

    def test_bootstrap_keeps_response_vector_as_one_recipe_unit(self):
        y=np.zeros((3,2))
        ref=np.array([[1,3],[2,0],[4,2]],dtype=float)
        new=ref*0.5
        draws=np.array([[0,0,0],[1,1,1],[2,2,2]])
        result=paired_bootstrap(y,ref,new,draws)
        expected_rmse=-0.5*np.sqrt((ref**2).mean(1))
        expected_mae=-0.5*np.abs(ref).mean(1)
        for key,values in [("rmse",expected_rmse),("mae",expected_mae)]:
            lo,hi=np.quantile(values,[0.025,0.975])
            self.assertAlmostEqual(result[key+"_ci95_low"],lo)
            self.assertAlmostEqual(result[key+"_ci95_high"],hi)
            self.assertAlmostEqual(result[key+"_reduction_pct"],50)


if __name__ == "__main__":
    unittest.main()
