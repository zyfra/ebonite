from pprint import pprint

import pandas as pd
from pyjackson import serialize
from sklearn.metrics import roc_auc_score

import ebonite


def get_data():
    data = pd.DataFrame([[1, 0], [0, 1]], columns=['a', 'b'])
    target = [1, 0]
    return data, target


def constant(data):
    return [0 for _ in range(len(data))]


def truth(data: pd.DataFrame):
    return [int(r[0]) for _, r in data.iterrows()]


def main():
    ebnt = ebonite.Ebonite.inmemory()

    data, target = get_data()
    # we want easy way to transform anything to datasets, so its either this or ebonite.create_dataset (same for metrics)
    # for now there is no difference, however if we want manage datasets with meta and art repos, we use client
    # or create with ebonite.create_... and then push with ebnt.push_... like for models
    # dataset = ebnt.create_dataset(data, target)

    # here we postpone setting task input and output types for easy task creation
    task = ebnt.get_or_create_task('my_project', 'regression_is_my_profession')
    task.add_metric('auc', roc_auc_score)
    task.add_evaluation('train', data, target, 'auc')

    pprint(task.evaluation_sets)
    pprint(task.datasets)
    pprint(task.metrics)

    # omit providing dataset as we already have it in task
    mc = task.create_and_push_model(constant, data, model_name='constant')
    mt = task.create_and_push_model(truth, data, model_name='truth')

    pprint(mc.wrapper.methods)
    pprint(mt.wrapper.methods)

    # maybe save result to models? also need different ways to evaluate "not all"
    result = task.evaluate_all()

    print(result['train'].scores)

    pprint(serialize(task))


if __name__ == '__main__':
    main()
