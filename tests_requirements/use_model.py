import dill

if __name__ == '__main__':
    with open('model.pkl', 'rb') as f:
        model = dill.load(f)

    model(1)
