import numbers
import time

import numpy as np
from pycompss.api.compss import compss
from pycompss.api.parameter import FILE_IN, FILE_OUT
from pycompss.api.task import task


@compss(runcompss="runcompss", flags="-d --python_interpreter=python3",
        working_dir='/home/bscuser/.COMPSs/prova_dins',
        app_name="/home/bscuser/git/dislib/examples/nested_app.py")
@task(params=FILE_IN, out=FILE_OUT, returns=int)
def nested_fit_and_score(out, estimator, train_ds, validation_ds, scorer,
                         parameters, fit_params, nested):
    pass


def fit_and_score(estimator, train_ds, validation_ds, scorer, parameters,
                  fit_params, nested, idx):
    if nested:
        result = 'result' + str(idx) + '.out'
        ret_code = nested_fit_and_score(estimator, train_ds, validation_ds,
                                        scorer, parameters, fit_params, result)
        if ret_code != 0:  # Return code should be 0
            raise RuntimeError(
                '@compss task failed with return code ' + str(ret_code))
        return result
    if parameters is not None:
        estimator.set_params(**parameters)
    t0_fit = time.time()
    estimator.fit(train_ds, **fit_params)
    master_fit_time = time.time() - t0_fit
    t0_score = time.time()
    test_scores = _score(estimator, validation_ds, scorer)
    master_score_time = time.time() - t0_score

    return [test_scores, master_fit_time, master_score_time]


def _score(estimator, dataset, scorers):
    """Return a dict of scores"""
    scores = {}

    for name, scorer in scorers.items():
        score = scorer(estimator, dataset)
        scores[name] = score
    return scores


def validate_score(score, name):
    if not isinstance(score, numbers.Number) and \
            not (isinstance(score, np.ndarray) and len(score.shape) == 0):
        raise ValueError("scoring must return a number, got %s (%s) "
                         "instead. (scorer=%s)"
                         % (str(score), type(score), name))
    return score


def aggregate_score_dicts(scores):
    """Aggregate the results of each scorer
    Example
    -------
    >>> scores = [{'a': 1, 'b':10}, {'a': 2, 'b':2}, {'a': 3, 'b':3},
    ...           {'a': 10, 'b': 10}]
    >>> aggregate_score_dicts(scores)
    {'a': array([1, 2, 3, 10]),
     'b': array([10, 2, 3, 10])}
    """
    return {key: np.asarray([score[key] for score in scores])
            for key in scores[0]}


def check_scorer(estimator, scorer):
    if scorer is None:
        if hasattr(estimator, 'score'):
            def _passthrough_scorer(estimator, *args, **kwargs):
                """Function that wraps estimator.score"""
                return estimator.score(*args, **kwargs)
            return _passthrough_scorer
        else:
            raise TypeError(
                "If a scorer is None, the estimator passed should have a "
                "'score' method. The estimator %r does not." % estimator)
    elif callable(scorer):
        return scorer
    raise ValueError("Invalid scorer %r" % scorer)
