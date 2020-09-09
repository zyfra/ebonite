from ebonite import Ebonite
import os
from datetime import datetime
import joblib
import pandas as pd
import transliterate
from ebonite.build.builder.base import use_local_installation


def rename_df(data):
    data_name=[]
    for i in data.columns:
        try:
            data_name.append(transliterate.translit(str(i).replace('/', '_'), reversed=True))
        except:
            data_name.append(str(i).replace('/', '_'))
    data.columns=data_name
    return(data)


def rename_model(name: str) -> str:
    name = name.split('.pkl')[0]
    unallowed = "!?()*&^%$#@+=/:|><`.'"
    name = ''.join([x for x in name if x not in list(unallowed)])
    name = name.replace(' ', '_').replace('-', '_')
    return 'model_' + name.lower()


def load_models_to_ebonite(num_models: int = 0):
    gmc=pd.read_excel('data.xlsx')
    OM=pd.read_excel('./object_model_PAZ.xlsx',sheet_name='Прогноз')
    OM=rename_df(OM)
    gmc=rename_df(gmc)
    num_models = num_models if num_models else OM.shape[0] + 1
    for i in range(OM.shape[0]):
        try:
            OM['Tselevoj parametr'][i]=transliterate.translit(str(OM['Tselevoj parametr'][i]).replace('/', '_'), reversed=True)
        except:
            OM['Tselevoj parametr'][i]=OM['Tselevoj parametr'][i].replace('/', '_')

    ebnt = Ebonite.local(clear=True)
    task = ebnt.get_or_create_task('zif_project', 'zif_task')

    model_list=os.listdir('./model/')
    start_time = datetime.now()
    lim = 0
    for i in range(OM.shape[0]):
        x_list=OM.loc[OM['Tselevoj parametr']==OM['Tselevoj parametr'][i]].iloc[:,4:]
        x_list=list(x_list[list(x_list.loc[:, (x_list != 0).any(axis=0)].columns)].columns)
        X=gmc[x_list]

        for ii in model_list:
            if ii.find('_'+OM['Tselevoj parametr'][i])!=-1:
                iter_start = datetime.now()
                model_name = rename_model(ii)
                if ebnt.get_model(model_name, task) is not None:
                    continue

                model = joblib.load('./model/'+ii)

                ebnt.create_model(model, X.values, model_name,
                                          project_name='zif_project', task_name='zif_task')
                lim += 1
                if lim > num_models:
                    break
                iter_end = datetime.now()
                print(f'Total time loading models {iter_end-start_time} | '
                      f'Model loaded to ebonite in {iter_end - iter_start} ')
        if lim > num_models:
            break
    return


def build_and_run_multiloader():
    ebnt = Ebonite.local()
    project = ebnt.meta_repo.get_project_by_name('zif_project')
    task = ebnt.meta_repo.get_task_by_name(project, 'zif_task')
    models = ebnt.meta_repo.get_models(task, project)
    if ebnt.meta_repo.get_image_by_name('zif_image', task, project) is None:
        image = ebnt.create_image(models, 'test_wsgi_image', task, builder_args = {'force_overwrite': True},
                          debug=True)
    else:
        image = ebnt.meta_repo.get_image_by_name('zif_image', task, project)

    print(image)

    instance = ebnt.create_instance(image, 'zif_instance',  port_mapping={9000:9000})
    instance.run(detach=True)


def main():
    with use_local_installation():
       load_models_to_ebonite(3)
       build_and_run_multiloader()


if __name__ == '__main__':
    main()
