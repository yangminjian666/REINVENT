#!/usr/bin/env python
from __future__ import division
import numpy as np
from sklearn import svm
from rdkit import Chem
from rdkit import rdBase
from rdkit import DataStructs
from rdkit.Chem import AllChem
import pickle
rdBase.DisableLog('rdApp.error')

"""Scoring function should be a class where some tasks that are shared for every call 
   can be reallocated to the __init__, and has a __call__ method which takes a list of 
   smiles as an argument and returns a matching np.array of floats."""

class no_sulphur(object):
    def __init__(self, **kwargs):
        pass

    def __call__(self, smiles):
        mols = [Chem.MolFromSmiles(smile) for smile in smiles]
        valid = [1 if mol!=None else 0 for mol in mols]
        valid_idxs = [idx for idx, boolean in enumerate(valid) if boolean==1]
        valid_mols = [mols[idx] for idx in valid_idxs]
        has_sulphur = [16 not in [atom.GetAtomicNum() for atom in mol.GetAtoms()] for mol in valid_mols]
        sulphur_score =  [1 if ele else -1 for ele in has_sulphur]
        score = np.full(len(smiles), 0, dtype=np.float32)
        for idx, value in zip(valid_idxs, sulphur_score):
            score[idx] =  value
        return np.array(score, dtype=np.float32)

class tanimoto(object):
    def __init__(self, k=0.7, **kwargs):
        self.k = k
        query_mol = Chem.MolFromSmiles("Cc1ccc(cc1)c2cc(nn2c3ccc(cc3)S(=O)(=O)N)C(F)(F)F")
        self.query_fp = AllChem.GetMorganFingerprint(query_mol, 2, useCounts=False, useFeatures=True)

    def __call__(self, smiles):
        mols = [Chem.MolFromSmiles(smile) for smile in smiles]
        valid = [1 if mol!=None else 0 for mol in mols]
        valid_idxs = [idx for idx, boolean in enumerate(valid) if boolean==1]
        valid_mols = [mols[idx] for idx in valid_idxs]

        fps = [AllChem.GetMorganFingerprint(mol, 2, useCounts=False, useFeatures=True) for mol in valid_mols]

        tversky_similarity = np.array([DataStructs.TverskySimilarity(self.query_fp, fp, 1, 1) for fp in fps])
        tversky_similarity = np.minimum(tversky_similarity, self.k)
        tversky_similarity = [-1 + 2 * x / self.k for x in tversky_similarity]
        score = np.full(len(smiles), -1, dtype=np.float32)

        for idx, value in zip(valid_idxs, tversky_similarity):
            score[idx] =  value
        return np.array(score, dtype=np.float32)

class activity_model(object):
    def __init__(self, **kwargs):
        with open("data/clf.pkl", "r") as f:
            self.clf = pickle.load(f)
            
    def __call__(self, smiles):
        mols = [Chem.MolFromSmiles(smile) for smile in smiles]
        valid = [1 if mol!=None else 0 for mol in mols]
        valid_idxs = [idx for idx, boolean in enumerate(valid) if boolean==1]
        valid_mols = [mols[idx] for idx in valid_idxs]

        fps = activity_model.fingerprints_from_mols(valid_mols)
        activity_score = self.clf.predict_proba(fps)[:, 1]    
        activity_score = -1 + 2 * activity_score

        score = np.full(len(smiles), -1, dtype=np.float32)

        for idx, value in zip(valid_idxs, activity_score):
            score[idx] =  value
        return np.array(score, dtype=np.float32)

    @classmethod
    def fingerprints_from_mols(cls, mols):
            fps = [AllChem.GetMorganFingerprintAsBitVect(mol, 3) for mol in mols] 
            np_fps = []
            for fp in fps:
                arr = np.zeros((1,))
                DataStructs.ConvertToNumpyArray(fp, arr)
                np_fps.append(arr)
            return np_fps

def get_scoring_function(name, kwargs):
    scoring_functions = [no_sulphur, tanimoto, activity_model]
    try:
        scoring_function = [f for f in scoring_functions if f.__name__ == name][0]
        return scoring_function(**kwargs)
    except IndexError:
        print "Scoring function must be one of {}".format([f.__name__ for f in scoring_functions])
        raise 

