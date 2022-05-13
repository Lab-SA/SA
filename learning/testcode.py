import copy
from tqdm import tqdm

from federated_main import add_accuracy, setup, get_user_dataset, local_update, test_accuracy, update_globalmodel, test_model
from models_helper import get_model_weights
from utils import sum_weights

if __name__ == "__main__":

    local_models = []

    train_loss = []

    global_model = setup()

    user_groups = get_user_dataset()

    global_weights = get_model_weights(global_model)


    print(f'\n | TESTING CODE |\n')

    for epoch in tqdm(range(3)):
        local_weights, local_losses = [], []
        print(f'\n | Global Training Round : {epoch+1} |\n')

        for idx in range(0,4):
            local_model, local_weight, local_loss = local_update(global_model, user_groups[idx], epoch)
            print(local_weight)
            local_models.append(copy.deepcopy(local_model))
            local_weights.append(copy.deepcopy(local_weight))
            local_losses.append(copy.deepcopy(local_loss))

        sum_weight = sum_weights(local_weights)

        global_model = update_globalmodel(global_model, sum_weight, local_losses)

        # # update global weights
        # global_weights = average_weights_origin(local_weights)

        # # update global weights
        # global_model.load_state_dict(global_weights)

        # loss_avg = sum(local_losses) / len(local_losses)
        # train_loss.append(loss_avg)


        list_acc = []
        for idx in range(0,4):
            acc = test_accuracy(local_models[idx], global_model)
            list_acc.append(acc)
        
        add_accuracy(list_acc, epoch)

    
    test_model(global_model)
