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
    return [r[0] for _, r in data.iterrows()]


def main():
    ebnt = ebonite.Ebonite.inmemory()

    data, target = get_data()
    # we want easy way to transform anything to datasets, so its either this or ebonite.create_dataset (same for metrics)
    # for now there is no difference, however if we want manage datasets with meta and art repos, we use client
    # or create with ebonite.create_... and then push with ebnt.push_... like for models
    dataset = ebnt.create_dataset(data, target)

    # here we postpone setting task input and output types for easy task creation
    task = ebnt.get_or_create_task('my_project', 'regression_is_my_profession')

    task.add_dataset('train', dataset)
    # this sets task input and output types

    task.add_metric('auc', ebnt.create_metric(roc_auc_score))

    # omit providing dataset as we already have it in task
    task.create_and_push_model(constant, model_name='constant')
    task.create_and_push_model(truth, model_name='truth')

    # maybe save result to models? also need different ways to evaluate "not all"
    result = task.evaluate_all()

    print(result['train']['auc']['constant'])
    print(result['train']['auc']['truth'])

    pprint(serialize(task))


if __name__ == '__main__':
    main()
